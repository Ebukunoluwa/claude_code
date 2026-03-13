from __future__ import annotations

from livekit.agents.tts import TTS
from livekit.plugins import elevenlabs

from config.settings import settings
from providers.base_tts import BaseTTSProvider


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs turbo v2.5 — fallback TTS."""

    def build(self) -> TTS:
        return elevenlabs.TTS(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model="eleven_turbo_v2_5",
            language="en",
        )
