import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Card, Deck, ReviewLog, User
from app.schemas.study import DeckStats, StudyCard, StudySummary
from app.study.memory import apply_memory, memory_of
from app.study.scheduler import Scheduler, is_lapse
from app.study.scores import deck_stats, forecast


async def get_queue(
    session: AsyncSession,
    user: User,
    *,
    deck_id: uuid.UUID | None,
    new_limit: int,
    scheduler: Scheduler,
    now: datetime,
) -> list[StudyCard]:
    """Due cards first (most overdue first), then up to `new_limit` new cards."""
    base = (
        select(Card, Deck.name)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Card.owner_id == user.id, Card.status == "active")
    )
    if deck_id is not None:
        base = base.where(Card.deck_id == deck_id)

    due = await session.execute(
        base.where(Card.last_review_at.is_not(None), Card.due_at <= now).order_by(Card.due_at)
    )
    new = await session.execute(
        base.where(Card.last_review_at.is_(None))
        .order_by(Card.created_at, Card.position)
        .limit(new_limit)
    )
    return [_study_card(card, deck_name, scheduler, now) for card, deck_name in [*due, *new]]


async def submit_review(
    session: AsyncSession,
    user: User,
    *,
    review_id: uuid.UUID,
    card_id: uuid.UUID,
    rating: int,
    scheduler: Scheduler,
    now: datetime,
) -> Card:
    # Lock the card row so two concurrent reviews of the same card can't interleave.
    card = await session.scalar(
        select(Card)
        .where(Card.id == card_id, Card.owner_id == user.id, Card.status == "active")
        .with_for_update()
    )
    if card is None:
        raise NotFoundError("Card not found")

    before = memory_of(card)
    after = scheduler.review(before, rating, now)

    inserted = await session.scalar(
        insert(ReviewLog)
        .values(
            id=review_id,
            owner_id=user.id,
            card_id=card.id,
            rating=rating,
            reviewed_at=now,
            fsrs_state=after.state,
            stability=after.stability,
            difficulty=after.difficulty,
            due_at=after.due_at,
        )
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(ReviewLog.id)
    )
    if inserted is None:
        # Seen this review_id before: a retry. Return the card unchanged.
        await session.commit()
        return card

    apply_memory(card, after)
    card.reps += 1
    if is_lapse(before, rating):
        card.lapses += 1
    await session.commit()
    await session.refresh(card)
    return card


def _study_card(card: Card, deck_name: str, scheduler: Scheduler, now: datetime) -> StudyCard:
    memory = memory_of(card)
    return StudyCard(
        id=card.id,
        deck_id=card.deck_id,
        deck_name=deck_name,
        question=card.question,
        answer=card.answer,
        source_excerpt=card.source_excerpt,
        is_new=card.last_review_at is None,
        memory_score=scheduler.retrievability(memory, now),
        next_due={str(r): due for r, due in scheduler.preview(memory, now).items()},
    )

async def _active_cards(session: AsyncSession, user: User) -> list[Card]:
    result = await session.scalars(
        select(Card).where(Card.owner_id == user.id, Card.status == "active")
    )
    return list(result)
 
 
async def stats_by_deck(
    session: AsyncSession, user: User, scheduler: Scheduler, now: datetime
) -> dict[uuid.UUID, DeckStats]:
    """Stats for every deck the user owns, including decks with no cards yet."""
    deck_ids = await session.scalars(select(Deck.id).where(Deck.owner_id == user.id))
    by_deck: dict[uuid.UUID, list[Card]] = {deck_id: [] for deck_id in deck_ids}
    for card in await _active_cards(session, user):
        by_deck[card.deck_id].append(card)
    return {deck_id: deck_stats(cards, scheduler, now) for deck_id, cards in by_deck.items()}
 
 
async def summary(
    session: AsyncSession, user: User, scheduler: Scheduler, now: datetime
) -> StudySummary:
    cards = await _active_cards(session, user)
    overall = deck_stats(cards, scheduler, now)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    reviews_today = await session.scalar(
        select(func.count())
        .select_from(ReviewLog)
        .where(ReviewLog.owner_id == user.id, ReviewLog.reviewed_at >= start_of_today)
    )
    return StudySummary(
        score=overall.score,
        due=overall.due,
        new=overall.new,
        studied=overall.total - overall.new,
        reviews_today=reviews_today or 0,
        forecast_7d=forecast(cards, now),
    )