import uuid

from fastapi import APIRouter

from app.api.deps import NowDep, SchedulerDep, SessionDep, SettingsDep
from app.auth.dependencies import CurrentUser, require_scope
from app.schemas.cards import ActiveCardOut
from app.schemas.study import ReviewCreate, StudyCard
from app.services import study as study_service
from app.services.cards import to_active_card_out

router = APIRouter(tags=["study"])


@router.get("/study/queue", dependencies=[require_scope("decks:read")])
async def get_study_queue(
    session: SessionDep,
    user: CurrentUser,
    scheduler: SchedulerDep,
    now: NowDep,
    settings: SettingsDep,
    deck_id: uuid.UUID | None = None,
) -> list[StudyCard]:
    return await study_service.get_queue(
        session,
        user,
        deck_id=deck_id,
        new_limit=settings.new_cards_per_session,
        scheduler=scheduler,
        now=now,
    )


@router.post("/reviews", dependencies=[require_scope("decks:write")])
async def submit_review(
    body: ReviewCreate, session: SessionDep, user: CurrentUser, scheduler: SchedulerDep, now: NowDep
) -> ActiveCardOut:
    card = await study_service.submit_review(
        session,
        user,
        review_id=body.review_id,
        card_id=body.card_id,
        rating=body.rating,
        scheduler=scheduler,
        now=now,
    )
    return to_active_card_out(card, scheduler, now)
