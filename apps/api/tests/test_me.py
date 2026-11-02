import pytest
from pydantic import ValidationError

from app.core.config import Settings


async def test_me_creates_the_dev_user_on_first_request(client):
    response = await client.get("/v1/me")

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] is None
    assert body["scopes"] == ["cards:generate", "decks:read", "decks:write"]


async def test_me_returns_the_same_user_on_later_requests(client):
    first = (await client.get("/v1/me")).json()
    second = (await client.get("/v1/me")).json()

    assert first["id"] == second["id"]


async def test_x_dev_user_header_acts_as_a_different_user(client):
    me = (await client.get("/v1/me")).json()
    other = (await client.get("/v1/me", headers={"X-Dev-User": "dev|other"})).json()

    assert me["id"] != other["id"]


def test_dev_auth_is_refused_in_production(test_database_url):
    with pytest.raises(ValidationError):
        Settings(env="production", database_url=test_database_url, auth_mode="dev")
