import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Card, User
from app.schemas.cards import ActiveCardOut, CardUpdate, KeptDraft
from app.services.decks import get_deck
from app.services.generation import get_source
from app.study.memory import apply_memory, memory_of
from app.study.scheduler import Scheduler


async def commit_drafts(
    session: AsyncSession,
    user: User,
    source_id: uuid.UUID,
    kept: list[KeptDraft],
    *,
    scheduler: Scheduler,
    now: datetime,
) -> list[Card]:
    """The draft check, in one transaction. Running it twice is harmless."""
    source = await get_source(session, user, source_id)
    # Lock the drafts so two concurrent commits cannot both decide what to keep.
    drafts = await session.scalars(
        select(Card).where(Card.source_id == source.id, Card.status == "draft").with_for_update()
    )
    edits = {k.card_id: k for k in kept}

    for card in drafts:
        edit = edits.get(card.id)
        if edit is None:
            await session.delete(card)
            continue
        card.question, card.answer = edit.question, edit.answer
        card.status = "active"
        apply_memory(card, scheduler.new_card(now))  # due now: study it straight away
    await session.commit()

    result = await session.scalars(
        select(Card)
        .where(Card.source_id == source.id, Card.status == "active")
        .order_by(Card.position)
    )
    return list(result)


async def list_active_cards(session: AsyncSession, user: User, deck_id: uuid.UUID) -> list[Card]:
    deck = await get_deck(session, user, deck_id)
    result = await session.scalars(
        select(Card)
        .where(Card.deck_id == deck.id, Card.status == "active")
        .order_by(Card.created_at, Card.position)
    )
    return list(result)


async def get_card(
    session: AsyncSession, user: User, card_id: uuid.UUID, *, status: str = "active"
) -> Card:
    """Load a card the user may edit. Drafts are excluded: they have no memory state yet."""
    card = await session.scalar(
        select(Card).where(Card.id == card_id, Card.owner_id == user.id, Card.status == status)
    )
    if card is None:
        raise NotFoundError("Card not found")
    return card


async def update_card(
    session: AsyncSession, user: User, card_id: uuid.UUID, changes: CardUpdate
) -> Card:
    card = await get_card(session, user, card_id)
    if changes.question is not None:
        card.question = changes.question
    if changes.answer is not None:
        card.answer = changes.answer
    await session.commit()
    await session.refresh(card)
    return card


async def delete_card(session: AsyncSession, user: User, card_id: uuid.UUID) -> None:
    await session.delete(await get_card(session, user, card_id))
    await session.commit()


def to_active_card_out(card: Card, scheduler: Scheduler, now: datetime) -> ActiveCardOut:
    memory = memory_of(card)
    return ActiveCardOut(
        id=card.id,
        deck_id=card.deck_id,
        source_id=card.source_id,
        question=card.question,
        answer=card.answer,
        source_excerpt=card.source_excerpt,
        due_at=memory.due_at,
        reps=card.reps,
        lapses=card.lapses,
        memory_score=scheduler.retrievability(memory, now),
    )
