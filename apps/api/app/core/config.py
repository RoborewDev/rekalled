from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Repo-root .env first, then an optional apps/api/.env that overrides it.
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str  # required, read from DATABASE_URL
    auth_mode: Literal["dev", "logto"] = "dev"

    @model_validator(mode="after")
    def dev_auth_never_in_production(self) -> Self:
        if self.env == "production" and self.auth_mode == "dev":
            raise ValueError("AUTH_MODE=dev is not allowed when ENV=production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
