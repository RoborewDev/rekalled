import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.params import Depends as DependsParam
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import SessionDep, SettingsDep
from app.auth.dev import dev_principal
from app.auth.logto import (
    InvalidTokenError,
    JwksKeyResolver,
    KeyServiceUnavailableError,
    LogtoTokenVerifier,
)
from app.auth.principal import Principal
from app.models import User
from app.services.users import get_or_create_user

logger = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)


@lru_cache
def _verifier_for(issuer: str, audience: str, client_id: str, jwks_url: str) -> LogtoTokenVerifier:
    return LogtoTokenVerifier(
        issuer=issuer,
        audience=audience,
        client_id=client_id,
        keys=JwksKeyResolver(jwks_url),
    )


def get_token_verifier(settings: SettingsDep) -> LogtoTokenVerifier | None:
    if settings.auth_mode != "logto":
        return None
    return _verifier_for(
        settings.logto_issuer,
        settings.logto_api_resource,
        settings.logto_app_id,
        settings.logto_jwks_url,
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


async def get_principal(
    verifier: Annotated[LogtoTokenVerifier | None, Depends(get_token_verifier)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_dev_user: Annotated[str | None, Header()] = None,
) -> Principal:
    if verifier is None:  # AUTH_MODE=dev
        return dev_principal(x_dev_user)
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        # PyJWKClient fetches keys with blocking I/O, so keep it off the event loop.
        return await run_in_threadpool(verifier.verify, credentials.credentials)
    except InvalidTokenError as exc:
        # The reason only, never the token: this line names the cause of a 401 storm.
        # %r escapes control characters: the reason can carry an attacker-chosen kid.
        logger.warning("Rejected access token: %r", exc)
        raise _unauthorized("Invalid token") from exc
    except KeyServiceUnavailableError as exc:
        logger.error("Could not fetch Logto signing keys", exc_info=exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication service unavailable"
        ) from exc


PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def get_current_user(principal: PrincipalDep, session: SessionDep) -> User:
    return await get_or_create_user(session, principal.provider, principal.subject)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_scope(scope: str) -> DependsParam:
    async def check(principal: PrincipalDep) -> None:
        if scope not in principal.scopes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing scope: {scope}")

    return DependsParam(check)
