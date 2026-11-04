from app.api.deps import get_card_generator
from app.generation.base import CardDraft, GenerationError
from app.generation.fake import FailingCardGenerator, FakeCardGenerator

TEXT = "Postgres uses MVCC. Each row version has xmin and xmax. VACUUM removes dead tuples."


async def make_deck(client) -> str:
    return (await client.post("/v1/decks", json={"name": "Postgres"})).json()["id"]


async def test_pasting_text_creates_a_source_with_draft_cards(client):
    deck_id = await make_deck(client)

    response = await client.post(
        f"/v1/decks/{deck_id}/sources", json={"title": "MVCC notes", "text": TEXT}
    )

    assert response.status_code == 201
    source = response.json()
    assert source["title"] == "MVCC notes"
    assert [c["status"] for c in source["cards"]] == ["draft", "draft", "draft"]
    assert source["cards"][0]["source_excerpt"] == "Postgres uses MVCC."


async def test_drafts_survive_a_reload(client):
    deck_id = await make_deck(client)
    created = (await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})).json()

    fetched = (await client.get(f"/v1/sources/{created['id']}")).json()

    assert len(fetched["cards"]) == 3


async def test_text_over_the_limit_is_rejected(client, override_settings):
    override_settings(max_source_chars=10)
    deck_id = await make_deck(client)

    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": "x" * 11})

    assert response.status_code == 413


async def test_huge_text_is_refused_before_any_work(client):
    deck_id = await make_deck(client)

    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": "x" * 200_001})

    assert response.status_code == 422


async def test_sources_per_day_are_capped(client, override_settings):
    override_settings(max_sources_per_day=2)
    deck_id = await make_deck(client)

    for _ in range(2):
        ok = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})
        assert ok.status_code == 201
    third = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})

    assert third.status_code == 429


async def test_failed_generation_keeps_the_source_and_can_be_retried(client, app):
    deck_id = await make_deck(client)
    app.dependency_overrides[get_card_generator] = FailingCardGenerator

    failed = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})

    assert failed.status_code == 502
    source_id = failed.json()["source_id"]
    assert (await client.get(f"/v1/sources/{source_id}")).json()["cards"] == []

    app.dependency_overrides[get_card_generator] = FakeCardGenerator
    retried = await client.post(f"/v1/sources/{source_id}/generate")

    assert len(retried.json()["cards"]) == 3


class LeakyFailingGenerator:
    async def generate(self, text: str, *, max_cards: int) -> list[CardDraft]:
        raise GenerationError("status 401 body={'key': 'secret-from-provider'}")


async def test_generation_errors_do_not_leak_provider_details(client, app):
    deck_id = await make_deck(client)
    app.dependency_overrides[get_card_generator] = LeakyFailingGenerator

    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})

    assert response.status_code == 502
    assert "secret-from-provider" not in response.text


async def test_cannot_add_a_source_to_someone_elses_deck(client):
    deck_id = await make_deck(client)

    response = await client.post(
        f"/v1/decks/{deck_id}/sources", json={"text": TEXT}, headers={"X-Dev-User": "dev|other"}
    )

    assert response.status_code == 404
