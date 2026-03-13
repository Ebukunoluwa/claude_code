from __future__ import annotations

import logging

from openai import AsyncOpenAI
from livekit.agents.llm import LLM
from livekit.plugins import openai as lk_openai

from config.settings import settings
from providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI gpt-oss-120b — primary LLM."""

    def __init__(self) -> None:
        self._async_client = AsyncOpenAI(api_key=settings.openai_api_key)

    def build(self) -> LLM:
        return lk_openai.LLM(
            api_key=settings.openai_api_key,
            model="gpt-oss-120b",
        )

    async def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._async_client.chat.completions.create(
            model="gpt-oss-120b",
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        logger.debug("OpenAI batch completion: %d chars", len(content))
        return content
