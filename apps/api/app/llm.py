"""Pydantic AI model wiring. The only module that knows about Pydantic AI Gateway credentials.

Model names are Pydantic AI model strings. A `gateway/` prefix routes the call through
Pydantic AI Gateway, e.g. `gateway/openai:gpt-5.4-mini`. Anything else (`openai:...`,
`anthropic:...`) goes straight to that provider using its usual environment variable.
Those variables must be exported in the process environment: pydantic-settings loads
`.env` only into Settings, so a provider key placed in `.env` is not visible to it.
"""

from collections.abc import Callable

from pydantic_ai.models import Model, infer_model
from pydantic_ai.providers import Provider, infer_provider

# Several gateway_provider overloads return Provider[Unknown] in pydantic-ai's own types.
from pydantic_ai.providers.gateway import (
    gateway_provider,  # pyright: ignore[reportUnknownVariableType]
)

from app.core.config import Settings

GATEWAY_PREFIX = "gateway/"


def _provider_factory(settings: Settings) -> Callable[[str], Provider[object]]:
    # Pass the key from Settings explicitly: pydantic-settings reads .env into Settings,
    # not into os.environ, so the gateway would not find PYDANTIC_AI_GATEWAY_API_KEY itself.
    # Direct providers have no equivalent pass-through, hence the module docstring.
    api_key = settings.pydantic_ai_gateway_api_key.get_secret_value() or None

    def factory(provider_name: str) -> Provider[object]:
        if provider_name.startswith(GATEWAY_PREFIX):
            return gateway_provider(provider_name.removeprefix(GATEWAY_PREFIX), api_key=api_key)
        return infer_provider(provider_name)

    return factory


def chat_model(settings: Settings) -> Model:
    return infer_model(settings.ai_model, provider_factory=_provider_factory(settings))
