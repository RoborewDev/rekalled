import logging
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    GenerationFailedError,
    NotFoundError,
    QuotaExceededError,
    SourceTooLongError,
)
from app.generation.base import CardGenerator, GenerationError
from app.models import Card, Source, User
from app.services.decks import get_deck

logger = logging.getLogger(__name__)


async def create_source_and_generate(
    session: AsyncSession,
    user: User,
    deck_id: uuid.UUID,
    *,
    text: str,
    title: str | None,
    generator: CardGenerator,
    max_chars: int,
    max_cards: int,
    max_per_day: int,
    kind: str = "text",
) -> Source:
    if len(text) > max_chars:
        raise SourceTooLongError(f"Text is {len(text)} characters; the limit is {max_chars}")
    deck = await get_deck(session, user, deck_id)
    await check_daily_quota(session, user, max_per_day)

    # Save the Source first, so a failed Generation can be retried without re-pasting.
    source = Source(owner_id=user.id, deck_id=deck.id, kind=kind, title=title, content=text)
    session.add(source)
    await session.commit()

    await _generate_drafts(session, source, generator, max_cards=max_cards)
    return source


async def check_daily_quota(session: AsyncSession, user: User, max_per_day: int) -> None:
    added_today = await session.scalar(
        select(func.count())
        .select_from(Source)
        .where(Source.owner_id == user.id, Source.created_at >= func.now() - timedelta(days=1))
    )
    if (added_today or 0) >= max_per_day:
        raise QuotaExceededError(f"You can add {max_per_day} sources a day. Try again tomorrow.")


async def regenerate(
    session: AsyncSession,
    user: User,
    source_id: uuid.UUID,
    generator: CardGenerator,
    *,
    max_cards: int,
) -> Source:
    source = await get_source(session, user, source_id)
    if not await list_source_cards(session, source):
        await _generate_drafts(session, source, generator, max_cards=max_cards)
    return source


async def get_source(session: AsyncSession, user: User, source_id: uuid.UUID) -> Source:
    source = await session.scalar(
        select(Source).where(Source.id == source_id, Source.owner_id == user.id)
    )
    if source is None:
        raise NotFoundError("Source not found")
    return source


async def list_source_cards(session: AsyncSession, source: Source) -> list[Card]:
    result = await session.scalars(
        select(Card).where(Card.source_id == source.id).order_by(Card.position)
    )
    return list(result)


async def _generate_drafts(
    session: AsyncSession, source: Source, generator: CardGenerator, *, max_cards: int
) -> None:
    try:
        drafts = await generator.generate(source.content, max_cards=max_cards)
    except GenerationError as exc:
        # The provider's message can carry status codes, model names or response bodies:
        # log it here, send the client a generic one.
        logger.warning("Card generation failed for source %s", source.id, exc_info=exc)
        raise GenerationFailedError(
            "Card generation failed. Try again.", source_id=str(source.id)
        ) from exc

    session.add_all(
        Card(
            owner_id=source.owner_id,
            deck_id=source.deck_id,
            source_id=source.id,
            status="draft",
            position=i,
            question=d.question,
            answer=d.answer,
            source_excerpt=d.source_excerpt,
        )
        for i, d in enumerate(drafts)
    )
    await session.commit()
