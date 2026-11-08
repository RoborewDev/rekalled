import pytest
from fastapi.testclient import TestClient

import app.main
from app.main import create_app


def test_startup_validates_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid_settings() -> None:
        raise RuntimeError("settings are invalid")

    # The lifespan must read Settings even when start.sh skipped migrations.
    monkeypatch.setattr(app.main, "get_settings", invalid_settings)

    with pytest.raises(RuntimeError, match="settings are invalid"):
        with TestClient(create_app()):
            pass
