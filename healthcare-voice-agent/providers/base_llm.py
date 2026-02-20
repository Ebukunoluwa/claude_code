from __future__ import annotations

from abc import ABC, abstractmethod

from livekit.agents.llm import LLM


class BaseLLMProvider(ABC):
    """Abstract factory for LLM providers."""

    @abstractmethod
    def build(self) -> LLM:
        """Return a LiveKit-compatible streaming LLM instance."""
        ...

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> str:
        """One-shot batch completion (no streaming). Used for post-call processing."""
        ...
