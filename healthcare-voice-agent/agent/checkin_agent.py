from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Optional

from livekit import api as lk_api
from livekit.agents import Agent, AgentSession
from livekit.agents.llm import ChatContext, ChatMessage

# Spoken-word digit map for NHS number extraction from speech
_WORD_TO_DIGIT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "oh": "0", "nought": "0", "o": "0",
}

# For spoken date-of-birth parsing
_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
_ORDINAL_MAP = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "twenty": 20,
    "twenty-first": 21, "twentyfirst": 21,
    "twenty-second": 22, "twentysecond": 22,
    "twenty-third": 23, "twentythird": 23,
    "twenty-fourth": 24, "twentyfourth": 24,
    "twenty-fifth": 25, "twentyfifth": 25,
    "twenty-sixth": 26, "twentysixth": 26,
    "twenty-seventh": 27, "twentyseventh": 27,
    "twenty-eighth": 28, "twentyeighth": 28,
    "twenty-ninth": 29, "twentyninth": 29,
    "thirtieth": 30, "thirty": 30,
    "thirty-first": 31, "thirtyfirst": 31,
}
_NUMBER_WORD_MAP = {
    "nineteen": 19, "eighteen": 18, "seventeen": 17, "sixteen": 16,
    "fifteen": 15, "fourteen": 14, "thirteen": 13, "twelve": 12,
    "eleven": 11, "ten": 10, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "zero": 0, "oh": 0,
}

