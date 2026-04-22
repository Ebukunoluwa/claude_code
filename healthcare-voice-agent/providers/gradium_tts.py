from __future__ import annotations

from livekit.agents.tts import TTS
from livekit.plugins import gradium

from config.settings import settings
from providers.base_tts import BaseTTSProvider


class GradiumTTSProvider(BaseTTSProvider):
    """Gradium TTS — primary voice.
    Speed, stability and similarity are passed via json_config in the setup message.
    Sample rate is fixed at 48 kHz by the plugin.
    """

    def build(self) -> TTS:
        return gradium.TTS(
            api_key=settings.gradium_api_key,
            model_endpoint=settings.gradium_model_endpoint,
            voice_id=settings.gradium_voice_id or None,
            json_config={
                "speed": 0.3,
                "stability": 0.4,
                "similarity_boost": 3.5,
            },
        )
