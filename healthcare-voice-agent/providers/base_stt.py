from __future__ import annotations

from abc import ABC, abstractmethod

from livekit.agents.stt import STT


class BaseSTTProvider(ABC):
    """Abstract factory for speech-to-text providers."""

    @abstractmethod
    def build(self) -> STT:
        """Return a LiveKit-compatible STT instance."""
        ...
