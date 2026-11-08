from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import get_now
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.generation.base import CardGenerator
from app.generation.fake import FakeCardGenerator
from app.generation.llm_generator import LlmCardGenerator
from app.study.scheduler import Scheduler

SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Config is injected like any other dependency, so tests override it per app, not globally.
SettingsDep = Annotated[Settings, Depends(get_settings)]
NowDep = Annotated[datetime, Depends(get_now)]


def get_card_generator(settings: SettingsDep) -> CardGenerator:
    if settings.card_generator == "fake":
        return FakeCardGenerator()
    return LlmCardGenerator.from_settings(settings)

def get_scheduler(settings: SettingsDep) -> Scheduler:
    return Scheduler(fuzzing=settings.fsrs_fuzzing)
 
 
SchedulerDep = Annotated[Scheduler, Depends(get_scheduler)]

CardGeneratorDep = Annotated[CardGenerator, Depends(get_card_generator)]
