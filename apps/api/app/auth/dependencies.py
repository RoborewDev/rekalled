from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.params import Depends as DependsParam

from app.api.deps import SessionDep, SettingsDep
from app.auth.dev import dev_principal
from app.auth.principal import Principal
from app.models import User
from app.services.users import get_or_create_user


async def get_principal(
    settings: SettingsDep, x_dev_user: Annotated[str | None, Header()] = None
) -> Principal:
    if settings.auth_mode == "dev":
        return dev_principal(x_dev_user)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def get_current_user(principal: PrincipalDep, session: SessionDep) -> User:
    return await get_or_create_user(session, principal.provider, principal.subject)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_scope(scope: str) -> DependsParam:
    async def check(principal: PrincipalDep) -> None:
        if scope not in principal.scopes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing scope: {scope}")

    return DependsParam(check)
