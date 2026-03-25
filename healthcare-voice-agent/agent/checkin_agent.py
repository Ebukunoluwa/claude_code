from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional

from livekit.agents import Agent, AgentSession
from livekit.agents.llm import ChatContext, ChatMessage

from agent.identity_verification import IdentityState
from agent.system_prompt import build_system_prompt
from agent.triage import RED_ESCALATION_PHRASE, TriageLevel, classify_turn
from config.settings import settings
from processing.pipeline import run_post_call_pipeline
from sizor_ai.client import ingest_call as sizor_ingest, get_patient_call_context
from storage.database import get_db
from storage.models import Call
from storage.repositories import insert_call, update_call_status

logger = logging.getLogger(__name__)


class CheckInAgent(Agent):
    """
    NHS post-appointment check-in voice agent.

    Lifecycle:
      1. on_enter()              — read participant attributes, persist call record
      2. on_user_turn_completed  — real-time triage on every patient utterance
      3. on_exit()               — close call record, fire post-call pipeline
    """

    def __init__(self) -> None:
        super().__init__(instructions="")  # overridden in on_enter

        self._call_id: str = str(uuid.uuid4())
        self._patient_name: str = "Unknown Patient"
        self._nhs_number: str = ""
        self._patient_id: str = ""  # sizor patient_id if available
        self._direction: str = "inbound"
        self._phone_number: str = ""
        self._next_appointment: str = "not yet scheduled"
        self._room_name: str = ""

        self._started_at: float = time.time()
        self._identity_state: Optional[IdentityState] = None
        self._conversation_turns: list[tuple[str, str]] = []  # [(role, text), ...]
        self._turn_end_time: float = 0.0  # when user last finished speaking
        self._triage_level: TriageLevel = TriageLevel.GREEN
        self._triage_reasons: list[str] = []
        self._red_flag_triggered: bool = False
        self._session: Optional[AgentSession] = None

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle hooks
    # ─────────────────────────────────────────────────────────────────────────

    async def on_enter(self) -> None:
        """Called when the agent joins the room/session."""
        # ── 1. Read participant attributes (best-effort) ──────────────────────
        try:
            session = self.session
            remote_participants = session.room_io.room.remote_participants
            attrs: dict = {}
            if remote_participants:
                first = next(iter(remote_participants.values()))
                attrs = dict(first.attributes) if first.attributes else {}

            self._call_id = attrs.get("call_id", self._call_id)
            self._patient_name = attrs.get("patient_name", "Patient")
            self._nhs_number = attrs.get("nhs_number", "")
            self._patient_id = attrs.get("patient_id", "")
            self._direction = attrs.get("direction", "inbound")
            self._phone_number = attrs.get("phone_number", "")
            self._next_appointment = attrs.get("next_appointment", "not yet scheduled")
            self._room_name = attrs.get("room_name", session.room_io.room.name)
            self._is_probe = attrs.get("is_probe", "false") == "true"
            self._probe_call_id = attrs.get("probe_call_id", "")
            self._probe_prompt = attrs.get("probe_prompt", "")
        except Exception as exc:
            logger.warning("Could not read participant attributes: %s", exc)

        logger.info(
            "CheckInAgent entering — call_id=%s patient=%s direction=%s",
            self._call_id, self._patient_name, self._direction,
        )

        self._identity_state = IdentityState(
            expected_name=self._patient_name,
            expected_nhs_number=self._nhs_number,
        )

        # Set the system prompt — use probe prompt if this is a probe call
        if self._is_probe and self._probe_prompt:
            prompt = self._probe_prompt
            logger.info("Probe call — using clinician-generated prompt (%d chars)", len(prompt))
        else:
            # Fetch previous call context to enable conversation continuity
            previous_context = None
            if self._nhs_number:
                try:
                    previous_context = await get_patient_call_context(self._nhs_number)
                    if previous_context:
                        logger.info(
                            "Loaded previous call context — %d summaries, %d open flags",
                            len(previous_context.get("call_summaries", [])),
                            len(previous_context.get("open_flags", [])),
                        )
                except Exception as exc:
                    logger.warning("Could not fetch call context: %s", exc)

            prompt = build_system_prompt(
                patient_name=self._patient_name,
                nhs_number=self._nhs_number,
                next_appointment=self._next_appointment,
                previous_context=previous_context,
            )
        try:
            await self.update_instructions(prompt)
            logger.info("System prompt applied — %d chars", len(prompt))
        except Exception as exc:
            logger.error("update_instructions failed: %s", exc, exc_info=True)
            # Fallback: set directly on the agent
            self._instructions = prompt

        # ── 2. Persist call record (best-effort) ──────────────────────────────
        try:
            call = Call(
                call_id=self._call_id,
                patient_name=self._patient_name,
                nhs_number=self._nhs_number,
                phone_number=self._phone_number,
                direction=self._direction,
                status="in_progress",
                started_at=self._started_at,
                livekit_room=self._room_name,
            )
            async with get_db(settings.sqlite_db_path) as db:
                await insert_call(db, call)
        except Exception as exc:
            logger.warning("DB insert skipped: %s", exc)

        # ── 3. Wait for SIP participant to join then greet ───────────────────
        # on_enter fires when the agent joins, but the patient (SIP participant)
        # joins later when they actually answer the phone. Poll until they appear.
        room = self.session.room_io.room
        for _ in range(30):  # wait up to 30s
            if room.remote_participants:
                break
            await asyncio.sleep(1)
        else:
            logger.warning("No remote participant joined after 30s — call_id=%s", self._call_id)
            return

        await asyncio.sleep(1)  # brief pause after answer for audio to settle
        logger.info("Attempting session.say() greeting — call_id=%s", self._call_id)
        greeting = (
            f"Good day, this is Sarah calling from the NHS post-appointment care line. "
            f"Could I please speak with {self._patient_name}?"
        )
        try:
            await self.session.say(greeting)
            # Manually add to history so it appears in the transcript
            self.session.history.messages.append(
                ChatMessage(role="assistant", content=greeting)
            )
            logger.info("session.say() completed successfully")
        except Exception as exc:
            logger.error("session.say() failed: %s", exc, exc_info=True)

    def _build_transcript(self) -> str:
        """
        Build the full conversation transcript from the live chat context.
        Captures session.say() calls (greeting) and all LLM responses.
        Falls back to _conversation_turns if chat_ctx is unavailable or empty.
        """
        lines = []
        try:
            for msg in self.session.history.messages:
                # ChatRole may be a str enum or a plain enum — normalise to str
                role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                if role not in ("assistant", "user"):
                    continue
                content = msg.content
                if isinstance(content, list):
                    text = " ".join(
                        p if isinstance(p, str) else getattr(p, "text", "")
                        for p in content
                        if p
                    )
                elif isinstance(content, str):
                    text = content
                else:
                    continue
                text = text.strip()
                if not text:
                    continue
                label = "AGENT" if role == "assistant" else "PATIENT"
                lines.append(f"[{label}]: {text}")
        except Exception as exc:
            logger.warning("history transcript failed: %s", exc)

        # Fall back to incrementally-built turns if chat_ctx gave us nothing
        if not lines:
            lines = [
                f"[{r.upper()}]: {t}"
                for r, t in self._conversation_turns
                if t.strip()
            ]
        return "\n".join(lines)

    async def on_exit(self) -> None:
        """Called when the session ends."""
        ended_at = time.time()
        duration = ended_at - self._started_at

        logger.info(
            "CheckInAgent exiting — call_id=%s duration=%.1fs triage=%s",
            self._call_id,
            duration,
            self._triage_level,
        )

        async with get_db(settings.sqlite_db_path) as db:
            await update_call_status(
                db,
                call_id=self._call_id,
                status="completed",
                ended_at=ended_at,
                duration_seconds=duration,
                identity_verified=(
                    self._identity_state.verified if self._identity_state else False
                ),
            )

        transcript_text = self._build_transcript()

        asyncio.create_task(
            run_post_call_pipeline(
                call_id=self._call_id,
                patient_name=self._patient_name,
                transcript=transcript_text,
                turn_count=len(self._conversation_turns),
                realtime_triage_level=self._triage_level.value,
                realtime_triage_reasons=self._triage_reasons,
            )
        )

        # Push to Sizor AI platform for full clinical pipeline + dashboard
        asyncio.create_task(
            sizor_ingest(
                call_id=self._call_id,
                nhs_number=self._nhs_number,
                transcript=transcript_text,
                direction=self._direction,
                duration_seconds=duration,
                patient_id=self._patient_id or None,
                probe_call_id=self._probe_call_id or None,
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Conversation hooks
    # ─────────────────────────────────────────────────────────────────────────

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        """Real-time triage after every patient utterance."""
        self._turn_end_time = time.time()
        content = new_message.content
        if isinstance(content, list):
            text = " ".join(
                p if isinstance(p, str) else getattr(p, "text", "")
                for p in content
            )
        else:
            text = content or ""
        self._conversation_turns.append(("patient", text))

        level, reasons = classify_turn(text)

        if level == TriageLevel.RED and not self._red_flag_triggered:
            self._red_flag_triggered = True
            self._triage_level = TriageLevel.RED
            self._triage_reasons.extend(reasons)
            logger.warning(
                "RED flag triggered — call_id=%s reasons=%s",
                self._call_id,
                reasons,
            )
            # Interrupt the normal conversation and deliver the escalation phrase
            await self.session.say(RED_ESCALATION_PHRASE, allow_interruptions=False)
            # Brief pause for TTS to complete, then close
            await asyncio.sleep(10)
            await self.session.aclose()
            return

        if level == TriageLevel.AMBER and self._triage_level == TriageLevel.GREEN:
            self._triage_level = TriageLevel.AMBER
            self._triage_reasons.extend(reasons)
            logger.info(
                "AMBER flag — call_id=%s reasons=%s",
                self._call_id,
                reasons,
            )

    async def on_agent_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        """Record agent turns for the full transcript."""
        if self._turn_end_time:
            latency = time.time() - self._turn_end_time
            logger.info("LATENCY user→agent: %.3fs", latency)
            self._turn_end_time = 0.0
        content = new_message.content
        if isinstance(content, list):
            text = " ".join(
                p if isinstance(p, str) else getattr(p, "text", "")
                for p in content
            )
        else:
            text = content or ""
        self._conversation_turns.append(("agent", text))

        # Close the session automatically after the agent says goodbye
        lower = text.lower()
        if any(w in lower for w in ("goodbye", "take care", "bye", "farewell")):
            logger.info("Goodbye detected — closing session in 5s — call_id=%s", self._call_id)
            asyncio.create_task(self._close_after_delay(5.0))

    async def _close_after_delay(self, delay: float = 5.0) -> None:
        await asyncio.sleep(delay)
        try:
            await self.session.aclose()
        except Exception:
            pass
