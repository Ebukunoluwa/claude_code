from __future__ import annotations

"""
Unified agent worker — handles inbound, outbound, and probe calls.

Room prefix → agent:
  inbound-  → SizorInboundAgent  (patient called in)
  probe-    → CheckInAgent       (clinician-triggered probe)
  call-     → CheckInAgent       (scheduled post-appointment)

Run:
    python -m agent.worker start
"""

import logging

from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.agents import llm, stt, tts
from livekit.plugins import cartesia, deepgram, silero
from livekit.plugins import openai as lk_openai

from agent.checkin_agent import CheckInAgent
from agent.sizor_inbound_agent import SizorInboundAgent
from config.settings import settings
from providers.cartesia_tts import CartesiaTTSProvider
from providers.deepgram_stt import DeepgramSTTProvider
from providers.groq_llm import GroqLLMProvider
from providers.openai_llm import OpenAILLMProvider
from providers.assemblyai_stt import AssemblyAISTTProvider
from providers.elevenlabs_tts import ElevenLabsTTSProvider

logger = logging.getLogger(__name__)


def prewarm(proc) -> None:
    proc.userdata["vad"] = silero.VAD.load(
        min_silence_duration=1.2,
        min_speech_duration=0.1,
        padding_duration=0.4,
    )
    logger.info("Silero VAD pre-warmed")


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    room_name = ctx.room.name
    vad = ctx.proc.userdata.get("vad") or silero.VAD.load(min_silence_duration=0.9)

    if room_name.startswith("inbound-"):
        # ── Patient called in → inbound agent ────────────────────────────────
        logger.info("Inbound call — room=%s", room_name)

        stt_instance = deepgram.STT(
            api_key=settings.deepgram_api_key,
            model="nova-3-general",
            language="en-GB",
        )
        tts_instance = cartesia.TTS(
            api_key=settings.cartesia_api_key,
            model="sonic-3",
            voice=settings.cartesia_voice_id,
            language="en",
        )
        llm_instance = lk_openai.LLM(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",
        )
        agent = SizorInboundAgent()

    else:
        # ── Outbound or probe call → checkin agent ────────────────────────────
        call_type = "probe" if room_name.startswith("probe-") else "outbound"
        logger.info("%s call — room=%s", call_type, room_name)

        stt_instance = stt.FallbackAdapter([
            DeepgramSTTProvider().build(),
            AssemblyAISTTProvider().build(),
        ])
        tts_instance = tts.FallbackAdapter([
            CartesiaTTSProvider().build(),
            ElevenLabsTTSProvider().build(),
        ])
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

    await session.start(agent=agent, room=ctx.room)
    logger.info("AgentSession started — room=%s", room_name)


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
