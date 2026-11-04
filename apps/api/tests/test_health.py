import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.api_types import HealthJson, json_object


async def test_health_reports_ok_when_database_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert json_object(response, HealthJson)["status"] == "ok"


async def test_health_reports_the_commit_the_image_was_built_from(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The Dockerfile sets GIT_SHA; Settings reads it like any other variable.
    monkeypatch.setenv("GIT_SHA", "abc123def456")
    get_settings.cache_clear()
    try:
        response = await client.get("/v1/health")
    finally:
        get_settings.cache_clear()

    assert json_object(response, HealthJson) == {"status": "ok", "git_sha": "abc123def456"}
