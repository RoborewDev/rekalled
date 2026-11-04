import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET_URL = "postgresql+asyncpg://u:S3cretPW@localhost:5432/rekalled"

_GENERATION_ENV_NAMES = {
    "card_generator",
    "max_source_chars",
    "max_cards",
    "max_sources_per_day",
}


def _clear_generation_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Settings matches env names case-insensitively; delenv only removes the exact key.
    for key in list(os.environ):
        if key.casefold() in _GENERATION_ENV_NAMES:
            monkeypatch.delenv(key, raising=False)


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")

    with pytest.raises(ValidationError):
        _ = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_database_url_is_masked_in_repr() -> None:
    settings = Settings(_env_file=None, database_url=SECRET_URL)  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in repr(settings)
    assert settings.database_url.get_secret_value() == SECRET_URL


def test_errors_do_not_echo_the_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)

    with pytest.raises(ValidationError) as exc:
        _ = Settings(_env_file=None, env="staging")  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in str(exc.value)


def test_env_files_do_not_depend_on_the_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    api_dir = Path(__file__).resolve().parents[1]

    env_file = Settings.model_config.get("env_file")
    assert isinstance(env_file, (list, tuple))
    env_files = [Path(p) for p in env_file]

    assert env_files == [
        api_dir.parent.parent / ".env",
        api_dir / ".env",
        api_dir.parent.parent / ".env.local",
    ]


def test_git_sha_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GIT_SHA", raising=False)

    settings = Settings(_env_file=None, database_url=SECRET_URL, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.git_sha == "local"


def test_git_sha_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SHA", "abc")

    settings = Settings(_env_file=None, database_url=SECRET_URL, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.git_sha == "abc"


def test_auth_mode_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_MODE")

    with pytest.raises(ValidationError):
        _ = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_unknown_env_values_are_refused() -> None:
    with pytest.raises(ValidationError):
        _ = Settings(_env_file=None, env="staging", auth_mode="dev")  # pyright: ignore[reportCallIssue]


def test_settings_errors_do_not_echo_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)

    with pytest.raises(ValidationError) as exc:
        _ = Settings(_env_file=None, env="production", auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in str(exc.value)


def test_generation_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_generation_env(monkeypatch)
    settings = Settings(_env_file=None, database_url=SECRET_URL, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.card_generator == "ai"
    assert settings.max_source_chars == 20_000
    assert settings.max_cards == 20
    assert settings.max_sources_per_day == 50


def test_generation_env_cleanup_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("card_generator", "fake")
    _clear_generation_env(monkeypatch)

    settings = Settings(_env_file=None, database_url=SECRET_URL, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.card_generator == "ai"


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("max_source_chars", 0),
        ("max_source_chars", 200_001),
        ("max_cards", 0),
        ("max_cards", 1_001),
        ("max_sources_per_day", 0),
    ],
)
def test_generation_settings_reject_unsafe_values(setting: str, value: int) -> None:
    with pytest.raises(ValidationError):
        _ = Settings.model_validate(
            {"database_url": SECRET_URL, "auth_mode": "dev", setting: value}
        )


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:pw@db.example:25060/app",
            "postgresql+asyncpg://u:pw@db.example:25060/app",
        ),
        ("postgres://u:pw@db.example:25060/app", "postgresql+asyncpg://u:pw@db.example:25060/app"),
        ("postgresql+asyncpg://u:pw@db.example/app", "postgresql+asyncpg://u:pw@db.example/app"),
        # Managed Postgres (DigitalOcean) appends libpq's sslmode, which asyncpg rejects.
        (
            "postgresql://u:pw@db.example:25060/app?sslmode=require",
            "postgresql+asyncpg://u:pw@db.example:25060/app?ssl=require",
        ),
    ],
)
def test_database_url_is_normalised_for_asyncpg(given: str, expected: str) -> None:
    settings = Settings(_env_file=None, database_url=given, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.database_url.get_secret_value() == expected


def test_database_url_keeps_special_characters_in_the_password() -> None:
    url = "postgresql+asyncpg://u:p%40ss%2Fw@db.example/app"

    settings = Settings(_env_file=None, database_url=url, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.database_url.get_secret_value() == url


def test_an_unparseable_database_url_is_refused_without_echoing_it() -> None:
    with pytest.raises(ValidationError) as exc:
        _ = Settings(_env_file=None, database_url="not a url S3cretPW", auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in str(exc.value)
