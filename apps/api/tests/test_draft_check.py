from datetime import datetime

from httpx import AsyncClient

from tests.api_types import ActiveCardJson, KeptDraftJson, SourceJson, json_list, json_object
from tests.conftest import Clock
from tests.helpers import make_deck, make_source


async def test_commit_keeps_edits_and_deletes_unticked_drafts(
    client: AsyncClient, clock: Clock
) -> None:
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    first, second, _third = source["cards"]

    response = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit",
        json={
            "kept": [
                {"card_id": first["id"], "question": "Edited?", "answer": "Edited."},
                {"card_id": second["id"], "question": second["question"], "answer": "A2"},
            ]
        },
    )

    assert response.status_code == 200
    active = json_list(response, ActiveCardJson)
    assert [c["question"] for c in active] == ["Edited?", second["question"]]
    # New Active cards are due straight away and have no Memory score yet.
    assert all(datetime.fromisoformat(c["due_at"]) == clock.now for c in active)
    assert all(c["memory_score"] is None for c in active)
    deck_cards = json_list(await client.get(f"/v1/decks/{deck_id}/cards"), ActiveCardJson)
    assert len(deck_cards) == 2


async def test_committing_twice_is_harmless(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    body: dict[str, list[KeptDraftJson]] = {
        "kept": [
            {"card_id": c["id"], "question": c["question"], "answer": c["answer"]}
            for c in source["cards"]
        ]
    }

    first = await client.post(f"/v1/sources/{source['id']}/drafts/commit", json=body)
    second = await client.post(f"/v1/sources/{source['id']}/drafts/commit", json=body)

    assert len(json_list(first, ActiveCardJson)) == len(json_list(second, ActiveCardJson)) == 3


async def test_edit_and_delete_an_active_card(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card = source["cards"][0]
    _ = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit",
        json={"kept": [{"card_id": card["id"], "question": "Q", "answer": "A"}]},
    )

    edited = json_object(
        await client.patch(f"/v1/cards/{card['id']}", json={"answer": "Better answer"}),
        ActiveCardJson,
    )
    assert edited["answer"] == "Better answer"

    assert (await client.delete(f"/v1/cards/{card['id']}")).status_code == 204
    assert json_list(await client.get(f"/v1/decks/{deck_id}/cards"), ActiveCardJson) == []


async def test_overlong_card_text_is_rejected(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card = source["cards"][0]
    too_long: KeptDraftJson = {"card_id": card["id"], "question": "Q", "answer": "x" * 2_001}

    commit = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit", json={"kept": [too_long]}
    )
    edit = await client.patch(f"/v1/cards/{card['id']}", json={"question": "x" * 2_001})

    assert commit.status_code == 422
    assert edit.status_code == 422


async def test_other_users_cannot_commit_or_edit_my_cards(client: AsyncClient) -> None:
    other = {"X-Dev-User": "dev|other"}
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card_id = source["cards"][0]["id"]

    commit = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit", json={"kept": []}, headers=other
    )
    edit = await client.patch(f"/v1/cards/{card_id}", json={"answer": "x"}, headers=other)

    assert commit.status_code == 404
    assert edit.status_code == 404


async def test_own_draft_cards_cannot_be_edited_or_deleted(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card = source["cards"][0]

    edit = await client.patch(f"/v1/cards/{card['id']}", json={"answer": "Too early"})
    delete = await client.delete(f"/v1/cards/{card['id']}")

    # A draft has no memory state, so it is not editable: 404, never a 500.
    assert edit.status_code == 404
    assert delete.status_code == 404
    still_drafts = json_object(await client.get(f"/v1/sources/{source['id']}"), SourceJson)
    assert [c["status"] for c in still_drafts["cards"]] == ["draft", "draft", "draft"]

    # Nothing was changed, so the draft check still commits the draft as it stands.
    committed = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit",
        json={
            "kept": [
                {"card_id": card["id"], "question": card["question"], "answer": card["answer"]}
            ]
        },
    )
    assert [c["question"] for c in json_list(committed, ActiveCardJson)] == [card["question"]]


async def test_an_empty_patch_is_rejected(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card = source["cards"][0]
    _ = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit",
        json={"kept": [{"card_id": card["id"], "question": "Q", "answer": "A"}]},
    )

    response = await client.patch(f"/v1/cards/{card['id']}", json={})

    assert response.status_code == 422


async def test_commit_rejects_card_ids_from_another_source(client: AsyncClient) -> None:
    deck_id = await make_deck(client)
    mine = await make_source(client, deck_id)
    other = await make_source(client, deck_id)

    response = await client.post(
        f"/v1/sources/{mine['id']}/drafts/commit",
        json={"kept": [{"card_id": other["cards"][0]["id"], "question": "Q", "answer": "A"}]},
    )

    assert response.status_code == 400
    # Nothing was activated or deleted: both sources keep all their drafts.
    mine_after = json_object(await client.get(f"/v1/sources/{mine['id']}"), SourceJson)
    other_after = json_object(await client.get(f"/v1/sources/{other['id']}"), SourceJson)
    assert [c["status"] for c in mine_after["cards"]] == ["draft", "draft", "draft"]
    assert [c["status"] for c in other_after["cards"]] == ["draft", "draft", "draft"]
