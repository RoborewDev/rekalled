import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Deck, User


async def list_decks(session: AsyncSession, user: User) -> list[Deck]:
    result = await session.scalars(
        select(Deck).where(Deck.owner_id == user.id).order_by(Deck.created_at)
    )
    return list(result)


async def create_deck(session: AsyncSession, user: User, name: str) -> Deck:
    deck = Deck(owner_id=user.id, name=name)
    session.add(deck)
    await session.commit()
    await session.refresh(deck)
    return deck


async def get_deck(session: AsyncSession, user: User, deck_id: uuid.UUID) -> Deck:
    # Filtering by owner here is what makes other users' decks a 404, not a 403.
    deck = await session.scalar(select(Deck).where(Deck.id == deck_id, Deck.owner_id == user.id))
    if deck is None:
        raise NotFoundError("Deck not found")
    return deck


async def rename_deck(session: AsyncSession, user: User, deck_id: uuid.UUID, name: str) -> Deck:
    deck = await get_deck(session, user, deck_id)
    deck.name = name
    await session.commit()
    await session.refresh(deck)
    return deck


async def delete_deck(session: AsyncSession, user: User, deck_id: uuid.UUID) -> None:
    deck = await get_deck(session, user, deck_id)
    await session.delete(deck)
    await session.commit()
