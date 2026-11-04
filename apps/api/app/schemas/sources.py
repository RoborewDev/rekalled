import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    # A hard parse ceiling. The friendly 413 at max_source_chars is checked in the service.
    text: str = Field(min_length=1, max_length=200_000)


class CardOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    source_id: uuid.UUID | None
    status: str
    question: str
    answer: str
    source_excerpt: str | None


class SourceOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    kind: str
    title: str | None
    content: str
    created_at: datetime
    cards: list[CardOut]
