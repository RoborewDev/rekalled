from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Validate settings before serving traffic. Migrations usually read them first, but
    # MIGRATE_ON_START=false must still fail here rather than on the first request.
    _ = get_settings()
    yield


def unique_id(route: APIRoute) -> str:
    return route.name


def create_app(settings: Settings | None = None) -> FastAPI:
    # Only pin settings that were passed in explicitly. Otherwise leave get_settings as the
    # dependency so the lru_cache behaves normally and a cleared cache (a test changing an
    # environment variable, say) is picked up on the next request.
    explicit_settings = settings is not None
    settings = settings or get_settings()
    # Interactive docs and the schema are for development. In production they would map
    # the whole API for anyone; the typed client is generated at build time anyway.
    docs = settings.env != "production"
    app = FastAPI(
        title="Rekalled API",
        # Gives the generated TS client names like listDecks, not list_decks_v1_decks_get.
        generate_unique_id_function=unique_id,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    # Routes see the same config as the middleware.
    if explicit_settings:
        app.dependency_overrides[get_settings] = lambda: settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
