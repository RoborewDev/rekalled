from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET_URL = "postgresql+asyncpg://u:S3cretPW@localhost:5432/rekalled"


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_database_url_is_masked_in_repr():
    settings = Settings(_env_file=None, database_url=SECRET_URL)  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in repr(settings)
    assert settings.database_url.get_secret_value() == SECRET_URL


def test_errors_do_not_echo_the_input(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, env="staging")  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in str(exc.value)


def test_env_files_do_not_depend_on_the_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    api_dir = Path(__file__).resolve().parents[1]

    env_files = [Path(p) for p in Settings.model_config["env_file"]]  # type: ignore[union-attr]

    assert env_files == [
        api_dir.parent.parent / ".env",
        api_dir / ".env",
        api_dir.parent.parent / ".env.local",
    ]


def test_git_sha_defaults_to_local(monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)

    settings = Settings(_env_file=None, database_url=SECRET_URL, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.git_sha == "local"


def test_git_sha_reads_the_environment(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc")

    settings = Settings(_env_file=None, database_url=SECRET_URL, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.git_sha == "abc"


def test_auth_mode_is_required(monkeypatch):
    monkeypatch.delenv("AUTH_MODE")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_unknown_env_values_are_refused():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, env="staging", auth_mode="dev")  # pyright: ignore[reportCallIssue]


def test_settings_errors_do_not_echo_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, env="production", auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in str(exc.value)


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
def test_database_url_is_normalised_for_asyncpg(given, expected):
    settings = Settings(_env_file=None, database_url=given, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.database_url.get_secret_value() == expected


def test_database_url_keeps_special_characters_in_the_password():
    url = "postgresql+asyncpg://u:p%40ss%2Fw@db.example/app"

    settings = Settings(_env_file=None, database_url=url, auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert settings.database_url.get_secret_value() == url


def test_an_unparseable_database_url_is_refused_without_echoing_it():
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, database_url="not a url S3cretPW", auth_mode="dev")  # pyright: ignore[reportCallIssue]

    assert "S3cretPW" not in str(exc.value)
