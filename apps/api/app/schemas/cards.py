import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# Generous for a flash card, but bounded: every field is stored and sent to the browser.
MAX_CARD_TEXT = 2_000


class KeptDraft(BaseModel):
    card_id: uuid.UUID
    question: str = Field(min_length=1, max_length=MAX_CARD_TEXT)
    answer: str = Field(min_length=1, max_length=MAX_CARD_TEXT)


class DraftCommit(BaseModel):
    """Every draft of the Source not listed in `kept` is deleted."""

    kept: list[KeptDraft]


class CardUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1, max_length=MAX_CARD_TEXT)
    answer: str | None = Field(default=None, min_length=1, max_length=MAX_CARD_TEXT)


class ActiveCardOut(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    source_id: uuid.UUID | None
    question: str
    answer: str
    source_excerpt: str | None
    due_at: datetime
    reps: int
    lapses: int
    memory_score: float | None  # None until the card has been studied once
