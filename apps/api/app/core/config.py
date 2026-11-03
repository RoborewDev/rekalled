from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[2]  # apps/api
# Repo-root .env first, then an optional apps/api/.env that overrides it. Anchored to this
# file, not the working directory. Real environment variables win over both.
ENV_FILES = (API_DIR.parent.parent / ".env", API_DIR / ".env")


class Settings(BaseSettings):
    # hide_input_in_errors: a failed check must not print the raw input (DB URL, API keys).
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore", hide_input_in_errors=True)

    env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr  # required, read from DATABASE_URL; masked in repr and logs

    # "dev" = no tokens, a fixed local user. "logto" = validate Logto access tokens.
    # Required, so a deploy that forgets it fails to start instead of running unauthenticated.
    auth_mode: Literal["dev", "logto"]

    # Which commit this process was built from. The Dockerfile bakes it in as GIT_SHA, and
    # /v1/health reports it so a deploy can prove the new image is the one serving traffic.
    git_sha: str = "local"

    @model_validator(mode="after")
    def dev_auth_only_in_development(self) -> Self:
        # An allowlist, not "not production": an unexpected ENV must not switch auth off.
        if self.auth_mode == "dev" and self.env not in ("development", "test"):
            raise ValueError("AUTH_MODE=dev is only allowed when ENV is development or test")
        return self


@lru_cache
def get_settings() -> Settings:
    # Built without arguments on purpose: fields come from the environment/.env,
    # which static type checkers cannot see.
    return Settings.model_validate({})
