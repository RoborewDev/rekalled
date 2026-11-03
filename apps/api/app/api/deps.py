from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Config is injected like any other dependency, so tests override it per app, not globally.
SettingsDep = Annotated[Settings, Depends(get_settings)]
