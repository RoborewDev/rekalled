from fastapi import APIRouter

from app.api.v1 import cards, decks, health, me, sources

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router)
api_router.include_router(me.router)
api_router.include_router(decks.router)
api_router.include_router(sources.router)
api_router.include_router(cards.router)
