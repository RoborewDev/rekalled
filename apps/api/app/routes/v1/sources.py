import uuid

from fastapi import APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_scope
from app.models import Source
from app.routes.deps import CardGeneratorDep, SessionDep, SettingsDep
from app.schemas.sources import CardOut, SourceCreate, SourceOut
from app.services import generation

router = APIRouter(tags=["sources"])


async def _source_out(session: AsyncSession, source: Source) -> SourceOut:
    cards = await generation.list_source_cards(session, source)
    return SourceOut(
        id=source.id,
        deck_id=source.deck_id,
        kind=source.kind,
        title=source.title,
        content=source.content,
        created_at=source.created_at,
        cards=[CardOut.model_validate(c) for c in cards],
    )


@router.post(
    "/decks/{deck_id}/sources",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_scope("cards:generate")],
)
async def create_text_source(
    deck_id: uuid.UUID,
    body: SourceCreate,
    session: SessionDep,
    user: CurrentUser,
    generator: CardGeneratorDep,
    settings: SettingsDep,
) -> SourceOut:
    source = await generation.create_source_and_generate(
        session,
        user,
        deck_id,
        text=body.text,
        title=body.title,
        generator=generator,
        max_chars=settings.max_source_chars,
        max_cards=settings.max_cards,
        max_per_day=settings.max_sources_per_day,
    )
    return await _source_out(session, source)


@router.get("/sources/{source_id}", dependencies=[require_scope("decks:read")])
async def get_source(source_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> SourceOut:
    source = await generation.get_source(session, user, source_id)
    return await _source_out(session, source)


@router.post("/sources/{source_id}/generate", dependencies=[require_scope("cards:generate")])
async def regenerate_source(
    source_id: uuid.UUID,
    session: SessionDep,
    user: CurrentUser,
    generator: CardGeneratorDep,
    settings: SettingsDep,
) -> SourceOut:
    source = await generation.regenerate(
        session, user, source_id, generator, max_cards=settings.max_cards
    )
    return await _source_out(session, source)
