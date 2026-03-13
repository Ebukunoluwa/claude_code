from __future__ import annotations

from livekit.agents.tts import TTS
from livekit.plugins import cartesia

from config.settings import settings
from providers.base_tts import BaseTTSProvider


class CartesiaTTSProvider(BaseTTSProvider):
    """Cartesia Sonic-3 TTS with a male British English voice."""

    def build(self) -> TTS:
        return cartesia.TTS(
            api_key=settings.cartesia_api_key,
            model="sonic-3",
            voice=settings.cartesia_voice_id,
            language="en",
        )
