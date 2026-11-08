import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StudyCard(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    deck_name: str
    question: str
    answer: str
    source_excerpt: str | None
    is_new: bool
    memory_score: float | None
    # When the card would be due next for each rating. Keys are "1".."4".
    next_due: dict[str, datetime]


class ReviewCreate(BaseModel):
    review_id: uuid.UUID  # crypto.randomUUID() in the browser; retries reuse it
    card_id: uuid.UUID
    rating: Literal[1, 2, 3, 4]
