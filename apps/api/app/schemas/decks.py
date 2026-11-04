import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class DeckCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class DeckUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class DeckOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
