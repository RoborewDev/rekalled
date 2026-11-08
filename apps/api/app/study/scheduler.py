"""The only module that imports py-fsrs. Pure functions of (state, rating, time): no database."""

from dataclasses import dataclass
from datetime import UTC, datetime

import fsrs

RATINGS = (1, 2, 3, 4)  # Again, Hard, Good, Easy


@dataclass(frozen=True)
class MemoryState:
    """Mirrors the FSRS columns on the cards table."""

    state: int  # 1 Learning, 2 Review, 3 Relearning
    step: int | None
    stability: float | None
    difficulty: float | None
    due_at: datetime
    last_review_at: datetime | None


class Scheduler:
    def __init__(self, *, fuzzing: bool = True, desired_retention: float = 0.9) -> None:
        self._fsrs: fsrs.Scheduler = fsrs.Scheduler(
            desired_retention=desired_retention, enable_fuzzing=fuzzing
        )

    def new_card(self, now: datetime) -> MemoryState:
        return MemoryState(
            state=fsrs.State.Learning.value,
            step=0,
            stability=None,
            difficulty=None,
            due_at=_utc(now),
            last_review_at=None,
        )

    def review(self, memory: MemoryState, rating: int, now: datetime) -> MemoryState:
        card, _log = self._fsrs.review_card(_to_fsrs(memory), fsrs.Rating(rating), _utc(now))
        return _from_fsrs(card)

    def preview(self, memory: MemoryState, now: datetime) -> dict[int, datetime]:
        """When the card would be due next for each rating. Shown under the buttons."""
        return {rating: self.review(memory, rating, now).due_at for rating in RATINGS}

    def retrievability(self, memory: MemoryState, now: datetime) -> float | None:
        """Chance of recall right now (the Memory score). None for a never-studied card."""
        if memory.last_review_at is None:
            return None
        return self._fsrs.get_card_retrievability(_to_fsrs(memory), _utc(now))


def _utc(dt: datetime) -> datetime:
    # py-fsrs only accepts UTC. Callers can pass any aware datetime.
    if dt.tzinfo is None:
        raise ValueError("Scheduler needs timezone-aware datetimes")
    return dt.astimezone(UTC)


def _to_fsrs(m: MemoryState) -> fsrs.Card:
    return fsrs.Card(
        card_id=0,  # unused; avoids py-fsrs generating an id from the clock
        state=fsrs.State(m.state),
        step=m.step,
        stability=m.stability,
        difficulty=m.difficulty,
        due=_utc(m.due_at),
        last_review=_utc(m.last_review_at) if m.last_review_at else None,
    )


def _from_fsrs(c: fsrs.Card) -> MemoryState:
    return MemoryState(
        state=c.state.value,
        step=c.step,
        stability=c.stability,
        difficulty=c.difficulty,
        due_at=c.due,
        last_review_at=c.last_review,
    )
