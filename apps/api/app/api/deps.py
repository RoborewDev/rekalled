from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.errors import ServiceUnavailableError
from app.generation.base import CardGenerator
from app.generation.fake import FakeCardGenerator

SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Config is injected like any other dependency, so tests override it per app, not globally.
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_card_generator(settings: SettingsDep) -> CardGenerator:
    if settings.card_generator == "fake":
        return FakeCardGenerator()
    raise ServiceUnavailableError("Card generation is not available yet")


CardGeneratorDep = Annotated[CardGenerator, Depends(get_card_generator)]
