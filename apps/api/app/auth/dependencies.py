from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.api.deps import SessionDep
from app.auth.dev import dev_principal
from app.auth.principal import Principal
from app.core.config import get_settings
from app.models import User
from app.services.users import get_or_create_user


async def get_principal(x_dev_user: Annotated[str | None, Header()] = None) -> Principal:
    settings = get_settings()
    if settings.auth_mode == "dev":
        return dev_principal(x_dev_user)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def get_current_user(principal: PrincipalDep, session: SessionDep) -> User:
    return await get_or_create_user(session, principal.provider, principal.subject)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_scope(scope: str):
    async def check(principal: PrincipalDep) -> None:
        if scope not in principal.scopes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing scope: {scope}")

    return Depends(check)
