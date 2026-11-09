import pytest
from fastapi.testclient import TestClient

import app.main
from app.main import create_app


def test_startup_validates_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    # Build the app while settings are still valid: create_app() reads them itself, so the
    # failure below can only come from the lifespan hook at start-up.
    test_app = create_app()

    def invalid_settings() -> None:
        raise RuntimeError("settings are invalid")

    # The lifespan must read Settings even when start.sh skipped migrations.
    monkeypatch.setattr(app.main, "get_settings", invalid_settings)

    with pytest.raises(RuntimeError, match="settings are invalid"):
        with TestClient(test_app):
            pass
