from tests.helpers import make_deck, make_source


async def test_commit_keeps_edits_and_deletes_unticked_drafts(client, clock):
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
    active = response.json()
    assert [c["question"] for c in active] == ["Edited?", second["question"]]
    # New Active cards are due straight away and have no Memory score yet.
    assert all(c["due_at"] == "2026-11-02T09:00:00Z" for c in active)
    assert all(c["memory_score"] is None for c in active)
    deck_cards = (await client.get(f"/v1/decks/{deck_id}/cards")).json()
    assert len(deck_cards) == 2


async def test_committing_twice_is_harmless(client):
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    body = {
        "kept": [
            {"card_id": c["id"], "question": c["question"], "answer": c["answer"]}
            for c in source["cards"]
        ]
    }

    first = await client.post(f"/v1/sources/{source['id']}/drafts/commit", json=body)
    second = await client.post(f"/v1/sources/{source['id']}/drafts/commit", json=body)

    assert len(first.json()) == len(second.json()) == 3


async def test_edit_and_delete_an_active_card(client):
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card = source["cards"][0]
    await client.post(
        f"/v1/sources/{source['id']}/drafts/commit",
        json={"kept": [{"card_id": card["id"], "question": "Q", "answer": "A"}]},
    )

    edited = await client.patch(f"/v1/cards/{card['id']}", json={"answer": "Better answer"})
    assert edited.json()["answer"] == "Better answer"

    assert (await client.delete(f"/v1/cards/{card['id']}")).status_code == 204
    assert (await client.get(f"/v1/decks/{deck_id}/cards")).json() == []


async def test_overlong_card_text_is_rejected(client):
    deck_id = await make_deck(client)
    source = await make_source(client, deck_id)
    card = source["cards"][0]
    too_long = {"card_id": card["id"], "question": "Q", "answer": "x" * 2_001}

    commit = await client.post(
        f"/v1/sources/{source['id']}/drafts/commit", json={"kept": [too_long]}
    )
    edit = await client.patch(f"/v1/cards/{card['id']}", json={"question": "x" * 2_001})

    assert commit.status_code == 422
    assert edit.status_code == 422


async def test_other_users_cannot_commit_or_edit_my_cards(client):
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
