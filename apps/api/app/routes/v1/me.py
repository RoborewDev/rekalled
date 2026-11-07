from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, PrincipalDep
from app.schemas.me import Me

router = APIRouter(tags=["me"])


@router.get("/me")
async def get_me(user: CurrentUser, principal: PrincipalDep) -> Me:
    return Me(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        scopes=sorted(principal.scopes),
    )
