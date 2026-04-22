from __future__ import annotations

"""
Sizor NHS Inbound Voice Agent
─────────────────────────────
Handles patient-initiated calls into the NHS contact line.

Stack  : LiveKit Agent + AgentSession (livekit-agents 1.x), Deepgram Nova-3,
         Cartesia Sonic-3, Groq openai/gpt-oss-120b (OpenAI-compat endpoint),
         Silero VAD (min_silence_duration=0.9), Twilio SIP.

Tools are defined as @llm.function_tool methods on the agent class — the
livekit-agents 1.x equivalent of the old FunctionContext/@ai_callable pattern.
find_function_tools(self) in Agent.__init__ auto-discovers them.

Flow
  1. Patient calls  → agent greets immediately
  2. Collect name   → collect NHS number  → verify_patient()
  3. On success     → inject enriched system prompt via update_instructions()
  4. On 2nd failure → "I'm sorry I couldn't verify your details,
                       please contact your GP directly" → end call
  5. "How can I help you today?" → chief complaint → ≤3 clarifying questions
  6. Red-flag monitor throughout → escalate_patient() → end call
  7. When enough info → generate_soap_note()  [Claude Sonnet, NOT read aloud]
  8. Close warmly → save_call_record() → clinician notification
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Annotated, Optional

import httpx
from livekit import api as lk_api
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents import llm, stt, tts
from livekit.agents.llm import ChatContext, ChatMessage, function_tool  # ChatMessage used in on_user/agent_turn_completed signatures
from livekit.plugins import cartesia, deepgram, silero
from livekit.plugins import openai as lk_openai

from agent.triage import RED_FLAG_SYSTEM_INSTRUCTION, TriageLevel, classify_turn
from config.settings import settings
from sizor_ai.client import get_patient_call_context

logger = logging.getLogger(__name__)


_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ── Base system prompt (active before identity is verified) ───────────────────

_BASE_SYSTEM_PROMPT = """\
You are Sarah, an NHS patient services receptionist. A patient has phoned in \
and you have answered. You are NOT making an outbound call — the patient called YOU.

1. Listen to why they are calling.
2. Ask for their full name and NHS number to verify their identity. \
   When they give their NHS number, read it back digit by digit to confirm, \
   then call verify_patient() with both values.
3. After verification, acknowledge them by first name, then ask focused \
   clarifying questions about their concern — one at a time (how long, severity \
   1–10, better or worse, anything tried).
4. Once you have enough detail, call generate_soap_note().
5. Close warmly: "I've logged that for your care team and they'll be in touch. \
   Is there anything else?" then call save_call_record() and say goodbye.

VERIFICATION FAILURE:
- If NHS number fails: say warmly "No problem at all — could I take your date of birth \
  instead to verify your identity?" then call verify_patient_dob() with their DOB.
- If DOB also fails: apologise warmly and let them know you cannot verify today. \
  Ask them to contact their GP directly. Continue the call to help them as best you can.

RED FLAGS — if the patient mentions chest pain, difficulty breathing, stroke \
signs, coughing blood, sudden severe headache, loss of consciousness, or sepsis \
signs, call escalate_patient() to alert the care team, then respond with warmth \
and empathy — for example: "Oh I'm really sorry to hear that, that must be really \
hard for you." Gently let them know: "I just want to make sure you know — if things \
feel like they're getting worse, please don't hesitate to ring NHS 111 or 999, \
they're always there to help." Then continue asking your remaining questions as normal. \
NEVER say "that sounds concerning", "that's worrying", or anything that might frighten them.

