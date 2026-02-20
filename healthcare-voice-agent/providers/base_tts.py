from __future__ import annotations

from abc import ABC, abstractmethod

from livekit.agents.tts import TTS


class BaseTTSProvider(ABC):
    """Abstract factory for text-to-speech providers."""

    @abstractmethod
    def build(self) -> TTS:
        """Return a LiveKit-compatible TTS instance."""
        ...
