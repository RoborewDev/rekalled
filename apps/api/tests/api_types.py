"""Typed views of the JSON the API returns, so tests do not work with `Any`."""

from typing import TypedDict, cast

from httpx import Response


class DeckJson(TypedDict):
    id: str
    name: str
    created_at: str


class CardJson(TypedDict):
    id: str
    deck_id: str
    source_id: str | None
    status: str
    question: str
    answer: str
    source_excerpt: str | None


class SourceJson(TypedDict):
    id: str
    deck_id: str
    kind: str
    title: str | None
    content: str
    created_at: str
    cards: list[CardJson]


class ActiveCardJson(TypedDict):
    id: str
    deck_id: str
    source_id: str | None
    question: str
    answer: str
    source_excerpt: str | None
    due_at: str
    reps: int
    lapses: int
    memory_score: float | None


class KeptDraftJson(TypedDict):
    card_id: str
    question: str
    answer: str


class MeJson(TypedDict):
    id: str
    email: str | None
    display_name: str | None
    scopes: list[str]


class HealthJson(TypedDict):
    status: str
    git_sha: str


class GenerationFailedJson(TypedDict):
    detail: str
    source_id: str


def json_object[JsonT](response: Response, _model: type[JsonT]) -> JsonT:
    return cast(JsonT, response.json())


def json_list[JsonT](response: Response, _model: type[JsonT]) -> list[JsonT]:
    return cast(list[JsonT], response.json())
