"""
LLMClient — single abstraction layer over all LLM providers via LiteLLM.

Change LLM_MODEL in .env to swap models. No other code changes needed.

Supported examples:
  gpt-4o, gpt-4o-mini, gpt-oss-120b          (OpenAI)
  claude-sonnet-4-20250514                     (Anthropic Claude)
  groq/llama-3.3-70b-versatile                 (Groq)
  meta-llama/Llama-3-70b-instruct              (via LiteLLM)

ALL AI calls throughout the application go through this class.
Never call any provider SDK directly.
"""
import os
from litellm import acompletion
from ..config import settings


class LLMClient:
    def __init__(self, model: str | None = None):
        self.model = model or settings.llm_model
        # Set API keys from settings so LiteLLM picks them up
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        if settings.groq_api_key:
            os.environ["GROQ_API_KEY"] = settings.groq_api_key

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await acompletion(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""


# Singleton instance — import this throughout the app
llm_client = LLMClient()
