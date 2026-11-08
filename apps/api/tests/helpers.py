from httpx import AsyncClient

from tests.api_types import (
    ActiveCardJson,
    DeckJson,
    KeptDraftJson,
    SourceJson,
    json_list,
    json_object,
)

TEXT = "Postgres uses MVCC. Each row version has xmin and xmax. VACUUM removes dead tuples."


async def make_deck(
    client: AsyncClient, name: str = "Postgres", headers: dict[str, str] | None = None
) -> str:
    response = await client.post("/v1/decks", json={"name": name}, headers=headers or {})
    return json_object(response, DeckJson)["id"]


async def make_source(client: AsyncClient, deck_id: str, text: str = TEXT) -> SourceJson:
    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": text})
    return json_object(response, SourceJson)


async def keep_all(client: AsyncClient, source: SourceJson) -> list[ActiveCardJson]:
    kept: list[KeptDraftJson] = [
        {"card_id": c["id"], "question": c["question"], "answer": c["answer"]}
        for c in source["cards"]
    ]
    response = await client.post(f"/v1/sources/{source['id']}/drafts/commit", json={"kept": kept})
    return json_list(response, ActiveCardJson)


async def make_active_cards(
    client: AsyncClient, text: str = TEXT, deck_name: str = "Postgres"
) -> tuple[str, list[ActiveCardJson]]:
    deck_id = await make_deck(client, deck_name)
    return deck_id, await keep_all(client, await make_source(client, deck_id, text))
