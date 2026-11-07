import uuid

from fastapi import APIRouter, status

from app.routes.deps import SessionDep
from app.auth.dependencies import CurrentUser, require_scope
from app.schemas.decks import DeckCreate, DeckOut, DeckUpdate
from app.services import decks as deck_service

router = APIRouter(prefix="/decks", tags=["decks"])

read = [require_scope("decks:read")]
write = [require_scope("decks:write")]


@router.get("", dependencies=read)
async def list_decks(session: SessionDep, user: CurrentUser) -> list[DeckOut]:
    decks = await deck_service.list_decks(session, user)
    return [DeckOut.model_validate(d) for d in decks]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=write)
async def create_deck(body: DeckCreate, session: SessionDep, user: CurrentUser) -> DeckOut:
    deck = await deck_service.create_deck(session, user, body.name)
    return DeckOut.model_validate(deck)


@router.get("/{deck_id}", dependencies=read)
async def get_deck(deck_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> DeckOut:
    return DeckOut.model_validate(await deck_service.get_deck(session, user, deck_id))


@router.patch("/{deck_id}", dependencies=write)
async def rename_deck(
    deck_id: uuid.UUID, body: DeckUpdate, session: SessionDep, user: CurrentUser
) -> DeckOut:
    deck = await deck_service.rename_deck(session, user, deck_id, body.name)
    return DeckOut.model_validate(deck)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=write)
async def delete_deck(deck_id: uuid.UUID, session: SessionDep, user: CurrentUser) -> None:
    await deck_service.delete_deck(session, user, deck_id)
