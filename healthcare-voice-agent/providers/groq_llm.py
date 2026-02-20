from __future__ import annotations

import logging

from openai import AsyncOpenAI
from livekit.agents.llm import LLM
from livekit.plugins import openai as lk_openai

from config.settings import settings
from providers.base_llm import BaseLLMProvider

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqLLMProvider(BaseLLMProvider):
    """
    Groq Llama-3 via OpenAI-compatible API.

    - build()    → LiveKit streaming LLM (used by the agent pipeline)
    - complete() → AsyncOpenAI one-shot completion (used post-call)
    """

    def __init__(self) -> None:
        self._async_client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=_GROQ_BASE_URL,
        )

    def build(self) -> LLM:
        return lk_openai.LLM(
            api_key=settings.groq_api_key,
            base_url=_GROQ_BASE_URL,
            model=settings.groq_model,
        )

    async def complete(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._async_client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        logger.debug("Groq batch completion: %d chars", len(content))
        return content
