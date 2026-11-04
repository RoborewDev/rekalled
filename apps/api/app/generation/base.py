from typing import Protocol

from pydantic import BaseModel, Field


class CardDraft(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    source_excerpt: str = Field(min_length=1)


class GenerationError(Exception):
    """The generator could not produce usable cards (model down, bad output, ...)."""


class CardGenerator(Protocol):
    async def generate(self, text: str, *, max_cards: int) -> list[CardDraft]: ...
