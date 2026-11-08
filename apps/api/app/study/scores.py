"""Memory scores. Computed when read, never stored, because they fall as time passes."""

from collections.abc import Iterable
from datetime import datetime, timedelta

from app.models import Card
from app.schemas.study import Bands, DeckStats
from app.study.memory import memory_of
from app.study.scheduler import Scheduler

STRONG, WEAK = 0.9, 0.75


def deck_stats(cards: Iterable[Card], scheduler: Scheduler, now: datetime) -> DeckStats:
    scores: list[float] = []
    new = due = 0
    for card in cards:
        score = scheduler.retrievability(memory_of(card), now)
        if score is None:
            new += 1
            continue
        scores.append(score)
        if card.due_at is not None and card.due_at <= now:
            due += 1
    return DeckStats(
        score=mean(scores),
        due=due,
        new=new,
        total=len(scores) + new,
        bands=Bands(
            strong=sum(s >= STRONG for s in scores),
            fading=sum(WEAK <= s < STRONG for s in scores),
            weak=sum(s < WEAK for s in scores),
            new=new,
        ),
    )


def forecast(cards: Iterable[Card], now: datetime, days: int = 7) -> list[int]:
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    counts = [0] * days
    for card in cards:
        if card.last_review_at is None or card.due_at is None:
            continue
        day = max(0, (card.due_at - start_of_today) // timedelta(days=1))
        if day < days:
            counts[day] += 1
    return counts


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
