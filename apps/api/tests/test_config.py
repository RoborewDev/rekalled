import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET_URL = "postgresql+asyncpg://u:S3cretPW@localhost:5432/rekalled"

_GENERATION_ENV_NAMES = {
    "card_generator",
    "ai_model",
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
        _ = Settings.model_validate({"_env_file": None})


def test_database_url_is_masked_in_repr() -> None:
    settings = Settings.model_validate({"_env_file": None, "database_url": SECRET_URL})

    assert "S3cretPW" not in repr(settings)
    assert settings.database_url.get_secret_value() == SECRET_URL


def test_errors_do_not_echo_the_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)

    with pytest.raises(ValidationError) as exc:
        _ = Settings.model_validate({"_env_file": None, "env": "staging"})

    assert "S3cretPW" not in str(exc.value)


def test_settings_errors_do_not_echo_the_gateway_key() -> None:
    # An invalid type puts the canary on the gateway-key error path itself. The message
    # must hide the input (hide_input_in_errors), not merely avoid an unrelated validator.
    with pytest.raises(ValidationError) as exc:
        _ = Settings.model_validate(
            {
                "_env_file": None,
                "database_url": SECRET_URL,
                "auth_mode": "dev",
                "pydantic_ai_gateway_api_key": {"key": "pylf_canary_key"},
            }
        )

    assert "pylf_canary_key" not in str(exc.value)


@pytest.mark.parametrize("missing", ["logto_endpoint", "logto_api_resource", "logto_app_id"])
def test_logto_mode_needs_every_setting(missing: str) -> None:
    logto: dict[str, str] = {
        "logto_endpoint": "https://tenant.logto.app",
        "logto_api_resource": "https://api.rekalled.app",
        "logto_app_id": "spa-app-id",
    }
    del logto[missing]

    with pytest.raises(ValidationError, match="AUTH_MODE=logto needs"):
        _ = Settings.model_validate({"_env_file": None, "auth_mode": "logto", **logto})


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://tenant.logto.app",  # unencrypted, and not a local tenant
        "https://",  # no host
        "https://tenant.logto.app/oidc",  # a path would corrupt the derived issuer
        "https://tenant.logto.app?x=1",  # likewise a query string
        "tenant.logto.app",  # no scheme
    ],
)
def test_logto_endpoint_must_be_a_base_url(endpoint: str) -> None:
    with pytest.raises(ValidationError, match="LOGTO_ENDPOINT must be a base URL"):
        _ = Settings.model_validate(
            {
                "_env_file": None,
                "auth_mode": "logto",
                "card_generator": "fake",
                "logto_endpoint": endpoint,
                "logto_api_resource": "https://api.rekalled.app",
                "logto_app_id": "spa-app-id",
            }
        )


@pytest.mark.parametrize(
    "endpoint", ["https://tenant.logto.app", "https://tenant.logto.app/", "http://localhost:3001"]
)
def test_logto_endpoint_accepts_base_urls(endpoint: str) -> None:
    settings = Settings.model_validate(
        {
            "_env_file": None,
            "auth_mode": "logto",
            "card_generator": "fake",
            "logto_endpoint": endpoint,
            "logto_api_resource": "https://api.rekalled.app",
            "logto_app_id": "spa-app-id",
        }
    )

    assert settings.logto_issuer == f"{endpoint.rstrip('/')}/oidc"


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

    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

    assert settings.git_sha == "local"


def test_git_sha_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SHA", "abc")

    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

    assert settings.git_sha == "abc"


def test_auth_mode_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_MODE")

    with pytest.raises(ValidationError):
        _ = Settings.model_validate({"_env_file": None})


def test_unknown_env_values_are_refused() -> None:
    with pytest.raises(ValidationError):
        _ = Settings.model_validate({"_env_file": None, "env": "staging", "auth_mode": "dev"})


def test_settings_errors_do_not_echo_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", SECRET_URL)

    with pytest.raises(ValidationError) as exc:
        _ = Settings.model_validate({"_env_file": None, "env": "production", "auth_mode": "dev"})

    assert "S3cretPW" not in str(exc.value)


def test_generation_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_generation_env(monkeypatch)
    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

    assert settings.card_generator == "ai"
    assert settings.ai_model == "gateway/openai:gpt-5.4-mini"
    assert settings.max_source_chars == 20_000
    assert settings.max_cards == 20
    assert settings.max_sources_per_day == 50


