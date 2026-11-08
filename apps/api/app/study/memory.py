from app.models import Card
from app.study.scheduler import MemoryState


def memory_of(card: Card) -> MemoryState:
    # Not an assert: asserts vanish under `python -O`, leaving a draft to reach here as None.
    if card.fsrs_state is None or card.due_at is None:
        raise ValueError("drafts have no memory")
    return MemoryState(
        state=card.fsrs_state,
        step=card.fsrs_step,
        stability=card.stability,
        difficulty=card.difficulty,
        due_at=card.due_at,
        last_review_at=card.last_review_at,
    )


def apply_memory(card: Card, memory: MemoryState) -> None:
    card.fsrs_state = memory.state
    card.fsrs_step = memory.step
    card.stability = memory.stability
    card.difficulty = memory.difficulty
    card.due_at = memory.due_at
    card.last_review_at = memory.last_review_at
