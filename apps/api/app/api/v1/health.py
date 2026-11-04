from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep, SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: SessionDep, settings: SettingsDep) -> dict[str, str]:
    _ = await session.execute(text("SELECT 1"))
    # git_sha lets CI check that a deploy is serving the exact commit it built.
    return {"status": "ok", "git_sha": settings.git_sha}
