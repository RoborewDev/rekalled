from app.llm import chat_model
from pydantic import SecretStr

from app.core.config import Settings

# Gateway keys encode their region: pylf_v<version>_<region>_<secret>. This one is made up.
FAKE_KEY = SecretStr("pylf_v1_eu_not-a-real-key")


def test_gateway_models_use_the_key_from_settings_and_its_region():
    settings = Settings(
        ai_model="gateway/openai:gpt-5.4-mini", pydantic_ai_gateway_api_key=FAKE_KEY
    )

    model = chat_model(settings)

    assert model.model_name == "gpt-5.4-mini"
    assert model.base_url is not None
    assert model.base_url.startswith("https://gateway-eu.pydantic.dev/proxy/openai")
