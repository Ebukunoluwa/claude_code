from __future__ import annotations

"""
Agent worker entrypoint.

Run:
    python -m agent.worker start     # production (connects to LiveKit cloud)
    python -m agent.worker dev       # local microphone / playground
"""

import logging

from livekit.agents import (
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents import llm, stt, tts
from livekit.plugins import silero

from agent.checkin_agent import CheckInAgent
from config.settings import settings
from providers.cartesia_tts import CartesiaTTSProvider
from providers.deepgram_stt import DeepgramSTTProvider
from providers.groq_llm import GroqLLMProvider
from providers.openai_llm import OpenAILLMProvider
from providers.assemblyai_stt import AssemblyAISTTProvider
from providers.elevenlabs_tts import ElevenLabsTTSProvider

logger = logging.getLogger(__name__)


def prewarm(proc) -> None:
    """Pre-load the VAD model once before handling any call."""
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Silero VAD pre-warmed")


async def entrypoint(ctx: JobContext) -> None:
    """Invoked by the LiveKit worker for each new room/job."""
    await ctx.connect()

    vad = ctx.proc.userdata.get("vad") or silero.VAD.load()

    # ── STT: Deepgram → AssemblyAI multilingual fallback ─────────────────────
    stt_instance = stt.FallbackAdapter([
        DeepgramSTTProvider().build(),
        AssemblyAISTTProvider().build(),
    ])

    # ── TTS: Cartesia → ElevenLabs fallback ──────────────────────────────────
    tts_instance = tts.FallbackAdapter([
        CartesiaTTSProvider().build(),
        ElevenLabsTTSProvider().build(),
    ])

    # ── LLM: OpenAI gpt-oss-120b → Groq fallback ─────────────────────────────
    llm_instance = llm.FallbackAdapter([
        OpenAILLMProvider().build(),
        GroqLLMProvider().build(),
    ])

    agent = CheckInAgent()

    session = AgentSession(
        vad=vad,
        stt=stt_instance,
        llm=llm_instance,
        tts=tts_instance,
    )

    await session.start(
        agent=agent,
        room=ctx.room,
    )

    logger.info("AgentSession started — room=%s", ctx.room.name)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
            ws_url=settings.livekit_url,
        )
    )
