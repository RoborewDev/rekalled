from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Rekalled API",
        # Gives the generated TS client names like listDecks, not list_decks_v1_decks_get.
        generate_unique_id_function=lambda route: route.name,
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
