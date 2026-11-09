from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal, Self

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
