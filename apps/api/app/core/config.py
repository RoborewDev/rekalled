from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Repo-root .env first, then an optional apps/api/.env that overrides it.
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str  # required, read from DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    # Built without arguments on purpose: fields come from the environment/.env,
    # which static type checkers cannot see.
    return Settings.model_validate({})