from agent.identity_verification import IdentityState
from agent.system_prompt import build_system_prompt
from agent.triage import RED_FLAG_SYSTEM_INSTRUCTION, TriageLevel, classify_turn
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
        self._prompt_locked: bool = False   # True once clinical phase starts; blocks mid-call instruction updates
        self._turn_end_time: float = 0.0  # when user last finished speaking
        self._turn_latencies: list[float] = []  # user→agent latency per turn (seconds)
        self._triage_level: TriageLevel = TriageLevel.GREEN
        self._triage_reasons: list[str] = []
        self._red_flag_triggered: bool = False
        self._session: Optional[AgentSession] = None
        self._pending_dob_text: str = ""  # patient's original DOB speech, fallback if agent repeat empty
        self._said_goodbye: bool = False   # True when agent says farewell — signals clean call end
        self._is_continuation: bool = False  # True for continuation calls after a cut-off

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle hooks
    # ─────────────────────────────────────────────────────────────────────────

    async def on_enter(self) -> None:
        """Called when the agent joins the room/session."""
        # ── 0. Register agent-turn capture via conversation_item_added event ──
        # on_agent_turn_completed does not exist in livekit-agents 1.5+; instead
        # the session emits "conversation_item_added" for every message added to
        # the chat context, including assistant responses.
        def _on_conversation_item(event) -> None:
            try:
                msg = event.item
                if getattr(msg, "role", None) != "assistant":
                    return
                text = (msg.text_content or "").strip()
                if not text:
                    return
                # Track latency
                if self._turn_end_time:
                    latency = time.time() - self._turn_end_time
                    self._turn_latencies.append(latency)
                    logger.info(
                        "LATENCY turn=%d user→agent=%.3fs call_id=%s",
                        len(self._turn_latencies), latency, self._call_id,
                    )
                    self._turn_end_time = 0.0
                self._conversation_turns.append(("agent", text))
                # Capture DOB repeat for identity verification
                if (self._identity_state
                        and self._identity_state.awaiting_dob_confirm
                        and not self._identity_state.agent_dob_repeat):
                    self._identity_state.agent_dob_repeat = text
                    logger.info("Captured agent DOB repeat: %r call_id=%s", text, self._call_id)
                # Auto-close after goodbye.
                # Only match words that exclusively appear in the closing script.
                # "take care" is intentionally excluded — it appears mid-call in clinical advice.
                lower = text.lower()
                _is_goodbye = (
                    "goodbye" in lower
                    or lower.rstrip(" .!").endswith("bye")
                    or lower.rstrip(" .!").endswith("bye now")
                )
                if _is_goodbye:
                    self._said_goodbye = True
                    logger.info("Goodbye detected — closing session in 5s — call_id=%s", self._call_id)
                    asyncio.create_task(self._close_after_delay(5.0))
            except Exception:
                pass
        self.session.on("conversation_item_added", _on_conversation_item)

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
            self._is_continuation = attrs.get("is_continuation", "false") == "true"
            # Discharge info passed directly from scheduler (fallback if context unavailable)
            raw_day = attrs.get("day_in_recovery", "")
            self._date_of_birth: str = attrs.get("date_of_birth", "")
            self._discharge_date: str = attrs.get("discharge_date", "")
            self._postcode: str = attrs.get("postcode", "")
            self._day_in_recovery: Optional[int] = int(raw_day) if raw_day.isdigit() else None
        except Exception as exc:
            logger.warning("Could not read participant attributes: %s", exc)

        logger.info(
            "CheckInAgent entering — call_id=%s patient=%s direction=%s dob=%r postcode=%r",
            self._call_id, self._patient_name, self._direction,
            self._date_of_birth, self._postcode,
        )

        self._identity_state = IdentityState(
            expected_name=self._patient_name,
            expected_nhs_number=self._nhs_number,
            expected_dob=self._date_of_birth,
            expected_postcode=self._postcode,
        )

        # Set instructions — probe calls use the pre-generated probe prompt directly;
        # continuation calls mark identity as already verified;
        # standard calls use a placeholder until the background context fetch completes.
        if self._is_probe and self._probe_prompt:
            await self.update_instructions(self._probe_prompt)
            self._prompt_locked = True  # probe calls never need background instruction updates
        else:
            # For continuation calls, pass the identity_verified flag via the prompt
            # but do NOT pre-mark as verified in state — let the prompt handle it.
            # (Identity was already marked verified in the prior call if it succeeded.)
            await self.update_instructions(
                build_system_prompt(
                    patient_name=self._patient_name,
                    nhs_number=self._nhs_number,
                    next_appointment=self._next_appointment,
                    previous_context=None,
                    postcode=self._postcode,
                    is_continuation=self._is_continuation,
                )
            )
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

        # ── 3. Wait for SIP participant to join then greet immediately ──────────
        # on_enter fires when the agent joins, but the patient (SIP participant)
        # joins later when they actually answer the phone. Poll until they appear.
        room = self.session.room_io.room
        for _ in range(30):  # wait up to 30s
            if room.remote_participants:
                break
            await asyncio.sleep(1)
        else:
            logger.warning("No remote participant joined after 30s — call_id=%s", self._call_id)
            # Mark call as missed in both local DB and Sizor platform
            self._call_missed = True
            try:
                async with get_db(settings.sqlite_db_path) as db:
                    await update_call_status(
                        db,
                        call_id=self._call_id,
                        status="missed",
                        ended_at=time.time(),
                        duration_seconds=0,
                        identity_verified=False,
                    )
            except Exception as exc:
                logger.warning("Could not mark call as missed in local DB: %s", exc)
            try:
                await sizor_ingest(
                    call_id=self._call_id,
                    nhs_number=self._nhs_number,
                    transcript="",
                    direction=self._direction,
                    duration_seconds=0,
                    patient_id=self._patient_id or None,
                    call_status="missed",
                )
            except Exception as exc:
                logger.warning("Could not notify Sizor of missed call: %s", exc)
            return

        # Re-read participant attributes now that SIP participant has definitely joined.
        # For outbound calls, on_enter fires before the patient answers, so attrs are
        # empty the first time. Re-reading here ensures DOB / postcode are populated.
        try:
            if room.remote_participants:
                joined = next(iter(room.remote_participants.values()))
                late_attrs = dict(joined.attributes) if joined.attributes else {}
                if not self._date_of_birth and late_attrs.get("date_of_birth"):
                    self._date_of_birth = late_attrs["date_of_birth"]
                    self._identity_state.expected_dob = self._date_of_birth
                    logger.info("Late-loaded DOB from SIP attrs: %r call_id=%s", self._date_of_birth, self._call_id)
                if not self._postcode and late_attrs.get("postcode"):
                    self._postcode = late_attrs["postcode"]
                    from agent.identity_verification import _normalise_postcode
                    self._identity_state.expected_postcode = _normalise_postcode(self._postcode)
                    logger.info("Late-loaded postcode from SIP attrs: %r call_id=%s", self._postcode, self._call_id)
                # Also pick up other attrs that may have been empty
                if not self._nhs_number and late_attrs.get("nhs_number"):
                    self._nhs_number = late_attrs["nhs_number"]
                if not self._patient_name or self._patient_name == "Patient":
                    if late_attrs.get("patient_name"):
                        self._patient_name = late_attrs["patient_name"]
                        self._identity_state.expected_name = self._patient_name
        except Exception as exc:
            logger.warning("Late attr re-read failed: %s", exc)

        # ── 4. Greet the patient immediately — do NOT wait for context fetch ───
        # Context fetching (especially playbook retries) can take minutes.
        # The patient must hear audio as soon as they answer or they'll hang up.
        await asyncio.sleep(1)  # brief pause for audio to settle after answer
        _first = self._patient_name.split()[0] if self._patient_name.split() else self._patient_name
        if self._is_probe:
            # Probe calls: minimal opener — the probe script handles full intro
            greeting = f"Hi, is that {_first}?"
        elif self._is_continuation:
            greeting = (
                f"Hi {_first}, it's Sarah again from the NHS care line — "
                f"apologies, we seem to have got cut off. Are you okay to continue?"
            )
        else:
            greeting = (
                f"Good day, this is Sarah calling from the NHS post-discharge care line. "
                f"Am I speaking with {_first}?"
            )
        logger.info("Attempting session.say() greeting — call_id=%s dob=%r postcode=%r",
                    self._call_id, self._date_of_birth, self._postcode)
        try:
            await self.session.say(greeting)
            logger.info("session.say() completed successfully — call_id=%s", self._call_id)
        except Exception as exc:
            logger.error("session.say() failed: %s", exc, exc_info=True)

        # ── 5. Fetch pathway context in the background and update prompt ────────
        # The placeholder prompt set in step 1 is already active; once the richer
        # context arrives we silently swap it in.  The patient conversation may have
        # already started by the time the fetch completes — that is fine.
        if not (self._is_probe and self._probe_prompt):
            asyncio.create_task(self._fetch_and_update_context())

    async def _fetch_and_update_context(self) -> None:
        """
        Fetch the patient's pathway context / playbook in the background and
        update the agent's instructions once it arrives.  Called as a Task
        immediately after the opening greeting so context fetching never
        delays the patient hearing audio.
        """
        previous_context = None
        if self._nhs_number:
            for fetch_attempt in range(3):
                try:
                    previous_context = await get_patient_call_context(self._nhs_number)
                    # If pathway exists but playbook not ready yet (still generating),
                    # retry up to 4 times with 5s gaps (20s max).
                    # We don't wait longer — _domain_template fallback covers any gap,
                    # and a 3-minute retry loop would freeze the conversation mid-call.
                    if (
                        previous_context
                        and (previous_context.get("pathway_label") or previous_context.get("opcs_code"))
                        and not previous_context.get("playbook")
                    ):
                        for attempt in range(4):
                            logger.info(
                                "Playbook not ready yet — retrying in 5s (attempt %d/4) call_id=%s",
                                attempt + 1, self._call_id,
                            )
                            await asyncio.sleep(5)
                            previous_context = await get_patient_call_context(self._nhs_number)
                            if previous_context and previous_context.get("playbook"):
                                break
                    if previous_context:
                        logger.info(
                            "Loaded call context — playbook=%s pathway=%r summaries=%d flags=%d call_id=%s",
                            "yes" if previous_context.get("playbook") else "no",
                            previous_context.get("pathway_label"),
                            len(previous_context.get("call_summaries", [])),
                            len(previous_context.get("open_flags", [])),
                            self._call_id,
                        )
                    break  # success — exit retry loop
                except Exception as exc:
                    logger.warning(
                        "Call context fetch failed (attempt %d/3): %s call_id=%s",
                        fetch_attempt + 1, exc, self._call_id,
                    )
                    if fetch_attempt < 2:
                        await asyncio.sleep(5)
                    else:
                        logger.error(
                            "All call context fetch attempts failed — using generic script. "
                            "call_id=%s nhs=%s", self._call_id, self._nhs_number,
                        )

        if previous_context is not None:
            if previous_context.get("day_in_recovery") is None and self._day_in_recovery is not None:
                previous_context["day_in_recovery"] = self._day_in_recovery
            if not previous_context.get("discharge_date") and self._discharge_date:
                previous_context["discharge_date"] = self._discharge_date
            if not self._identity_state.expected_dob and previous_context.get("date_of_birth"):
                self._identity_state.expected_dob = previous_context["date_of_birth"]
            if not self._identity_state.expected_postcode and previous_context.get("postcode"):
                from agent.identity_verification import _normalise_postcode
                self._identity_state.expected_postcode = _normalise_postcode(previous_context["postcode"])
        elif self._day_in_recovery is not None or self._discharge_date:
            previous_context = {
                "has_history": False,
                "day_in_recovery": self._day_in_recovery,
                "discharge_date": self._discharge_date or None,
                "playbook": None,
                "pathway_label": None,
                "red_flags": [],
            }

        prompt = build_system_prompt(
            patient_name=self._patient_name,
            nhs_number=self._nhs_number,
            next_appointment=self._next_appointment,
            previous_context=previous_context,
            postcode=self._postcode,
            is_continuation=self._is_continuation,
        )
        # Don't update instructions once the clinical phase has started — swapping the
        # system prompt mid-conversation causes the LLM to pause/freeze for several seconds.
        if self._prompt_locked:
            logger.info(
                "Prompt locked (clinical phase started) — skipping late instruction update call_id=%s",
                self._call_id,
            )
            return

        try:
            await self.update_instructions(prompt)
            logger.info(
                "System prompt updated with pathway context — %d chars playbook=%s call_id=%s",
                len(prompt),
                "yes" if previous_context and previous_context.get("playbook") else "no",
                self._call_id,
            )
        except Exception as exc:
            logger.error("update_instructions (background fetch) failed: %s", exc, exc_info=True)

    def _build_transcript(self) -> str:
        """
        Build the full conversation transcript from the live chat context.
        Captures session.say() calls (greeting) and all LLM responses.
        Falls back to _conversation_turns if chat_ctx is unavailable or empty.
        """
        # Use incrementally-built turns (captured in on_user/agent_turn_completed)
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

        # ── Latency summary ───────────────────────────────────────────────────
        latency_stats: dict = {}
        if self._turn_latencies:
            lats = sorted(self._turn_latencies)
            n = len(lats)
            avg = sum(lats) / n
            p95 = lats[min(int(n * 0.95), n - 1)]
            latency_stats = {
                "turns": n,
                "min_s": round(lats[0], 3),
                "max_s": round(lats[-1], 3),
                "avg_s": round(avg, 3),
                "p95_s": round(p95, 3),
            }
            logger.info(
                "LATENCY SUMMARY call_id=%s turns=%d min=%.3fs avg=%.3fs p95=%.3fs max=%.3fs",
                self._call_id, n, lats[0], avg, p95, lats[-1],
            )
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

        # Detect cut-off: real conversation happened but call ended without a goodbye.
        # Lower threshold to 2 turns so early cut-offs are also caught.
        # Identity verification is NOT required — if the call cut off during verification
        # the continuation call will re-verify cleanly.
        _real_turns = len(self._conversation_turns)
        _was_cut_off = (
            _real_turns >= 2
            and not self._said_goodbye
            and not self._is_probe          # probe calls don't continue
            and not self._is_continuation   # don't chain continuation → continuation
        )
        final_call_status = "cut_off" if _was_cut_off else None
        if _was_cut_off:
            logger.info(
                "Call cut off after %d turns (goodbye=%s) — scheduling continuation — call_id=%s",
                _real_turns, self._said_goodbye, self._call_id,
            )
        else:
            logger.info(
                "Call ended cleanly — turns=%d goodbye=%s probe=%s continuation=%s call_id=%s",
                _real_turns, self._said_goodbye, self._is_probe, self._is_continuation, self._call_id,
            )

        # Push to Sizor AI platform for full clinical pipeline + dashboard.
        # Awaited directly so it completes before the session fully closes —
        # fire-and-forget tasks get cancelled when the room is deleted.
        await sizor_ingest(
            call_id=self._call_id,
            nhs_number=self._nhs_number,
            transcript=transcript_text,
            direction=self._direction,
            duration_seconds=duration,
            patient_id=self._patient_id or None,
            probe_call_id=self._probe_call_id or None,
            latency_stats=latency_stats or None,
            call_status=final_call_status,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Conversation hooks
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_dob_digits(self, text: str) -> str:
        """
        Extract date-of-birth from spoken or typed input.
        Returns DDMMYYYY (8 chars) or "" on failure.

        Handles:
          "14/03/1958"  "14-03-1958"  "14 03 1958"   (numeric)
          "14th March 1958"  "14th of March 1958"      (mixed)
          "fourteenth of March nineteen fifty-eight"   (fully spoken)
          "third July eighty-two"                      (short year)
        """
        t = text.lower().strip()
        # Normalise: strip ordinal suffixes (1st→1, 2nd→2, etc.)
        t = re.sub(r"(\d+)(?:st|nd|rd|th)\b", r"\1", t)
        # Replace separators with spaces (incl. dot for 18.09.1995)
        t = re.sub(r"[/\-,.]", " ", t)

        # ── Pass 1: all-numeric parts DD MM YYYY ──────────────────────────────
        num_parts = [p for p in t.split() if p.isdigit()]
        if len(num_parts) >= 3:
            d, m, y_raw = num_parts[0], num_parts[1], num_parts[2]
            if len(y_raw) == 2:
                y_raw = ("19" if int(y_raw) >= 20 else "20") + y_raw
            if (len(y_raw) == 4 and 1900 <= int(y_raw) <= 2099
                    and 1 <= int(d) <= 31 and 1 <= int(m) <= 12):
                return f"{int(d):02d}{int(m):02d}{y_raw}"
        # Two-part year: "14 03 19 58"
        if len(num_parts) >= 4:
            d, m = num_parts[0], num_parts[1]
            y_raw = num_parts[2] + num_parts[3]
            if (len(y_raw) == 4 and 1900 <= int(y_raw) <= 2099
                    and 1 <= int(d) <= 31 and 1 <= int(m) <= 12):
                return f"{int(d):02d}{int(m):02d}{y_raw}"

        # ── Pass 2: spoken words ───────────────────────────────────────────────
        words = t.split()
        day, month, year = None, None, None

        # Join two-word compound ordinals: "twenty first" → "twenty-first"
        _TENS_WORDS = {"twenty", "thirty"}
        _UNIT_ORDINALS = {
            "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
        }
        merged: list[str] = []
        i = 0
        while i < len(words):
            if (words[i] in _TENS_WORDS and i + 1 < len(words)
                    and words[i + 1] in _UNIT_ORDINALS):
                merged.append(words[i] + "-" + words[i + 1])
                i += 2
            else:
                merged.append(words[i])
                i += 1
        words = merged

        # Find month name and remove it
        for i, w in enumerate(words):
            if w in _MONTH_MAP:
                month = _MONTH_MAP[w]
                words.pop(i)
                break

        # Find day: ordinal word or bare number ≤ 31
        for i, w in enumerate(words):
            if w in _ORDINAL_MAP:
                day = _ORDINAL_MAP[w]
                words.pop(i)
                break
            if w.isdigit() and 1 <= int(w) <= 31:
                day = int(w)
                words.pop(i)
                break

        # Find year: 4-digit literal or 2-digit shorthand ("95" → 1995)
        for i, w in enumerate(words):
            if w.isdigit() and len(w) == 4 and 1900 <= int(w) <= 2099:
                year = int(w)
                words.pop(i)
                break
            if w.isdigit() and len(w) == 2:
                y2 = int(w)
                year = 1900 + y2 if y2 >= 20 else 2000 + y2
                words.pop(i)
                break

        # Find year: spoken — "nineteen fifty-eight" → 1958, "two thousand and three" → 2003
        if year is None:
            century = None
            decade_units = 0
            skip_next = False
            for idx, w in enumerate(words):
                if skip_next:
                    skip_next = False
                    continue
                if w == "nineteen":
                    century = 1900
                elif w == "two" and idx + 1 < len(words) and words[idx + 1] == "thousand":
                    century = 2000
                    skip_next = True
                elif w in ("twenty",) and century is None:
                    century = 2000
                elif w in ("and", "of", "the"):
                    continue
                elif w in _NUMBER_WORD_MAP and century is not None:
                    v = _NUMBER_WORD_MAP[w]
                    if v < 100:
                        decade_units += v
            if century is not None:
                candidate = century + decade_units
                if 1900 <= candidate <= 2099:
                    year = candidate

        if day and month and year:
            return f"{day:02d}{month:02d}{year}"

        # ── Pass 3: last resort — strip all non-digits ─────────────────────────
        return re.sub(r"\D", "", text)

    def _extract_digits(self, text: str) -> str:
        """
        Extract digits from patient speech — handles both:
          - direct digits:  "9434765919" or "943 476 5919"
          - spoken words:   "nine four three four seven six five nine one nine"
        Returns the best digit string candidate.
        """
        # Raw digits first
        raw = re.sub(r"\D", "", text)

        # Word-by-word conversion
        words = re.sub(r"[^a-z0-9 ]", "", text.lower()).split()
        spoken = "".join(_WORD_TO_DIGIT[w] for w in words if w in _WORD_TO_DIGIT)

        # Return whichever is longer (more likely to be the NHS number)
        return raw if len(raw) >= len(spoken) else spoken

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        """Real-time triage + code-level identity verification on every patient utterance."""
        self._turn_end_time = time.time()
        content = new_message.content

        # Lock instructions once identity phase is complete (≥4 patient turns) to prevent
        # background context fetch from swapping the system prompt mid-clinical-assessment.
        if not self._prompt_locked and len(self._conversation_turns) >= 4:
            self._prompt_locked = True
            logger.info("Prompt locked — clinical phase reached call_id=%s", self._call_id)
        if isinstance(content, list):
            text = " ".join(
                p if isinstance(p, str) else getattr(p, "text", "")
                for p in content
            )
        else:
            text = content or ""
        self._conversation_turns.append(("patient", text))

        # ── Code-level identity verification ─────────────────────────────────
        if self._identity_state and not self._identity_state.verified:

            # Outbound: we dialled the patient so name is already known.
            if self._direction == "outbound" and not self._identity_state.name_confirmed:
                self._identity_state.name_confirmed = True
            # Inbound: match name from speech
            elif not self._identity_state.name_confirmed:
                if self._identity_state.verify_name(text):
                    logger.info("Name verified — call_id=%s", self._call_id)
                    turn_ctx.add_message(
                        role="system",
                        content="[VERIFICATION] Patient name confirmed. Now ask for their date of birth.",
                    )

            # ── Postcode fallback: DOB failed ─────────────────────────────────
            if self._identity_state.awaiting_postcode:
                upper = text.upper()
                candidates: list[str] = []
                pc_match = re.search(r"[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}", upper)
                if pc_match:
                    candidates.append(re.sub(r"\s+", "", pc_match.group(0)))
                alphanum = re.sub(r"[^A-Z0-9]", "", upper)
                if 5 <= len(alphanum) <= 7:
                    candidates.append(alphanum)
                elif len(alphanum) > 7:
                    for n in (7, 6, 5):
                        candidates.append(alphanum[-n:])

                verified_pc = False
                for cand in candidates:
                    if len(cand) >= 5 and self._identity_state.verify_postcode(cand):
                        verified_pc = True
                        break

                if verified_pc:
                    logger.info("Postcode verified — call_id=%s", self._call_id)
                    turn_ctx.add_message(
                        role="system",
                        content="[VERIFICATION] Postcode CONFIRMED. Identity verified. "
                            "Say: 'Thank you, I've verified your identity.' "
                            "then proceed to Phase 2.",
                    )
                elif candidates:
                    # Candidates found but none matched
                    logger.warning("Postcode mismatch — call_id=%s", self._call_id)
                    turn_ctx.add_message(
                        role="system",
                        content="[VERIFICATION] Postcode does NOT match our records. "
                            "Apologise warmly and tell them you cannot verify today. "
                            "Ask them to contact their GP or NHS 111 directly. "
                            "Continue the call without verifying.",
                    )
                else:
                    # Nothing postcode-like detected — ask again
                    turn_ctx.add_message(
                        role="system",
                        content="[VERIFICATION] Could not detect a postcode in what the patient said. "
                            "Ask them to say their postcode again slowly, one letter or number at a time if needed.",
                    )

            # ── DOB: patient confirming agent's repeat ─────────────────────────
            elif self._identity_state.awaiting_dob_confirm:
                lower = text.lower()
                confirmed = any(w in lower for w in (
                    "yes", "yeah", "yep", "correct", "right", "that's right",
                    "thats right", "that is", "exactly", "confirmed",
                ))
                denied = any(w in lower for w in (
                    "no", "nope", "wrong", "incorrect", "that's not", "thats not",
                    "not right", "not correct",
                ))
                if confirmed:
                    # _pending_dob_text already holds the extracted DDMMYYYY digits
                    candidate = self._pending_dob_text
                    logger.info(
                        "DOB confirm — extracted=%r expected=%r call_id=%s",
                        candidate, self._identity_state.expected_dob, self._call_id,
                    )
                    if candidate and self._identity_state.verify_dob(candidate):
                        logger.info("DOB verified — call_id=%s", self._call_id)
                        self._identity_state.awaiting_dob_confirm = False
                        self._pending_dob_text = ""
                        turn_ctx.add_message(
                            role="system",
                            content="[VERIFICATION] Date of birth CONFIRMED. Identity verified. "
                                "Say: 'Thank you, I've confirmed your identity.' "
                                "then proceed to Phase 2.",
                        )
                    else:
                        logger.warning(
                            "DOB mismatch — extracted=%r expected=%r call_id=%s",
                            candidate, self._identity_state.expected_dob, self._call_id,
                        )
                        self._identity_state.awaiting_dob_confirm = False
                        self._identity_state.dob_failed = True
                        self._pending_dob_text = ""
                        turn_ctx.add_message(
                            role="system",
                            content="[VERIFICATION] Date of birth does NOT match our records. "
                                "Say warmly: 'Not to worry — could I take your postcode instead?' "
                                "Wait for their postcode.",
                        )
                elif denied:
                    self._identity_state.awaiting_dob_confirm = False
                    self._pending_dob_text = ""
                    turn_ctx.add_message(
                        role="system",
                        content="[VERIFICATION] Patient said the date was incorrect. "
                            "Apologise and ask them to provide their date of birth again.",
                    )
                else:
                    turn_ctx.add_message(
                        role="system",
                        content="[VERIFICATION] Unclear response. Ask the patient: "
                            "'Sorry — just to confirm, is that date correct? Yes or no?'",
                    )

            # ── DOB: patient has just spoken their date of birth ───────────────
            elif not self._identity_state.dob_confirmed and not self._identity_state.dob_failed:
                has_date = (
                    any(c.isdigit() for c in text) or
                    any(m in text.lower() for m in (
                        "jan", "feb", "mar", "apr", "may", "jun",
                        "jul", "aug", "sep", "oct", "nov", "dec",
                    ))
                )
                if has_date:
                    candidate = self._extract_dob_digits(text)
                    logger.info(
                        "DOB spoken — raw=%r extracted=%r call_id=%s",
                        text, candidate, self._call_id,
                    )
                    if candidate:
                        # Store extracted digits now — no re-parsing needed at confirm
                        self._pending_dob_text = candidate
                        self._identity_state.awaiting_dob_confirm = True
                        turn_ctx.add_message(
                            role="system",
                            content="[VERIFICATION] The patient just gave their date of birth. "
                                "Repeat it back clearly: 'So your date of birth is [day] [month] [year] — is that right?' "
                                "Use the full month name and 4-digit year. Wait for their yes or no.",
                        )
                    else:
                        turn_ctx.add_message(
                            role="system",
                            content="[VERIFICATION] Could not parse the date. "
                                "Ask the patient to repeat their date of birth clearly, "
                                "for example: 'Could you say that again — day, month, and year?'",
                        )

        # ── Real-time triage ──────────────────────────────────────────────────
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
            turn_ctx.add_message(role="system", content=RED_FLAG_SYSTEM_INSTRUCTION)

        if level == TriageLevel.AMBER and self._triage_level == TriageLevel.GREEN:
            self._triage_level = TriageLevel.AMBER
            self._triage_reasons.extend(reasons)
            logger.info(
                "AMBER flag — call_id=%s reasons=%s",
                self._call_id,
                reasons,
            )


    async def _close_after_delay(self, delay: float = 5.0) -> None:
        await asyncio.sleep(delay)
        # Delete the room via the LiveKit API — this terminates the SIP leg
        # (hanging up the patient's phone) and then closes the agent session.
        try:
            async with lk_api.LiveKitAPI(
                url=settings.livekit_url,
                api_key=settings.livekit_api_key,
                api_secret=settings.livekit_api_secret,
            ) as lk_client:
                await lk_client.room.delete_room(
                    lk_api.DeleteRoomRequest(room=self._room_name)
                )
            logger.info("Room deleted — SIP call terminated — room=%s", self._room_name)
        except Exception as exc:
            logger.warning("Room deletion failed (%s) — falling back to session close", exc)
        try:
            await self.session.aclose()
        except Exception:
            pass
