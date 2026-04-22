from __future__ import annotations

from livekit.agents.stt import STT
from livekit.plugins import deepgram

from config.settings import settings
from providers.base_stt import BaseSTTProvider


class DeepgramSTTProvider(BaseSTTProvider):
    """Deepgram Nova-3, en-GB, streaming STT."""

    def build(self) -> STT:
        return deepgram.STT(
            api_key=settings.deepgram_api_key,
            model="nova-3-general",
            language="en-GB",
        )
