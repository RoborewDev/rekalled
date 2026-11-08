from pydantic import SecretStr

from app.api.deps import get_card_generator
from app.core.config import Settings
from app.generation.fake import FakeCardGenerator
from app.generation.llm_generator import LlmCardGenerator

SECRET_URL = "postgresql+asyncpg://u:p@localhost:5432/rekalled"
FAKE_KEY = SecretStr("pylf_v1_eu_test-not-a-real-key")


def _settings(**changes: object) -> Settings:
    # _env_file=None: the assertions below must not depend on a developer's .env.
    return Settings.model_validate(
        {
            "_env_file": None,
            "database_url": SECRET_URL,
            "auth_mode": "dev",
            "pydantic_ai_gateway_api_key": FAKE_KEY,
            **changes,
        }
    )


def test_the_fake_setting_selects_the_fake_generator() -> None:
    assert isinstance(get_card_generator(_settings(card_generator="fake")), FakeCardGenerator)


def test_the_ai_setting_selects_the_llm_generator() -> None:
    # The routes depend on app.api.deps, so this is the wiring the endpoints actually use.
    assert isinstance(get_card_generator(_settings(card_generator="ai")), LlmCardGenerator)
