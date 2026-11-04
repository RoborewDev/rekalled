from httpx import AsyncClient

from tests.api_types import DeckJson, json_list, json_object

OTHER_USER = {"X-Dev-User": "dev|other"}


async def test_create_deck_then_it_appears_in_my_list(client: AsyncClient) -> None:
    created = await client.post("/v1/decks", json={"name": "Postgres internals"})

    assert created.status_code == 201
    decks = json_list(await client.get("/v1/decks"), DeckJson)
    assert [d["name"] for d in decks] == ["Postgres internals"]


async def test_deck_name_cannot_be_empty(client: AsyncClient) -> None:
    response = await client.post("/v1/decks", json={"name": ""})

    assert response.status_code == 422


async def test_rename_deck(client: AsyncClient) -> None:
    deck = json_object(await client.post("/v1/decks", json={"name": "Old"}), DeckJson)

    response = await client.patch(f"/v1/decks/{deck['id']}", json={"name": "New"})

    assert json_object(response, DeckJson)["name"] == "New"


async def test_delete_deck(client: AsyncClient) -> None:
    deck = json_object(await client.post("/v1/decks", json={"name": "Temp"}), DeckJson)

    assert (await client.delete(f"/v1/decks/{deck['id']}")).status_code == 204
    assert (await client.get(f"/v1/decks/{deck['id']}")).status_code == 404


async def test_other_users_cannot_see_or_change_my_deck(client: AsyncClient) -> None:
    deck = json_object(await client.post("/v1/decks", json={"name": "Mine"}), DeckJson)
    url = f"/v1/decks/{deck['id']}"

    assert json_list(await client.get("/v1/decks", headers=OTHER_USER), DeckJson) == []
    assert (await client.get(url, headers=OTHER_USER)).status_code == 404
    assert (await client.patch(url, json={"name": "x"}, headers=OTHER_USER)).status_code == 404
    assert (await client.delete(url, headers=OTHER_USER)).status_code == 404
