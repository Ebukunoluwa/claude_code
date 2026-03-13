from __future__ import annotations

from livekit.agents.stt import STT
from livekit.plugins import assemblyai

from config.settings import settings
from providers.base_stt import BaseSTTProvider


class AssemblyAISTTProvider(BaseSTTProvider):
    """AssemblyAI universal-streaming-multilingual — fallback STT with multilingual turn detection."""

    def build(self) -> STT:
        return assemblyai.STT(
            api_key=settings.assemblyai_api_key,
            model="universal-streaming-multilingual",
            language_detection=True,
        )
