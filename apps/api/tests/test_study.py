import uuid

from httpx import AsyncClient, Response

from tests.api_types import ActiveCardJson, StudyCardJson, json_list, json_object
from tests.conftest import Clock
from tests.helpers import make_active_cards

AGAIN, GOOD, EASY = 1, 3, 4


async def review(
    client: AsyncClient, card_id: str, rating: int, review_id: str | None = None
) -> Response:
    return await client.post(
        "/v1/reviews",
        json={"review_id": review_id or str(uuid.uuid4()), "card_id": card_id, "rating": rating},
    )


async def test_new_cards_are_offered_straight_after_saving(client: AsyncClient) -> None:
    _ = await make_active_cards(client)

    queue = json_list(await client.get("/v1/study/queue"), StudyCardJson)

    assert len(queue) == 3
    assert all(c["is_new"] for c in queue)
    assert queue[0]["next_due"]["3"] == "2026-11-02T09:10:00Z"  # Good → 10 minutes


async def test_rating_a_card_reschedules_it_and_gives_it_a_memory_score(
    client: AsyncClient,
) -> None:
    _, cards = await make_active_cards(client)

    response = await review(client, cards[0]["id"], EASY)

    assert response.status_code == 200
    card = json_object(response, ActiveCardJson)
    assert card["due_at"] == "2026-11-10T09:00:00Z"  # Easy on a new card → 8 days
    assert card["memory_score"] == 1.0
    assert card["reps"] == 1


async def test_due_cards_come_before_new_cards(client: AsyncClient, clock: Clock) -> None:
    _, cards = await make_active_cards(client)
    _ = await review(client, cards[2]["id"], EASY)  # due in 8 days

    clock.advance(days=9)
    queue = json_list(await client.get("/v1/study/queue"), StudyCardJson)

    assert queue[0]["id"] == cards[2]["id"]
    assert queue[0]["is_new"] is False
    assert [c["is_new"] for c in queue[1:]] == [True, True]


async def test_a_card_not_yet_due_is_not_in_the_queue(client: AsyncClient) -> None:
    _, cards = await make_active_cards(client)

    _ = await review(client, cards[0]["id"], EASY)
    queue = json_list(await client.get("/v1/study/queue"), StudyCardJson)

    assert cards[0]["id"] not in [c["id"] for c in queue]


async def test_new_cards_are_limited_per_session(client: AsyncClient) -> None:
    text = " ".join(f"Fact number {i} is true." for i in range(15))
    _ = await make_active_cards(client, text=text)

    queue = json_list(await client.get("/v1/study/queue"), StudyCardJson)

    assert len(queue) == 10


async def test_queue_can_be_filtered_to_one_deck(client: AsyncClient) -> None:
    deck_a, _ = await make_active_cards(client, deck_name="A")
    _ = await make_active_cards(client, deck_name="B")

    queue = json_list(
        await client.get("/v1/study/queue", params={"deck_id": deck_a}), StudyCardJson
    )

    assert {c["deck_name"] for c in queue} == {"A"}


async def test_repeating_a_review_id_changes_nothing(client: AsyncClient) -> None:
    _, cards = await make_active_cards(client)
    review_id = str(uuid.uuid4())

    first = json_object(await review(client, cards[0]["id"], GOOD, review_id), ActiveCardJson)
    retry = json_object(await review(client, cards[0]["id"], GOOD, review_id), ActiveCardJson)

    assert retry == first
    assert retry["reps"] == 1


async def test_rating_must_be_between_1_and_4(client: AsyncClient) -> None:
    _, cards = await make_active_cards(client)

    assert (await review(client, cards[0]["id"], 5)).status_code == 422


async def test_other_users_cards_never_appear_and_cannot_be_reviewed(
    client: AsyncClient,
) -> None:
    other = {"X-Dev-User": "dev|other"}
    _, cards = await make_active_cards(client)

    queue = json_list(await client.get("/v1/study/queue", headers=other), StudyCardJson)
    response = await client.post(
        "/v1/reviews",
        json={"review_id": str(uuid.uuid4()), "card_id": cards[0]["id"], "rating": GOOD},
        headers=other,
    )

    assert queue == []
    assert response.status_code == 404


async def test_again_on_a_review_card_counts_a_lapse(client: AsyncClient, clock: Clock) -> None:
    _, cards = await make_active_cards(client)
    _ = await review(client, cards[0]["id"], EASY)
    clock.advance(days=8)

    card = json_object(await review(client, cards[0]["id"], AGAIN), ActiveCardJson)

    assert card["lapses"] == 1
