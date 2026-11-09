"""Run the real LlmCardGenerator once. Not run in CI.

PYDANTIC_AI_GATEWAY_API_KEY=pylf_v1_... uv run python -m scripts.try_generator < some-notes.txt
"""

import asyncio
import sys

from app.core.config import get_settings
from app.generation.llm_generator import LlmCardGenerator


async def main() -> None:
    generator = LlmCardGenerator.from_settings(get_settings())
    for card in await generator.generate(sys.stdin.read(), max_cards=10):
        print(f"Q: {card.question}\nA: {card.answer}\n   ↳ {card.source_excerpt}\n")


asyncio.run(main())
