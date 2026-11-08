import uuid

from fastapi import APIRouter, status

from app.api.deps import NowDep, SchedulerDep, SessionDep
from app.auth.dependencies import CurrentUser, require_scope
from app.schemas.cards import ActiveCardOut, CardUpdate, DraftCommit
from app.services import cards as card_service

router = APIRouter(tags=["cards"])


@router.post("/sources/{source_id}/drafts/commit", dependencies=[require_scope("decks:write")])
async def commit_drafts(
    source_id: uuid.UUID,
    body: DraftCommit,
    session: SessionDep,
    user: CurrentUser,
    scheduler: SchedulerDep,
    now: NowDep,
) -> list[ActiveCardOut]:
    cards = await card_service.commit_drafts(
        session, user, source_id, body.kept, scheduler=scheduler, now=now
    )
    return [card_service.to_active_card_out(c, scheduler, now) for c in cards]


@router.get("/decks/{deck_id}/cards", dependencies=[require_scope("decks:read")])
async def list_deck_cards(
    deck_id: uuid.UUID, session: SessionDep, user: CurrentUser, scheduler: SchedulerDep, now: NowDep
) -> list[ActiveCardOut]:
    cards = await card_service.list_active_cards(session, user, deck_id)
    return [card_service.to_active_card_out(c, scheduler, now) for c in cards]


@router.patch("/cards/{card_id}", dependencies=[require_scope("decks:write")])
async def update_card(
    card_id: uuid.UUID,
    body: CardUpdate,
    session: SessionDep,
    user: CurrentUser,
    scheduler: SchedulerDep,
    now: NowDep,
) -> ActiveCardOut:
    card = await card_service.update_card(session, user, card_id, body)
    return card_service.to_active_card_out(card, scheduler, now)


@router.delete(
    "/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_scope("decks:write")],
)
async def delete_card(card_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> None:
    await card_service.delete_card(session, user, card_id)