You are on a phone call. Keep every response short and natural — one or two \
sentences at a time. Never diagnose. Never give medical advice.\
"""


# ── Enriched prompt injected after successful verification ────────────────────

def _recovery_phase_guidance(day: int | None) -> str:
    """Return a short clinical focus note based on days post-discharge."""
    if day is None:
        return ""
    if day <= 3:
        return (
            f"\nRECOVERY PHASE: Day {day} — EARLY (0–3 days). "
            "Priority areas: acute pain, wound/site status, fever/infection signs, "
            "medication initiation, basic mobility. Patients at highest risk of "
            "immediate post-discharge complications."
        )
    elif day <= 14:
        return (
            f"\nRECOVERY PHASE: Day {day} — MID (4–14 days). "
            "Priority areas: wound healing progression, mobility improvement, "
            "appetite/nutrition, mood (watch for post-operative depression), "
            "medication adherence, signs of delayed complications."
        )
    else:
        return (
            f"\nRECOVERY PHASE: Day {day} — LATE/ONGOING (14+ days). "
            "Priority areas: functional recovery, return to activities, "
            "persistent symptoms, readiness for follow-up appointments."
        )


def _build_enriched_prompt(
    patient_name: str,
    patient: dict,
    summaries: list[dict],
    call_context: dict | None = None,
) -> str:
    first = patient_name.split()[0] if patient_name else "the patient"
    day_in_recovery = patient.get("day_in_recovery")

    lines = [
        f"Patient {patient.get('full_name', patient_name)} has been VERIFIED.",
        f"NHS number   : {patient.get('nhs_number', '')}",
        f"Condition    : {patient.get('condition', 'not recorded')}",
    ]
    if patient.get("procedure"):
        lines.append(f"Procedure    : {patient['procedure']}")
    if patient.get("discharge_date"):
        discharge_str = patient["discharge_date"]
        if day_in_recovery is not None:
            discharge_str += f"  (Day {day_in_recovery} post-discharge today)"
        lines.append(f"Discharge    : {discharge_str}")
    if patient.get("primary_diagnosis"):
        lines.append(f"Diagnosis    : {patient['primary_diagnosis']}")
    meds = patient.get("current_medications") or []
    if meds:
        lines.append(f"Medications  : {', '.join(meds)}")
    allergies = patient.get("allergies") or []
    if allergies:
        lines.append(f"Allergies    : {', '.join(allergies)}")

    summary_block = ""
    if summaries:
        parts = []
        for i, s in enumerate(summaries[:3], 1):
            date = (s.get("generated_at") or "")[:10]
            assessment = (s.get("assessment") or "").strip()
            parts.append(f"  Call {i} ({date}): {assessment}")
        summary_block = "\nLast 3 call summaries (for comparison):\n" + "\n".join(parts)

    day_str = str(day_in_recovery) if day_in_recovery is not None else "unknown"
    patient_ctx = "\n".join(lines) + _recovery_phase_guidance(day_in_recovery) + summary_block

    # Previous call context block (open flags, scores, active concerns)
    context_block = ""
    if call_context:
        ctx_lines = ["\n── PREVIOUS CALL HISTORY ───────────────────────────────────────────────────"]

        for i, s in enumerate(call_context.get("call_summaries", [])[:3], 1):
            day_label = f"Day {s['day']}" if s.get("day") is not None else f"Call {i}"
            ctx_lines.append(f"\n[{day_label}]")
            if s.get("what_patient_reported"):
                ctx_lines.append(f"  Patient reported: {s['what_patient_reported']}")
            if s.get("assessment"):
                ctx_lines.append(f"  Assessment: {s['assessment']}")
            scores = s.get("scores", {})
            score_parts = []
            if "pain" in scores:
                score_parts.append(f"pain={scores['pain']}/10")
            if "mood" in scores:
                score_parts.append(f"mood={scores['mood']}/10")
            if "medication_adherent" in scores:
                score_parts.append(f"medication={'adherent' if scores['medication_adherent'] else 'NON-ADHERENT'}")
            if score_parts:
                ctx_lines.append(f"  Scores: {', '.join(score_parts)}")
            if scores.get("concerns_noted"):
                ctx_lines.append(f"  Concerns: {scores['concerns_noted']}")

        open_flags = call_context.get("open_flags", [])
        if open_flags:
            ctx_lines.append("\nOPEN FLAGS (must follow up):")
            for f in open_flags:
                ctx_lines.append(f"  ⚠ [{f['severity'].upper()}] {f['type'].replace('_', ' ')}: {f['description']}")

        active_concerns = call_context.get("active_concerns", [])
        if active_concerns:
            ctx_lines.append("\nACTIVE CONCERNS:")
            for c in active_concerns:
                ctx_lines.append(f"  • {c}")

        ctx_lines.append("""
CONTINUITY INSTRUCTIONS:
- If the patient's reason for calling relates to any concern above, acknowledge it and probe further.
- If an open flag exists, ask specifically about that symptom: "Last time you mentioned X, how has that been?"
- Frame naturally — do not read clinical notes aloud or make the patient feel interrogated.
────────────────────────────────────────────────────────────────────────────""")
        context_block = "\n".join(ctx_lines)

    return f"""\
{_BASE_SYSTEM_PROMPT}

