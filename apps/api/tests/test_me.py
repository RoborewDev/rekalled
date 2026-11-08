import pytest
from httpx import AsyncClient
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from tests.api_types import MeJson, json_object


async def test_me_creates_the_dev_user_on_first_request(client: AsyncClient) -> None:
    response = await client.get("/v1/me")

    assert response.status_code == 200
    body = json_object(response, MeJson)
    assert body["display_name"] is None
    assert body["scopes"] == ["cards:generate", "decks:read", "decks:write"]


async def test_me_returns_the_same_user_on_later_requests(client: AsyncClient) -> None:
    first = json_object(await client.get("/v1/me"), MeJson)
    second = json_object(await client.get("/v1/me"), MeJson)

    assert first["id"] == second["id"]


async def test_x_dev_user_header_acts_as_a_different_user(client: AsyncClient) -> None:
    me = json_object(await client.get("/v1/me"), MeJson)
    other = json_object(await client.get("/v1/me", headers={"X-Dev-User": "dev|other"}), MeJson)

    assert me["id"] != other["id"]


def test_dev_auth_is_refused_in_production(test_database_url: str) -> None:
    with pytest.raises(ValidationError):
        # card_generator=fake keeps the gateway-key validator out of this failure.
        _ = Settings(
            env="production",
            database_url=SecretStr(test_database_url),
            auth_mode="dev",
            card_generator="fake",
        )
