import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings


def test_migrations_accept_url_encoded_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # "p@ss" URL-encoded. Offline (sql=True) mode renders SQL without touching a database.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p%40ss@localhost:5432/x_test")
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head", sql=True)
    finally:
        get_settings.cache_clear()

    assert "CREATE EXTENSION" in capsys.readouterr().out
