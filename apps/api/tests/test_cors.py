import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


async def test_web_origin_may_call_the_api(client: AsyncClient) -> None:
    response = await client.options(
        "/v1/decks",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_other_origins_are_refused(client: AsyncClient) -> None:
    response = await client.options(
        "/v1/decks",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in response.headers


def production_settings(**changes: object) -> Settings:
    return Settings.model_validate(
        {
            "_env_file": None,
            "env": "production",
            "auth_mode": "logto",
            "logto_endpoint": "https://tenant.logto.app",
            "logto_api_resource": "https://api.rekalled.app",
            "logto_app_id": "spa-app-id",
            # The default is a localhost origin, which production refuses on purpose.
            "cors_origins": ["https://rekalled.app"],
            **changes,
        }
    )


async def test_cors_origins_come_from_the_settings_passed_in():
    app = create_app(production_settings(cors_origins=["https://rekalled.app"]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/v1/decks",
            headers={"Origin": "https://rekalled.app", "Access-Control-Request-Method": "GET"},
        )

    assert response.headers["access-control-allow-origin"] == "https://rekalled.app"


async def test_docs_and_schema_are_off_in_production():
    app = create_app(production_settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert (await client.get(path)).status_code == 404


def test_wildcard_cors_is_refused_in_production():
    with pytest.raises(ValidationError, match="CORS_ORIGINS must list real origins"):
        _ = production_settings(cors_origins=["*"])
