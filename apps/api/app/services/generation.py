import logging
import uuid
from datetime import timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    GenerationFailedError,
    NotFoundError,
    QuotaExceededError,
    SourceTooLongError,
)
from app.generation.base import CardGenerator, GenerationError
from app.models import Card, GenerationLog, Source, User
from app.services.decks import get_deck

logger = logging.getLogger(__name__)


async def _lock(session: AsyncSession, key: str) -> None:
    """Serialise work for one user/source; Postgres releases the lock at transaction end."""
    _ = await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}
    )


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
    await session.flush()  # the reservation below needs source.id
    # The spend is reserved in the same transaction as the quota count above, so parallel
    # requests cannot both pass the check. _generate_drafts releases it if the model fails.
    spend = GenerationLog(owner_id=user.id, source_id=source.id)
    session.add(spend)
    await session.commit()

    await _generate_drafts(session, source, generator, max_cards=max_cards, spend=spend)
    return source


async def check_daily_quota(session: AsyncSession, user: User, max_per_day: int) -> None:
    # The count and the reservation insert must be atomic, or parallel requests can both
    # pass. The caller inserts the GenerationLog in this same transaction.
    await _lock(session, f"user:{user.id}")
    # GenerationLog, not Source: a regeneration spends model credit too, and a Source that
    # only exists because generation failed must not count against the user.
    spent_today = await session.scalar(
        select(func.count())
        .select_from(GenerationLog)
        .where(
            GenerationLog.owner_id == user.id,
            GenerationLog.created_at >= func.now() - timedelta(days=1),
        )
    )
    if (spent_today or 0) >= max_per_day:
        raise QuotaExceededError(
            f"You can run card generation {max_per_day} times a day. Try again tomorrow."
        )


async def regenerate(
    session: AsyncSession,
    user: User,
    source_id: uuid.UUID,
    generator: CardGenerator,
    *,
    max_cards: int,
    max_per_day: int,
) -> Source:
    source = await get_source(session, user, source_id)
    # The user lock is taken before the source lock, matching create_source_and_generate.
    # Advisory xact locks are re-entrant within a transaction, so check_daily_quota can
    # re-acquire it below.
    await _lock(session, f"user:{user.id}")
    # Hold the source lock across the emptiness check and the insert.
    await _lock(session, f"source:{source.id}")
    if await list_source_cards(session, source):
        # Existing cards need no model run, so no quota is spent: a capped user can still
        # read them back (and retry a lost response to the last permitted generation).
        return source
    # A regeneration spends model credit like a creation, so it shares the daily cap. One
    # transaction from the quota count to the spend insert: atomic, like the create path,
    # because there is no intermediate commit here.
    await check_daily_quota(session, user, max_per_day)
    spend = GenerationLog(owner_id=source.owner_id, source_id=source.id)
    session.add(spend)
    await _generate_drafts(session, source, generator, max_cards=max_cards, spend=spend)
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
        select(Card)
        .where(Card.source_id == source.id, Card.owner_id == source.owner_id)
        .order_by(Card.position, Card.created_at, Card.id)
    )
    return list(result)


async def _generate_drafts(
    session: AsyncSession,
    source: Source,
    generator: CardGenerator,
    *,
    max_cards: int,
    spend: GenerationLog,
) -> None:
    await _lock(session, f"source:{source.id}")
    try:
        drafts = await generator.generate(source.content, max_cards=max_cards)
    except GenerationError as exc:
        # Release the reservation: a failed run must not count against the daily cap, or
        # the retry would be charged for our outage. (Identity delete, not a WHERE on the
        # source: an earlier successful generation's log must survive.)
        await session.delete(spend)
        await session.commit()
        # The provider's message can carry status codes, model names or response bodies:
        # log it here, send the client a generic one.
        logger.warning("Card generation failed for source %s", source.id, exc_info=exc)
        raise GenerationFailedError(
            "Card generation failed. Try again.", source_id=str(source.id)
        ) from exc
    except Exception:
        # GenerationError is the generator's own failure type; anything else (transport
        # error, raw library error, draft validation) must not burn quota either. Release
        # the reservation and let the unexpected error propagate as-is.
        await session.delete(spend)
        await session.commit()
        logger.exception("Card generation raised unexpectedly for source %s", source.id)
        raise

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
    await session.commit()  # cards, plus the reservation when it is still pending
