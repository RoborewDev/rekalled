import uuid

from tests.helpers import make_active_cards

AGAIN, GOOD, EASY = 1, 3, 4


async def review(client, card_id: str, rating: int, review_id: str | None = None):
    return await client.post(
        "/v1/reviews",
        json={"review_id": review_id or str(uuid.uuid4()), "card_id": card_id, "rating": rating},
    )


async def test_new_cards_are_offered_straight_after_saving(client):
    await make_active_cards(client)

    queue = (await client.get("/v1/study/queue")).json()

    assert len(queue) == 3
    assert all(c["is_new"] for c in queue)
    assert queue[0]["next_due"]["3"] == "2026-11-02T09:10:00Z"  # Good → 10 minutes


async def test_rating_a_card_reschedules_it_and_gives_it_a_memory_score(client):
    _, cards = await make_active_cards(client)

    response = await review(client, cards[0]["id"], EASY)

    assert response.status_code == 200
    card = response.json()
    assert card["due_at"] == "2026-11-10T09:00:00Z"  # Easy on a new card → 8 days
    assert card["memory_score"] == 1.0
    assert card["reps"] == 1


async def test_due_cards_come_before_new_cards(client, clock):
    _, cards = await make_active_cards(client)
    await review(client, cards[2]["id"], EASY)  # due in 8 days

    clock.advance(days=9)
    queue = (await client.get("/v1/study/queue")).json()

    assert queue[0]["id"] == cards[2]["id"]
    assert queue[0]["is_new"] is False
    assert [c["is_new"] for c in queue[1:]] == [True, True]


async def test_a_card_not_yet_due_is_not_in_the_queue(client):
    _, cards = await make_active_cards(client)

    await review(client, cards[0]["id"], EASY)
    queue = (await client.get("/v1/study/queue")).json()

    assert cards[0]["id"] not in [c["id"] for c in queue]


async def test_new_cards_are_limited_per_session(client):
    text = " ".join(f"Fact number {i} is true." for i in range(15))
    await make_active_cards(client, text=text)

    queue = (await client.get("/v1/study/queue")).json()

    assert len(queue) == 10


async def test_queue_can_be_filtered_to_one_deck(client):
    deck_a, _ = await make_active_cards(client, deck_name="A")
    await make_active_cards(client, deck_name="B")

    queue = (await client.get("/v1/study/queue", params={"deck_id": deck_a})).json()

    assert {c["deck_name"] for c in queue} == {"A"}


async def test_repeating_a_review_id_changes_nothing(client):
    _, cards = await make_active_cards(client)
    review_id = str(uuid.uuid4())

    first = (await review(client, cards[0]["id"], GOOD, review_id)).json()
    retry = (await review(client, cards[0]["id"], GOOD, review_id)).json()

    assert retry == first
    assert retry["reps"] == 1


async def test_rating_must_be_between_1_and_4(client):
    _, cards = await make_active_cards(client)

    assert (await review(client, cards[0]["id"], 5)).status_code == 422


async def test_other_users_cards_never_appear_and_cannot_be_reviewed(client):
    other = {"X-Dev-User": "dev|other"}
    _, cards = await make_active_cards(client)

    queue = (await client.get("/v1/study/queue", headers=other)).json()
    response = await client.post(
        "/v1/reviews",
        json={"review_id": str(uuid.uuid4()), "card_id": cards[0]["id"], "rating": GOOD},
        headers=other,
    )

    assert queue == []
    assert response.status_code == 404


async def test_again_on_a_review_card_counts_a_lapse(client, clock):
    _, cards = await make_active_cards(client)
    await review(client, cards[0]["id"], EASY)
    clock.advance(days=8)

    card = (await review(client, cards[0]["id"], AGAIN)).json()

    assert card["lapses"] == 1
