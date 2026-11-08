import uuid

from tests.helpers import make_active_cards

EASY = 4


async def review(client, card_id: str, rating: int = EASY):
    body = {"review_id": str(uuid.uuid4()), "card_id": card_id, "rating": rating}
    return await client.post("/v1/reviews", json=body)


async def deck_stats(client, deck_id: str) -> dict:
    decks = (await client.get("/v1/decks")).json()
    return next(d["stats"] for d in decks if d["id"] == deck_id)


async def test_an_empty_deck_has_empty_stats(client):
    deck_id = (await client.post("/v1/decks", json={"name": "Empty"})).json()["id"]

    stats = await deck_stats(client, deck_id)

    assert stats["score"] is None
    assert stats["total"] == stats["due"] == 0


async def test_a_deck_of_new_cards_has_no_score_yet(client):
    deck_id, _ = await make_active_cards(client)

    stats = await deck_stats(client, deck_id)

    assert stats["score"] is None
    assert stats["total"] == stats["new"] == 3
    assert stats["bands"] == {"strong": 0, "fading": 0, "weak": 0, "new": 3}


async def test_deck_score_is_the_mean_of_studied_cards_and_fades(client, clock):
    deck_id, cards = await make_active_cards(client)
    await review(client, cards[0]["id"])

    assert (await deck_stats(client, deck_id))["score"] == 1.0

    clock.advance(days=30)  # Easy on a new card → ~79% after 30 days (py-fsrs fixture)
    stats = await deck_stats(client, deck_id)

    assert round(stats["score"], 3) == 0.792
    assert stats["bands"] == {"strong": 0, "fading": 1, "weak": 0, "new": 2}
    assert stats["due"] == 1


async def test_study_summary_counts_todays_reviews_and_forecasts_the_week(client, clock):
    _, cards = await make_active_cards(client)
    await review(client, cards[0]["id"], rating=3)  # Good → due in 10 minutes (today)
    await review(client, cards[1]["id"], rating=4)  # Easy → due in 8 days (outside the week)

    summary = (await client.get("/v1/study/summary")).json()

    assert summary["reviews_today"] == 2
    assert summary["studied"] == 2
    assert summary["new"] == 1
    assert summary["forecast_7d"] == [1, 0, 0, 0, 0, 0, 0]

    clock.advance(days=1)
    assert (await client.get("/v1/study/summary")).json()["reviews_today"] == 0
