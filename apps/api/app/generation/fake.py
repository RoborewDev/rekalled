import re

from app.generation.base import CardDraft, GenerationError


class FakeCardGenerator:
    """Deterministic generator for tests, E2E and offline dev: one card per sentence."""

    async def generate(self, text: str, *, max_cards: int) -> list[CardDraft]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        return [
            CardDraft(
                question=f"What does the text say about “{' '.join(s.split()[:4])}”?",
                answer=s,
                source_excerpt=s,
            )
            for s in sentences[:max_cards]
        ]


class FailingCardGenerator:
    async def generate(self, text: str, *, max_cards: int) -> list[CardDraft]:
        # These parameters are part of the generator interface; this one fails before using them.
        del text, max_cards
        raise GenerationError("Model unavailable")
