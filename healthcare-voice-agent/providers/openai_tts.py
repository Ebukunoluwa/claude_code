from __future__ import annotations

import os
from livekit.agents.tts import TTS
from livekit.plugins import openai as lk_openai

from config.settings import settings
from providers.base_tts import BaseTTSProvider


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS — British-accented female voice (nova)."""

    def build(self) -> TTS:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        return lk_openai.TTS(
            model="tts-1",
            voice="nova",
        )
