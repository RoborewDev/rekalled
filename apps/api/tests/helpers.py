TEXT = "Postgres uses MVCC. Each row version has xmin and xmax. VACUUM removes dead tuples."


async def make_deck(client, name: str = "Postgres", headers: dict | None = None) -> str:
    response = await client.post("/v1/decks", json={"name": name}, headers=headers or {})
    return response.json()["id"]


async def make_source(client, deck_id: str, text: str = TEXT) -> dict:
    response = await client.post(f"/v1/decks/{deck_id}/sources", json={"text": text})
    return response.json()


async def keep_all(client, source: dict) -> list[dict]:
    kept = [
        {"card_id": c["id"], "question": c["question"], "answer": c["answer"]}
        for c in source["cards"]
    ]
    response = await client.post(f"/v1/sources/{source['id']}/drafts/commit", json={"kept": kept})
    return response.json()


async def make_active_cards(client, text: str = TEXT, deck_name: str = "Postgres"):
    deck_id = await make_deck(client, deck_name)
    return deck_id, await keep_all(client, await make_source(client, deck_id, text))