def test_due_cards_per_session_defaults_to_200(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.casefold() == "due_cards_per_session":
            monkeypatch.delenv(key, raising=False)

    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

    assert settings.due_cards_per_session == 200


def test_due_cards_per_session_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        _ = Settings.model_validate(
            {
                "_env_file": None,
                "database_url": SECRET_URL,
                "auth_mode": "dev",
                "due_cards_per_session": 0,
            }
        )


def test_gateway_models_require_the_gateway_key() -> None:
    with pytest.raises(ValidationError, match="PYDANTIC_AI_GATEWAY_API_KEY is required"):
        _ = Settings.model_validate(
            {
                "_env_file": None,
                "database_url": SECRET_URL,
                "auth_mode": "dev",
                "card_generator": "ai",
                "ai_model": "gateway/openai:gpt-5.4-mini",
                "pydantic_ai_gateway_api_key": "",
            }
        )


def test_ai_generation_requires_a_model() -> None:
    with pytest.raises(ValidationError, match="AI_MODEL is required"):
        _ = Settings.model_validate(
            {
                "_env_file": None,
                "database_url": SECRET_URL,
                "auth_mode": "dev",
                "card_generator": "ai",
                "ai_model": "",
            }
        )


def test_the_fake_generator_accepts_an_empty_model() -> None:
    settings = Settings.model_validate(
        {
            "_env_file": None,
            "database_url": SECRET_URL,
            "auth_mode": "dev",
            "card_generator": "fake",
            "ai_model": "",
            "pydantic_ai_gateway_api_key": "",
        }
    )

    assert settings.card_generator == "fake"


def test_direct_models_do_not_require_the_gateway_key() -> None:
    settings = Settings.model_validate(
        {
            "_env_file": None,
            "database_url": SECRET_URL,
            "auth_mode": "dev",
            "card_generator": "ai",
            "ai_model": "openai:gpt-4o",
            "pydantic_ai_gateway_api_key": "",
        }
    )

    assert settings.ai_model == "openai:gpt-4o"


def test_the_fake_generator_does_not_require_the_gateway_key() -> None:
    settings = Settings.model_validate(
        {
            "_env_file": None,
            "database_url": SECRET_URL,
            "auth_mode": "dev",
            "card_generator": "fake",
            "pydantic_ai_gateway_api_key": "",
        }
    )

    assert settings.card_generator == "fake"


def test_generation_env_cleanup_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("card_generator", "fake")
    _clear_generation_env(monkeypatch)

    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

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
    settings = Settings.model_validate(
        {"_env_file": None, "database_url": given, "auth_mode": "dev"}
    )

    assert settings.database_url.get_secret_value() == expected


def test_database_url_keeps_special_characters_in_the_password() -> None:
    url = "postgresql+asyncpg://u:p%40ss%2Fw@db.example/app"

    settings = Settings.model_validate({"_env_file": None, "database_url": url, "auth_mode": "dev"})

    assert settings.database_url.get_secret_value() == url


def test_an_unparseable_database_url_is_refused_without_echoing_it() -> None:
    with pytest.raises(ValidationError) as exc:
        _ = Settings.model_validate(
            {"_env_file": None, "database_url": "not a url S3cretPW", "auth_mode": "dev"}
        )

    assert "S3cretPW" not in str(exc.value)


def _production_settings(**changes: object) -> Settings:
    return Settings.model_validate(
        {
            "_env_file": None,
            "env": "production",
            "auth_mode": "logto",
            "database_url": SECRET_URL,
            "logto_endpoint": "https://tenant.logto.app",
            "logto_api_resource": "https://api.rekalled.app",
            "logto_app_id": "spa-app-id",
            "cors_origins": ["https://rekalled.app"],
            **changes,
        }
    )


def test_cors_origins_default_to_the_local_web_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

    assert settings.cors_origins == ["http://localhost:3000"]


def test_cors_origins_are_parsed_as_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["https://rekalled.app", "https://www.rekalled.app"]')

    settings = Settings.model_validate(
        {"_env_file": None, "database_url": SECRET_URL, "auth_mode": "dev"}
    )

    assert settings.cors_origins == ["https://rekalled.app", "https://www.rekalled.app"]


@pytest.mark.parametrize(
    "origins",
    [
        ["*"],  # wildcard
        [],  # a deploy that forgot CORS_ORIGINS would otherwise block the frontend
        ["http://localhost:3000"],
        ["http://127.0.0.1:3000"],
        ["http://[::1]:3000"],
    ],
)
def test_production_refuses_unsafe_cors_origins(origins: list[str]) -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        _ = _production_settings(cors_origins=origins)


def test_localhost_cors_origins_are_allowed_outside_production() -> None:
    settings = Settings.model_validate(
        {
            "_env_file": None,
            "env": "development",
            "database_url": SECRET_URL,
            "auth_mode": "dev",
            "cors_origins": ["http://localhost:3000"],
        }
    )

    assert settings.cors_origins == ["http://localhost:3000"]