── PATIENT RECORD (loaded post-verification) ───────────────────────────────
{patient_ctx}{context_block}
────────────────────────────────────────────────────────────────────────────

The patient is now verified. Address them as {first}.
Say "Thank you {first}, I've got your records here." then return to their original concern.

IMPORTANT — use the patient record above to make this feel like a real clinical call:
- If you know their day in recovery, acknowledge it naturally, e.g. "You're on Day {day_str} since your discharge — how have things been going?" or reference it when asking about symptoms.
- Frame questions around their specific condition/procedure, not generic questions.
- If there are open flags or previous call concerns, ask about those specifically: "Last time there was a concern about X — how has that been?"
- Keep every response to 1–2 sentences. Never read clinical notes aloud.\
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  Inbound Agent — tools defined as @function_tool methods (livekit-agents 1.x)
# ═══════════════════════════════════════════════════════════════════════════════

class SizorInboundAgent(Agent):
    """
    NHS inbound call handler.

    Lifecycle:
      on_enter()               — read room attrs, greet immediately
      on_user_turn_completed() — real-time red-flag triage on every utterance
      on_agent_turn_completed()— record agent turns for the transcript
      on_exit()                — ensure call record is saved

    Tools (auto-discovered by find_function_tools in Agent.__init__):
      verify_patient     — fuzzy name + exact NHS number match
      escalate_patient   — raise RED flag, alert care team
      generate_soap_note — Claude Sonnet structured SOAP (not read aloud)
      save_call_record   — persist to DB, trigger Celery pipeline
    """

    def __init__(self) -> None:
        super().__init__(instructions=_BASE_SYSTEM_PROMPT)

        self._call_id: str = str(uuid.uuid4())
        self._patient_name: str = "Patient"
        self._nhs_number: str = ""
        self._patient_id: str = ""
        self._phone_number: str = ""
        self._room_name: str = ""

        self._started_at: float = time.time()
        self._conversation_turns: list[tuple[str, str]] = []
        self._turn_end_time: float = 0.0

        self._patient_verified: bool = False
        self._verification_attempts: int = 0
        self._verification_failed: bool = False

        self._triage_level: TriageLevel = TriageLevel.GREEN
        self._triage_reasons: list[str] = []
        self._red_flag_triggered: bool = False

        self._soap_generated: bool = False
        self._call_saved: bool = False

    # ── Transcript helpers ─────────────────────────────────────────────────────

    def _build_transcript(self) -> str:
        """
        Build the full conversation transcript from the live chat context.
        This is more reliable than on_agent_turn_completed because it captures:
          - session.say() calls (greeting, escalations) added manually to chat_ctx
          - LLM-generated responses
          - All user turns
        Falls back to _conversation_turns if chat_ctx is unavailable or empty.
        """
        lines = []
        try:
            for msg in self.session.history.messages:
                # ChatRole may be a str enum or a plain enum — normalise to str
                role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                if role not in ("assistant", "user"):
                    continue
                if hasattr(msg, "text_content") and msg.text_content:
                    text = msg.text_content
                else:
                    content = msg.content
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = " ".join(
                            p if isinstance(p, str) else getattr(p, "text", str(p))
                            for p in content
                            if p
                        )
                    else:
                        text = ""
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

    # ── HTTP helpers ───────────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "X-Internal-Key": settings.sizor_internal_key,
            "Content-Type": "application/json",
        }

    def _api(self, path: str) -> str:
        return f"{settings.sizor_api_url}{path}"

    # ── Tool 1: verify_patient ─────────────────────────────────────────────────

    @function_tool(
        description=(
            "Verify the caller's identity against the NHS patients database using "
            "fuzzy name matching and exact NHS number matching. "
            "Call this after collecting the patient's full name AND NHS number."
        )
    )
    async def verify_patient(
        self,
        full_name: Annotated[str, "Patient's full name exactly as they stated it"],
        nhs_number: Annotated[str, "Patient's NHS number as digits only — convert any spoken numbers (e.g. 'one six five') to digits, strip all spaces and dashes"],
    ) -> str:
        self._verification_attempts += 1
        nhs_clean = nhs_number.replace(" ", "").replace("-", "")

        if not settings.sizor_api_url or not settings.sizor_internal_key:
            logger.warning("Sizor not configured — verify_patient returning mock success")
            self._patient_verified = True
            self._patient_name = full_name
            self._nhs_number = nhs_clean
            return json.dumps({"verified": True, "patient_name": full_name})

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._api("/api/patients/verify-inbound"),
                    json={"full_name": full_name, "nhs_number": nhs_clean},
                    headers=self._headers(),
                )
                data = resp.json()
                logger.info(
                    "verify_patient response — status=%d verified=%s nhs_sent=%r name_sent=%r",
                    resp.status_code, data.get("verified"), nhs_clean, full_name,
                )
        except Exception as exc:
            logger.error("verify_patient HTTP error: %s", exc)
            return json.dumps({
                "verified": False,
                "reason": "Service temporarily unavailable — please try again shortly.",
            })

        if data.get("verified"):
            patient = data.get("patient", {})
            summaries = data.get("recent_summaries", [])

            self._patient_verified = True
            self._patient_name = patient.get("full_name", full_name)
            self._nhs_number = nhs_clean
            self._patient_id = patient.get("patient_id", "")

            # Fetch previous call context for conversation continuity
            call_context = None
            try:
                call_context = await get_patient_call_context(nhs_clean)
                if call_context:
                    logger.info(
                        "Inbound call context loaded — %d summaries, %d flags — call_id=%s",
                        len(call_context.get("call_summaries", [])),
                        len(call_context.get("open_flags", [])),
                        self._call_id,
                    )
            except Exception as exc:
                logger.warning("Could not fetch inbound call context: %s", exc)

            # Inject enriched system prompt mid-call
            enriched = _build_enriched_prompt(self._patient_name, patient, summaries, call_context)
            try:
                await self.update_instructions(enriched)
                logger.info(
                    "System prompt enriched post-verification — call_id=%s patient=%s",
                    self._call_id, self._patient_name,
                )
            except Exception as exc:
                logger.error("update_instructions failed: %s", exc)

            return json.dumps({
                "verified": True,
                "patient_name": self._patient_name,
                "condition": patient.get("condition"),
            })

        reason = data.get("reason", "Details could not be verified.")
        logger.warning(
            "verify_patient failed (attempt %d) — call_id=%s",
            self._verification_attempts, self._call_id,
        )
        if self._verification_attempts >= 3:
            self._verification_failed = True
        return json.dumps({"verified": False, "reason": reason})

    # ── Tool 1b: verify_patient_dob (fallback) ────────────────────────────────

    @function_tool(
        description=(
            "Fallback identity verification using date of birth. "
            "Call this ONLY when verify_patient() has already failed for the NHS number. "
            "Pass the patient's name and date of birth as they stated it."
        )
    )
    async def verify_patient_dob(
        self,
        full_name: Annotated[str, "Patient's full name as they stated it"],
        date_of_birth: Annotated[str, "Patient's date of birth — convert spoken dates to YYYY-MM-DD format, e.g. 'fifteenth of March nineteen eighty-two' → '1982-03-15'"],
    ) -> str:
        nhs_clean = self._nhs_number  # use what we already collected

        if not settings.sizor_api_url or not settings.sizor_internal_key:
            logger.warning("Sizor not configured — verify_patient_dob returning mock success")
            self._patient_verified = True
            return json.dumps({"verified": True, "patient_name": full_name})

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._api("/api/patients/verify-dob"),
                    json={
                        "nhs_number": nhs_clean,
                        "full_name": full_name,
                        "date_of_birth": date_of_birth,
                    },
                    headers=self._headers(),
                )
                data = resp.json()
                logger.info(
                    "verify_patient_dob response — status=%d verified=%s",
                    resp.status_code, data.get("verified"),
                )
        except Exception as exc:
            logger.error("verify_patient_dob HTTP error: %s", exc)
            return json.dumps({"verified": False, "reason": "Service temporarily unavailable."})

        if data.get("verified"):
            patient = data.get("patient", {})
            summaries = data.get("recent_summaries", [])

            self._patient_verified = True
            self._patient_name = patient.get("full_name", full_name)
            self._patient_id = patient.get("patient_id", "")

            call_context = None
            try:
                call_context = await get_patient_call_context(patient.get("nhs_number", nhs_clean))
            except Exception as exc:
                logger.warning("Could not fetch inbound call context: %s", exc)

            enriched = _build_enriched_prompt(self._patient_name, patient, summaries, call_context)
            try:
                await self.update_instructions(enriched)
                logger.info(
                    "System prompt enriched post-DOB-verification — call_id=%s patient=%s",
                    self._call_id, self._patient_name,
                )
            except Exception as exc:
                logger.error("update_instructions failed: %s", exc)

            return json.dumps({
                "verified": True,
                "patient_name": self._patient_name,
                "condition": patient.get("condition"),
            })

        return json.dumps({"verified": False, "reason": data.get("reason", "Date of birth could not be verified.")})

    # ── Tool 2: escalate_patient ───────────────────────────────────────────────

    @function_tool(
        description=(
            "Escalate the patient to urgent care. Call this IMMEDIATELY when the patient "
            "mentions chest pain, difficulty breathing, stroke signs, coughing blood, "
            "severe sudden headache, altered consciousness, or sepsis signs. "
            "Notifies the care team and prepares for call end."
        )
    )
    async def escalate_patient(
        self,
        reason: Annotated[str, "Brief description of the red-flag symptom(s) the patient described"],
    ) -> str:
        self._red_flag_triggered = True
        self._triage_level = TriageLevel.RED
        self._triage_reasons.append(reason)

        logger.warning("escalate_patient called — call_id=%s reason=%s", self._call_id, reason)

        if not settings.sizor_api_url or not settings.sizor_internal_key:
            return json.dumps({"escalated": True})

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._api("/api/escalations/inbound"),
                    json={
                        "call_id": self._call_id,
                        "patient_id": self._patient_id or None,
                        "nhs_number": self._nhs_number,
                        "patient_name": self._patient_name,
                        "reason": reason,
                        "triage_level": "red",
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                logger.info("Escalation recorded — call_id=%s", self._call_id)
        except Exception as exc:
            logger.error("escalate_patient HTTP error: %s", exc)

        return json.dumps({
            "escalated": True,
            "message": "Care team alerted. Patient instructed to call 999 / attend A&E.",
        })

    # ── Tool 3: generate_soap_note ─────────────────────────────────────────────

    @function_tool(
        description=(
            "Generate a structured clinical SOAP note from the conversation using Claude Sonnet. "
            "Call this when you have gathered the chief complaint plus at least two clarifying "
            "answers. The SOAP note is stored in the patient record — never read it to the patient."
        )
    )
    async def generate_soap_note(
        self,
        note: Annotated[str, "Pass an empty string"] = "",
    ) -> str:
        transcript = self._build_transcript()

        if not settings.sizor_api_url or not settings.sizor_internal_key:
            logger.warning("Sizor not configured — generate_soap_note skipped")
            self._soap_generated = True
            return json.dumps({"generated": False, "reason": "Sizor not configured"})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._api("/api/soap/generate-async"),
                    json={
                        "call_id": self._call_id,
                        "patient_id": self._patient_id or None,
                        "nhs_number": self._nhs_number,
                        "patient_name": self._patient_name,
                        "transcript": transcript,
                        "direction": "inbound",
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                result = resp.json()
                self._soap_generated = True
                logger.info(
                    "SOAP note generated — call_id=%s soap_id=%s",
                    self._call_id, result.get("soap_id"),
                )
                return json.dumps({"generated": True, "soap_id": result.get("soap_id")})
        except Exception as exc:
            logger.error("generate_soap_note HTTP error: %s", exc)
            return json.dumps({"generated": False, "error": str(exc)})

    # ── Tool 4: save_call_record ───────────────────────────────────────────────

    @function_tool(
        description=(
            "Save the completed call record to the database and notify the patient's "
            "care team. Call this at the very end of the call, after saying goodbye."
        )
    )
    async def save_call_record(
        self,
        note: Annotated[str, "Pass an empty string"] = "",
    ) -> str:
        if self._call_saved:
            return json.dumps({"saved": True, "note": "already saved"})

        ended_at = time.time()
        duration = ended_at - self._started_at
        transcript = self._build_transcript()

        if not settings.sizor_api_url or not settings.sizor_internal_key:
            logger.warning("Sizor not configured — save_call_record skipped")
            self._call_saved = True
            return json.dumps({"saved": False, "reason": "Sizor not configured"})

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._api("/api/calls/save-inbound"),
                    json={
                        "call_id": self._call_id,
                        "patient_id": self._patient_id or None,
                        "nhs_number": self._nhs_number,
                        "patient_name": self._patient_name,
                        "transcript": transcript,
                        "duration_seconds": int(duration),
                        "triage_level": self._triage_level.value,
                        "triage_reasons": self._triage_reasons,
                        "direction": "inbound",
                        "trigger_type": "inbound_patient",
                        "identity_verified": self._patient_verified,
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                result = resp.json()
                self._call_saved = True
                logger.info("Call record saved — call_id=%s", self._call_id)
        except Exception as exc:
            logger.error("save_call_record HTTP error: %s", exc)
            asyncio.create_task(self._close_after_delay())
            return json.dumps({"saved": False, "error": str(exc)})

        # Give TTS time to finish speaking the goodbye before hanging up
        asyncio.create_task(self._close_after_delay())
        return json.dumps({"saved": True, "call_id": result.get("call_id")})

    async def _close_after_delay(self, delay: float = 4.0) -> None:
        """Wait for TTS to finish speaking then hang up."""
        await asyncio.sleep(delay)
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

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def on_enter(self) -> None:
        """Read room attributes then greet immediately."""
        # Register agent-turn capture — on_agent_turn_completed does not exist
        # in livekit-agents 1.5+; use the conversation_item_added session event.
        def _on_conversation_item(event) -> None:
            try:
                msg = event.item
                if getattr(msg, "role", None) != "assistant":
                    return
                text = (msg.text_content or "").strip()
                if not text:
                    return
                if self._turn_end_time:
                    logger.info("LATENCY user→agent: %.3fs", time.time() - self._turn_end_time)
                    self._turn_end_time = 0.0
                self._conversation_turns.append(("agent", text))
                lower = text.lower()
                if any(w in lower for w in ("goodbye", "take care", "bye", "farewell")):
                    logger.info("Goodbye detected — closing session in 5s — call_id=%s", self._call_id)
                    asyncio.create_task(self._close_after_delay(5.0))
            except Exception:
                pass
        self.session.on("conversation_item_added", _on_conversation_item)

        try:
            session = self.session
            remote_participants = session.room_io.room.remote_participants
            attrs: dict = {}
            if remote_participants:
                first = next(iter(remote_participants.values()))
                attrs = dict(first.attributes) if first.attributes else {}

            self._call_id = attrs.get("call_id", self._call_id)
            self._phone_number = attrs.get("phone_number", "")
            self._room_name = attrs.get("room_name", session.room_io.room.name)
        except Exception as exc:
            logger.warning("Could not read participant attributes: %s", exc)

        logger.info("SizorInboundAgent entering — call_id=%s", self._call_id)

        await asyncio.sleep(1)

        greeting = (
            "Thank you for calling NHS Patient Services, this is Sarah. "
            "How may I help you today?"
        )
        try:
            await self.session.say(greeting, allow_interruptions=True)
        except Exception as exc:
            logger.error("Greeting failed: %s", exc, exc_info=True)

    async def on_exit(self) -> None:
        """Safety net — always save the call record and SOAP note on exit."""
        ended_at = time.time()
        duration = ended_at - self._started_at
        logger.info(
            "SizorInboundAgent exiting — call_id=%s duration=%.1fs triage=%s saved=%s soap=%s",
            self._call_id, duration, self._triage_level, self._call_saved, self._soap_generated,
        )
        if not self._soap_generated and self._conversation_turns:
            asyncio.create_task(self.generate_soap_note())
        if not self._call_saved:
            asyncio.create_task(self.save_call_record())

    # ── Conversation hooks ─────────────────────────────────────────────────────

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        """Real-time red-flag triage on every patient utterance."""
        self._turn_end_time = time.time()
        if hasattr(new_message, "text_content") and new_message.text_content:
            text = new_message.text_content
        else:
            content = new_message.content
            if isinstance(content, list):
                text = " ".join(
                    p if isinstance(p, str) else getattr(p, "text", str(p))
                    for p in content
                    if p
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
                "RED flag detected — call_id=%s reasons=%s", self._call_id, reasons
            )
            asyncio.create_task(self.escalate_patient(reason="; ".join(reasons)))
            turn_ctx.add_message(role="system", content=RED_FLAG_SYSTEM_INSTRUCTION)

        if level == TriageLevel.AMBER and self._triage_level == TriageLevel.GREEN:
            self._triage_level = TriageLevel.AMBER
            self._triage_reasons.extend(reasons)
            logger.info("AMBER flag — call_id=%s reasons=%s", self._call_id, reasons)




# ═══════════════════════════════════════════════════════════════════════════════
#  Worker entrypoint   python -m agent.sizor_inbound_agent start
# ═══════════════════════════════════════════════════════════════════════════════

# SizorInboundAgent is imported and used by agent/worker.py — not run standalone.
