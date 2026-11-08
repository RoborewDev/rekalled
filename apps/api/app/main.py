from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Validate settings before serving traffic. Migrations usually read them first, but
    # MIGRATE_ON_START=false must still fail here rather than on the first request.
    _ = get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rekalled API",
        lifespan=lifespan,
        # Gives the generated TS client names like listDecks, not list_decks_v1_decks_get.
        generate_unique_id_function=lambda route: route.name,
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
