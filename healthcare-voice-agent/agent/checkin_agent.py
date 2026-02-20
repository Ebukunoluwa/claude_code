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
        self._direction: str = "inbound"
        self._phone_number: str = ""
        self._next_appointment: str = "not yet scheduled"
        self._room_name: str = ""

        self._started_at: float = time.time()
        self._identity_state: Optional[IdentityState] = None
        self._conversation_turns: list[tuple[str, str]] = []  # [(role, text), ...]
        self._triage_level: TriageLevel = TriageLevel.GREEN
        self._triage_reasons: list[str] = []
        self._red_flag_triggered: bool = False
        self._session: Optional[AgentSession] = None

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle hooks
    # ─────────────────────────────────────────────────────────────────────────

    async def on_enter(self) -> None:
        """Called when the agent joins the room/session."""
        # Access session via self.session (available after super().on_enter())
        session = self.session

        # Read participant attributes forwarded by inbound_webhook / outbound_caller
        participant = session.room.remote_participants
        attrs: dict = {}
        if participant:
            first = next(iter(participant.values()))
            attrs = dict(first.attributes) if first.attributes else {}

        self._call_id = attrs.get("call_id", self._call_id)
        self._patient_name = attrs.get("patient_name", "Patient")
        self._nhs_number = attrs.get("nhs_number", "")
        self._direction = attrs.get("direction", "inbound")
        self._phone_number = attrs.get("phone_number", "")
        self._next_appointment = attrs.get("next_appointment", "not yet scheduled")
        self._room_name = attrs.get("room_name", getattr(session.room, "name", ""))

        logger.info(
            "CheckInAgent entering — call_id=%s patient=%s direction=%s",
            self._call_id,
            self._patient_name,
            self._direction,
        )

        self._identity_state = IdentityState(
            expected_name=self._patient_name,
            expected_nhs_number=self._nhs_number,
        )

        # Set the system prompt dynamically
        self.instructions = build_system_prompt(
            patient_name=self._patient_name,
            nhs_number=self._nhs_number,
            next_appointment=self._next_appointment,
        )

        # Open call record in SQLite
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

        transcript_text = "\n".join(
            f"[{role.upper()}]: {text}" for role, text in self._conversation_turns
        )

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

    # ─────────────────────────────────────────────────────────────────────────
    # Conversation hooks
    # ─────────────────────────────────────────────────────────────────────────

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        """Real-time triage after every patient utterance."""
        text = new_message.content or ""
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
        text = new_message.content or ""
        self._conversation_turns.append(("agent", text))
