from pydantic import SecretStr

from app.core.config import Settings
from app.llm import chat_model

# Gateway keys encode their region: pylf_v<version>_<region>_<secret>. This one is made up.
FAKE_KEY = SecretStr("pylf_v1_eu_not-a-real-key")


def test_gateway_models_use_the_key_from_settings_and_its_region() -> None:
    # model_validate, not Settings(...): database_url/auth_mode come from the environment
    # (set in conftest.py), which the type checker cannot see.
    settings = Settings.model_validate(
        {"ai_model": "gateway/openai:gpt-5.4-mini", "pydantic_ai_gateway_api_key": FAKE_KEY}
    )
    model = chat_model(settings)

    assert model.model_name == "gpt-5.4-mini"
    assert model.base_url is not None
    assert model.base_url.startswith("https://gateway-eu.pydantic.dev/proxy/openai")
