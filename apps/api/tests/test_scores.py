import uuid

from httpx import AsyncClient, Response

from tests.api_types import (
    DeckStatsJson,
    DeckWithStatsJson,
    StudySummaryJson,
    json_list,
    json_object,
)
from tests.conftest import Clock
from tests.helpers import make_active_cards, make_deck

EASY = 4


async def review(client: AsyncClient, card_id: str, rating: int = EASY) -> Response:
    body = {"review_id": str(uuid.uuid4()), "card_id": card_id, "rating": rating}
    return await client.post("/v1/reviews", json=body)


async def deck_stats(client: AsyncClient, deck_id: str) -> DeckStatsJson:
    decks = json_list(await client.get("/v1/decks"), DeckWithStatsJson)
    return next(d["stats"] for d in decks if d["id"] == deck_id)


async def test_an_empty_deck_has_empty_stats(client: AsyncClient) -> None:
    deck_id = await make_deck(client, "Empty")

    stats = await deck_stats(client, deck_id)

    assert stats["score"] is None
    assert stats["total"] == stats["due"] == 0


async def test_a_deck_of_new_cards_has_no_score_yet(client: AsyncClient) -> None:
    deck_id, _ = await make_active_cards(client)

    stats = await deck_stats(client, deck_id)

    assert stats["score"] is None
    assert stats["total"] == stats["new"] == 3
    assert stats["bands"] == {"strong": 0, "fading": 0, "weak": 0, "new": 3}


async def test_deck_score_is_the_mean_of_studied_cards_and_fades(
    client: AsyncClient, clock: Clock
) -> None:
    deck_id, cards = await make_active_cards(client)
    _ = await review(client, cards[0]["id"])

    score = (await deck_stats(client, deck_id))["score"]
    assert score is not None
    assert score == 1.0

    clock.advance(days=30)  # Easy on a new card → ~79% after 30 days (py-fsrs fixture)
    stats = await deck_stats(client, deck_id)
    score = stats["score"]
    assert score is not None

    assert round(score, 3) == 0.792
    assert stats["bands"] == {"strong": 0, "fading": 1, "weak": 0, "new": 2}
    assert stats["due"] == 1


async def test_study_summary_counts_todays_reviews_and_forecasts_the_week(
    client: AsyncClient, clock: Clock
) -> None:
    _, cards = await make_active_cards(client)
    _ = await review(client, cards[0]["id"], rating=3)  # Good → due in 10 minutes (today)
    _ = await review(client, cards[1]["id"], rating=4)  # Easy → due in 8 days (outside the week)

    summary = json_object(await client.get("/v1/study/summary"), StudySummaryJson)

    assert summary["reviews_today"] == 2
    assert summary["studied"] == 2
    assert summary["new"] == 1
    assert summary["forecast_7d"] == [1, 0, 0, 0, 0, 0, 0]

    clock.advance(days=1)
    later = json_object(await client.get("/v1/study/summary"), StudySummaryJson)
    assert later["reviews_today"] == 0
