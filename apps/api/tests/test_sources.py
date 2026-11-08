from collections.abc import Callable

from fastapi import FastAPI
from httpx import AsyncClient

from app.api.deps import get_card_generator
from app.core.config import Settings
from app.generation.base import CardDraft, GenerationError
from app.generation.fake import FailingCardGenerator, FakeCardGenerator
from tests.api_types import GenerationFailedJson, SourceJson, json_object
from tests.helpers import TEXT, make_deck


async def test_pasting_text_creates_a_source_with_draft_cards(client: AsyncClient) -> None:
    deck_id = await make_deck(client)

    response = await client.post(
        f"/v1/decks/{deck_id}/sources", json={"title": "MVCC notes", "text": TEXT}
    )

    assert response.status_code == 201
    source = json_object(response, SourceJson)
    assert source["title"] == "MVCC notes"
    assert [c["status"] for c in source["cards"]] == ["draft", "draft", "draft"]
    assert source["cards"][0]["source_excerpt"] == "Postgres uses MVCC."


async def test_drafts_survive_a_reload(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    created = json_object(
        await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT}), SourceJson
    )

    fetched = json_object(await client.get(f"/v1/sources/{created['id']}"), SourceJson)

    assert len(fetched["cards"]) == 3


async def test_text_over_the_limit_is_rejected(
    client: AsyncClient, override_settings: Callable[..., Settings]
) -> None:
    _ = override_settings(max_source_chars=10)
    deck_id = await make_deck(client)

    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": "x" * 11})

    assert response.status_code == 413


async def test_huge_text_is_refused_before_any_work(client: AsyncClient) -> None:
    deck_id = await make_deck(client)

    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": "x" * 200_001})

    assert response.status_code == 422


async def test_sources_per_day_are_capped(
    client: AsyncClient, override_settings: Callable[..., Settings]
) -> None:
    _ = override_settings(max_sources_per_day=2)
    deck_id = await make_deck(client)

    for _ in range(2):
        ok = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})
        assert ok.status_code == 201
    third = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})

    assert third.status_code == 429


async def test_failed_generation_keeps_the_source_and_can_be_retried(
    client: AsyncClient, app: FastAPI
) -> None:
    deck_id = await make_deck(client)
    app.dependency_overrides[get_card_generator] = FailingCardGenerator

    failed = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})

    assert failed.status_code == 502
    source_id = json_object(failed, GenerationFailedJson)["source_id"]
    assert json_object(await client.get(f"/v1/sources/{source_id}"), SourceJson)["cards"] == []

    app.dependency_overrides[get_card_generator] = FakeCardGenerator
    retried = await client.post(f"/v1/sources/{source_id}/generate")

    assert len(json_object(retried, SourceJson)["cards"]) == 3


class LeakyFailingGenerator:
    async def generate(self, text: str, *, max_cards: int) -> list[CardDraft]:
        # Interface parameters; this generator always fails before using them.
        del text, max_cards
        raise GenerationError("status 401 body={'key': 'secret-from-provider'}")


async def test_generation_errors_do_not_leak_provider_details(
    client: AsyncClient, app: FastAPI
) -> None:
    deck_id = await make_deck(client)
    app.dependency_overrides[get_card_generator] = LeakyFailingGenerator

    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": TEXT})

    assert response.status_code == 502
    assert "secret-from-provider" not in response.text


async def test_cannot_add_a_source_to_someone_elses_deck(client: AsyncClient) -> None:
    deck_id = await make_deck(client)

    response = await client.post(
        f"/v1/decks/{deck_id}/sources", json={"text": TEXT}, headers={"X-Dev-User": "dev|other"}
    )

    assert response.status_code == 404
