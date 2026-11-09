from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

API_DIR = Path(__file__).resolve().parents[2]  # apps/api
# Repo-root .env first, then an optional apps/api/.env, then the root .env.local written by
# scripts/env-pull.sh — later files override earlier ones. Anchored to this file, not the
# working directory. Real environment variables win over all of them.
ENV_FILES = (API_DIR.parent.parent / ".env", API_DIR / ".env", API_DIR.parent.parent / ".env.local")


class Settings(BaseSettings):
    # hide_input_in_errors: a failed check must not print the raw input (DB URL, API keys).
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=ENV_FILES, extra="ignore", hide_input_in_errors=True
    )

    env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr  # required, read from DATABASE_URL; masked in repr and logs

    # "dev" = no tokens, a fixed local user. "logto" = validate Logto access tokens.
    # Required, so a deploy that forgets it fails to start instead of running unauthenticated.
    auth_mode: Literal["dev", "logto"]
    logto_endpoint: str = ""  # e.g. https://abc123.logto.app
    logto_api_resource: str = ""  # the API identifier in Logto, e.g. https://api.rekalled.app
    logto_app_id: str = ""
    # Card generation. "fake" needs no API key: handy for frontend work and E2E.
    card_generator: Literal["ai", "fake"] = "ai"
    # A Pydantic AI model string. "gateway/" routes through Pydantic AI Gateway.
    ai_model: str = "gateway/openai:gpt-5.4-mini"
    pydantic_ai_gateway_api_key: SecretStr = SecretStr("")
    # SourceCreate rejects text above 200k, so a larger limit here would have no effect.
    max_source_chars: int = Field(default=20_000, gt=0, le=200_000)
    max_cards: int = Field(default=20, gt=0, le=1_000)
    # Every Source spends model credit, so cap how many one user can add per 24 hours.
    max_sources_per_day: int = Field(default=50, gt=0)
    # Browser origins allowed to call the API. Bearer tokens, no cookies, so no credentials.
    cors_origins: list[str] = ["http://localhost:3000"]
    # Spaced repetition. Fuzzing spreads due dates a little; tests turn it off.
    fsrs_fuzzing: bool = True
    new_cards_per_session: int = 10
    # Safety cap, not a daily limit: a large backlog would otherwise mean thousands of
    # FSRS previews and a huge response per queue request. The most overdue cards come first.
    due_cards_per_session: int = Field(default=200, gt=0)
    # Which commit this process was built from. The Dockerfile bakes it in as GIT_SHA, and
    # /v1/health reports it so a deploy can prove the new image is the one serving traffic.
    git_sha: str = "local"

    @field_validator("database_url", mode="after")
    @classmethod
    def use_asyncpg_driver(cls, value: SecretStr) -> SecretStr:
        # Managed Postgres hands out libpq-style URLs (postgresql://...?sslmode=require).
        # The app talks to Postgres through asyncpg, which needs the +asyncpg driver and
        # rejects sslmode as an unknown connect() argument; its equivalent is ssl.
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("DATABASE_URL is not a valid database URL") from None
        if url.drivername in ("postgres", "postgresql"):
            url = url.set(drivername="postgresql+asyncpg")
        if url.drivername == "postgresql+asyncpg" and "sslmode" in url.query:
            sslmode = url.query["sslmode"]
            if isinstance(sslmode, tuple):  # ?sslmode=a&sslmode=b: libpq uses the last one
                sslmode = sslmode[-1]
            url = url.difference_update_query(["sslmode"]).update_query_dict({"ssl": sslmode})
        return SecretStr(url.render_as_string(hide_password=False))

    @field_validator("logto_endpoint")
    @classmethod
    def logto_endpoint_is_a_base_url(cls, value: str) -> str:
        # A typo here would otherwise mean an opaque 401 on every request instead of a
        # clear failure at start-up. Empty stays valid: dev mode leaves Logto unused.
        if not value:
            return value
        url = urlsplit(value)
        # http is allowed only for a local tenant; anything else must be encrypted.
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (
            url.scheme not in ("http", "https")
            or (url.scheme == "http" and not local)
            or not url.hostname
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError("LOGTO_ENDPOINT must be a base URL such as https://abc123.logto.app")
        return value

    @model_validator(mode="after")
    def dev_auth_only_in_development(self) -> Self:
        # An allowlist, not "not production": an unexpected ENV must not switch auth off.
        if self.auth_mode == "dev" and self.env not in ("development", "test"):
            raise ValueError("AUTH_MODE=dev is only allowed when ENV is development or test")
        # Without the app id the client_id check would be silently skipped.
        if self.auth_mode == "logto" and not (
            self.logto_endpoint and self.logto_api_resource and self.logto_app_id
        ):
            raise ValueError(
                "AUTH_MODE=logto needs LOGTO_ENDPOINT, LOGTO_API_RESOURCE and LOGTO_APP_ID"
            )
        return self

    @field_validator("cors_origins")
    @classmethod
    def cors_origins_are_origins(cls, value: list[str]) -> list[str]:
        # Fail fast on anything a browser Origin header can never match: a missing scheme or
        # host, a path/query/fragment, user info, or an invalid port. "*" is allowed here and
        # refused in production below, so dev can still be permissive.
        for origin in value:
            if origin == "*":
                continue
            url = urlsplit(origin)
            try:
                _ = url.port
            except ValueError:
                raise ValueError("CORS_ORIGINS entries must use a valid port") from None
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.path
                or url.query
                or url.fragment
                or url.username is not None
                or url.password is not None
            ):
                raise ValueError(
                    "CORS_ORIGINS entries must be origins such as https://app.rekalled.app"
                )
        return value

    @model_validator(mode="after")
    def real_cors_origins_in_production(self) -> Self:
        # A missing, wildcard or localhost origin would either expose the API to any site or
        # block the real frontend; both only show up later as an opaque browser CORS error.
        if self.env != "production":
            return self
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must list real origins in production, not * or empty")
        local = ("localhost", "127.0.0.1", "::1")
        if any(urlsplit(origin).hostname in local for origin in self.cors_origins):
            raise ValueError("CORS_ORIGINS must not contain localhost origins in production")
        return self

    @property
    def logto_issuer(self) -> str:
        return f"{self.logto_endpoint.rstrip('/')}/oidc"

    @property
    def logto_jwks_url(self) -> str:
        return f"{self.logto_issuer}/jwks"

    @model_validator(mode="after")
    def ai_generation_needs_a_model(self) -> Self:
        if self.card_generator == "ai" and not self.ai_model.strip():
            raise ValueError("AI_MODEL is required for AI generation")
        return self

    @model_validator(mode="after")
    def gateway_model_needs_a_key(self) -> Self:
        # Fail at start-up, not on the first generation request. The check stays narrow:
        # direct models such as openai:... read their own environment variables instead.
        if (
            self.card_generator == "ai"
            and self.ai_model.startswith("gateway/")
            and not self.pydantic_ai_gateway_api_key.get_secret_value()
        ):
            raise ValueError("PYDANTIC_AI_GATEWAY_API_KEY is required for gateway/ models")
        return self


@lru_cache
def get_settings() -> Settings:
    # Built without arguments on purpose: fields come from the environment/.env,
    # which static type checkers cannot see.
    return Settings.model_validate({})
