from app.core.config import get_settings


async def test_health_reports_ok_when_database_is_reachable(client):
    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_health_reports_the_commit_the_image_was_built_from(client, monkeypatch):
    # The Dockerfile sets GIT_SHA; Settings reads it like any other variable.
    monkeypatch.setenv("GIT_SHA", "abc123def456")
    get_settings.cache_clear()
    try:
        response = await client.get("/v1/health")
    finally:
        get_settings.cache_clear()

    assert response.json() == {"status": "ok", "git_sha": "abc123def456"}
