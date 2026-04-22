"""
Patient Chat API — conversational AI with full patient context.

Model priority:
  1. gpt-4o        (OpenAI)   — if OPENAI_API_KEY is set
  2. groq/meta-llama/llama-4-scout-17b-16e-instruct  — if GROQ_API_KEY is set
  3. Falls back to LLM_MODEL in .env

Override per-request by passing { "model": "..." } in the request body.
"""
import json
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import litellm
import os

from ..database import get_db
from ..models import (
    Patient, PatientMedicalProfile, LongitudinalSummary,
    CallRecord, ClinicalExtraction, SOAPNote, UrgencyFlag, ProbeCall, CallSchedule,
)
from .auth import get_current_clinician
from ..config import settings

router = APIRouter(tags=["chat"])

MODELS = {
    "gpt-4o":   {"requires": "openai_api_key",  "label": "GPT-4o"},
    "groq/meta-llama/llama-4-scout-17b-16e-instruct": {"requires": "groq_api_key", "label": "Llama 4"},
    "groq/llama-3.3-70b-versatile": {"requires": "groq_api_key", "label": "Llama 3.3"},
    "claude-opus-4-6": {"requires": "anthropic_api_key", "label": "Claude Opus"},
}

SCHEDULE_TOOL = {
    "type": "function",
    "function": {
        "name": "schedule_call",
        "description": "Schedule a follow-up monitoring call for this patient at a specific date and time.",
        "parameters": {
            "type": "object",
            "properties": {
                "scheduled_for": {
                    "type": "string",
                    "description": "Call datetime in ISO 8601 format, e.g. '2026-04-15T10:00:00'. Resolve relative dates like 'tomorrow' or 'next Monday' using today's date from the system context.",
                },
                "module": {
                    "type": "string",
                    "description": "Short label for the call, e.g. 'Routine Check', 'Pain Assessment', 'Wound Review', 'Follow-up'.",
                },
                "call_type": {
                    "type": "string",
                    "enum": ["routine", "urgent", "follow-up"],
                    "description": "Call urgency type.",
                },
            },
            "required": ["scheduled_for", "module", "call_type"],
        },
    },
}


def _pick_model(requested: str | None) -> str:
    """Return the best available model."""
    if requested and requested in MODELS:
        req = MODELS[requested]["requires"]
        if getattr(settings, req, ""):
            return requested

    # priority order — OpenAI first, then Groq, then Anthropic
    if settings.openai_api_key:
        return "gpt-4o"
    if settings.groq_api_key:
        return "groq/llama-3.3-70b-versatile"
    if settings.anthropic_api_key:
        return "claude-opus-4-6"
    return settings.llm_model


def _fallback_model(primary: str) -> str | None:
    """Return a fallback model different from the primary."""
    if primary != "groq/llama-3.3-70b-versatile" and settings.groq_api_key:
        return "groq/llama-3.3-70b-versatile"
    if primary != "gpt-4o" and settings.openai_api_key:
        return "gpt-4o"
    if primary != "claude-opus-4-6" and settings.anthropic_api_key:
        return "claude-opus-4-6"
    return None


def _set_env():
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    if settings.groq_api_key:
        os.environ["GROQ_API_KEY"] = settings.groq_api_key


async def _build_context(patient_id: str, db: AsyncSession) -> str:
    """Build a rich system prompt from all available patient data."""
    pid = uuid.UUID(patient_id)

    p = (await db.execute(select(Patient).where(Patient.patient_id == pid))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Patient not found")

    profile = (await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == pid)
    )).scalar_one_or_none()

    summary = (await db.execute(
        select(LongitudinalSummary)
        .where(LongitudinalSummary.patient_id == pid, LongitudinalSummary.is_current == True)
        .order_by(LongitudinalSummary.version_number.desc())
        .limit(1)
    )).scalar_one_or_none()

    calls_res = await db.execute(
        select(CallRecord).where(CallRecord.patient_id == pid).order_by(CallRecord.started_at.desc()).limit(5)
    )
    calls = calls_res.scalars().all()

    flags_res = await db.execute(
        select(UrgencyFlag)
        .where(UrgencyFlag.patient_id == pid, UrgencyFlag.status.in_(["open", "reviewing"]))
    )
    open_flags = flags_res.scalars().all()

    age = None
    if p.date_of_birth:
        today = date.today()
        dob = p.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    today_str = date.today().strftime("%A, %d %B %Y")
    lines = [
        "You are Sizor AI, a clinical assistant embedded in a post-discharge monitoring platform.",
        "You are in a live chat with an NHS clinician reviewing this patient.",
        f"Today's date is {today_str}. Use this to resolve relative dates like 'tomorrow' or 'next Monday'.",
        "Keep every reply SHORT — 2 to 4 sentences max. Be direct and conversational, like a knowledgeable colleague.",
        "Use plain English. Reference specific data points. Do not invent data.",
        "If the clinician asks a follow-up, build on the conversation naturally.",
        "Only recommend escalation when genuinely warranted.",
        "",
        "═══ PATIENT RECORD ═══",
        f"Name: {p.full_name}",
        f"Age: {age if age else 'unknown'}",
        f"NHS Number: {p.nhs_number}",
        f"Condition: {p.condition}",
        f"Procedure: {p.procedure or 'N/A'}",
        f"Discharge date: {p.discharge_date or 'unknown'}",
        f"Program: {p.program_module or 'N/A'}",
        f"Status: {p.status}",
        f"Phone: {p.phone_number}",
    ]

    if profile:
        lines += [
            "",
            "── Medical Profile ──",
            f"Primary diagnosis: {profile.primary_diagnosis}",
            f"Secondary diagnoses: {', '.join(profile.secondary_diagnoses or [])}",
            f"Allergies: {', '.join(profile.allergies or []) or 'None known'}",
            f"Medications: {', '.join(profile.current_medications or [])}",
            f"Comorbidities: {', '.join(profile.relevant_comorbidities or [])}",
        ]
        if profile.consultant_notes:
            lines.append(f"Consultant notes: {profile.consultant_notes}")
        if profile.discharge_summary_text:
            lines.append(f"Discharge summary: {profile.discharge_summary_text}")

    if summary:
        lines += [
            "",
            "── Longitudinal Summary (AI-generated, current) ──",
            summary.narrative_text,
            f"Active concerns: {', '.join(summary.active_concerns_snapshot or []) or 'None'}",
            f"Trend snapshot: {json.dumps(summary.trend_snapshot or {})}",
        ]

    if open_flags:
        lines += ["", "── Open Urgency Flags ──"]
        for f in open_flags:
            lines.append(f"  [{f.severity.upper()}] {f.flag_type}: {f.trigger_description}")

    if calls:
        lines += ["", "── Recent Calls (latest first) ──"]
        for c in calls:
            lines.append(f"  Day {c.day_in_recovery} ({c.direction}, {c.trigger_type}) — {c.started_at.strftime('%d %b %Y')}")

    # Latest call scores
    if calls:
        latest = calls[0]
        ext = (await db.execute(
            select(ClinicalExtraction).where(ClinicalExtraction.call_id == latest.call_id)
        )).scalar_one_or_none()
        soap = (await db.execute(
            select(SOAPNote).where(SOAPNote.call_id == latest.call_id)
        )).scalar_one_or_none()

        if ext:
            def _score(v):
                return f"{v}/10" if v is not None else "not recorded"
            def _bool(v):
                return ("yes" if v else "no") if v is not None else "not recorded"
            lines += [
                "",
                f"── Latest Clinical Scores (Day {latest.day_in_recovery}) ──",
                f"  Pain: {_score(ext.pain_score)}",
                f"  Breathlessness: {_score(ext.breathlessness_score)}",
                f"  Mobility: {_score(ext.mobility_score)}",
                f"  Appetite: {_score(ext.appetite_score)}",
                f"  Mood: {_score(ext.mood_score)}",
                f"  Medication adherent: {_bool(ext.medication_adherence)}",
            ]
            if ext.condition_specific_flags:
                lines.append(f"  Condition flags: {json.dumps(ext.condition_specific_flags)}")

        if soap:
            lines += [
                "",
                f"── Latest SOAP Note (Day {latest.day_in_recovery}) ──",
                f"  S: {soap.subjective}",
                f"  O: {soap.objective}",
                f"  A: {soap.assessment}",
                f"  P: {soap.plan}",
            ]

    # Probe calls — clinician-initiated targeted checks
    probe_calls_res = await db.execute(
        select(ProbeCall)
        .where(ProbeCall.patient_id == pid)
        .order_by(ProbeCall.created_at.desc())
        .limit(5)
    )
    probe_calls = probe_calls_res.scalars().all()

    if probe_calls:
        lines += ["", "── Probe Calls (clinician-initiated, latest first) ──"]
        for pc in probe_calls:
            when = pc.scheduled_time.strftime("%d %b %Y %H:%M")
            lines.append(f"  [{pc.status.upper()}] {when} — Clinician note: {pc.note}")
            if pc.call_prompt and pc.prompt_source == "llm":
                lines.append(f"    AI call prompt: {pc.call_prompt[:300]}{'…' if len(pc.call_prompt) > 300 else ''}")

            # Include SOAP note from the probe call outcome if available
            probe_soap = None
            if pc.soap_note_id:
                probe_soap = (await db.execute(
                    select(SOAPNote).where(SOAPNote.soap_id == pc.soap_note_id)
                )).scalar_one_or_none()
            elif pc.call_sid:
                call_for_sid = (await db.execute(
                    select(CallRecord).where(CallRecord.call_sid == pc.call_sid)
                )).scalar_one_or_none()
                if call_for_sid:
                    probe_soap = (await db.execute(
                        select(SOAPNote).where(SOAPNote.call_id == call_for_sid.call_id)
                    )).scalar_one_or_none()

            if probe_soap:
                lines += [
                    f"    Probe SOAP outcome —",
                    f"      S: {probe_soap.subjective}",
                    f"      A: {probe_soap.assessment}",
                    f"      P: {probe_soap.plan}",
                ]

    return "\n".join(lines)


async def _build_ward_context(hospital_id: str, db: AsyncSession) -> str:
    """Build a system prompt summarising all wards for a hospital."""
    import uuid as _uuid
    try:
        hid = _uuid.UUID(hospital_id)
    except Exception:
        raise HTTPException(400, "Invalid hospital_id")

    patients_res = await db.execute(
        select(Patient).where(Patient.hospital_id == hid, Patient.status == "active")
    )
    patients = patients_res.scalars().all()

    if not patients:
        return (
            "You are Sizor AI, a clinical intelligence assistant for an NHS post-discharge monitoring platform. "
            "There are currently no active patients registered for this hospital. "
            "Answer general questions helpfully and concisely."
        )

    # Group by ward (condition)
    from collections import defaultdict
    ward_map = defaultdict(lambda: {"patients": [], "red": 0, "amber": 0, "green": 0, "flags": []})
    for p in patients:
        ward = p.condition or "General"
        ward_map[ward]["patients"].append(p)

    # Pull open flags for all patients
    pids = [p.patient_id for p in patients]
    flags_res = await db.execute(
        select(UrgencyFlag).where(
            UrgencyFlag.patient_id.in_(pids),
            UrgencyFlag.status.in_(["open", "reviewing"])
        )
    )
    open_flags = flags_res.scalars().all()
    flag_by_pid = defaultdict(list)
    for f in open_flags:
        flag_by_pid[f.patient_id].append(f)

    # Pull latest SOAP per patient (for assessment context)
    soap_res = await db.execute(
        select(SOAPNote).where(SOAPNote.patient_id.in_(pids))
        .order_by(SOAPNote.generated_at.desc())
    )
    all_soaps = soap_res.scalars().all()
    soap_by_pid = {}
    for s in all_soaps:
        if s.patient_id not in soap_by_pid:
            soap_by_pid[s.patient_id] = s

    # Assign RAG per patient
    for p in patients:
        flags = flag_by_pid.get(p.patient_id, [])
        has_red = any(f.severity == "red" for f in flags)
        has_amber = any(f.severity == "amber" for f in flags)
        ward = p.condition or "General"
        if has_red:
            ward_map[ward]["red"] += 1
        elif has_amber:
            ward_map[ward]["amber"] += 1
        else:
            ward_map[ward]["green"] += 1
        for f in flags:
            ward_map[ward]["flags"].append({"patient": p.full_name, "severity": f.severity, "type": f.flag_type, "detail": f.trigger_description})

    total_red   = sum(w["red"]   for w in ward_map.values())
    total_amber = sum(w["amber"] for w in ward_map.values())
    total_green = sum(w["green"] for w in ward_map.values())
    total       = len(patients)

    lines = [
        "You are Sizor AI, a clinical intelligence assistant embedded in an NHS post-discharge monitoring platform.",
        "You are chatting with a clinician on the Ward Overview dashboard.",
        "Keep replies SHORT — 2 to 5 sentences. Be direct and factual. Reference specific wards, patient counts, and flags where relevant.",
        "Do not invent data. If you don't know something specific, say so.",
        "",
        "═══ HOSPITAL-WIDE SUMMARY ═══",
        f"Total active patients: {total}",
        f"RED (immediate escalation): {total_red}",
        f"AMBER (close monitoring): {total_amber}",
        f"GREEN (on track): {total_green}",
        f"Active wards / pathways: {len(ward_map)}",
        f"Open urgency flags: {len(open_flags)}",
        "",
        "═══ WARD BREAKDOWN ═══",
    ]

    for ward_name, wd in sorted(ward_map.items()):
        n = len(wd["patients"])
        lines.append(f"\n── {ward_name} ({n} patients | R:{wd['red']} A:{wd['amber']} G:{wd['green']}) ──")
        for f in wd["flags"][:5]:
            lines.append(f"  [{f['severity'].upper()}] {f['patient']} — {f['type']}: {f['detail']}")
        # Include latest SOAP assessments for RED/AMBER patients in this ward
        critical = [p for p in wd["patients"] if flag_by_pid.get(p.patient_id)]
        for p in critical[:3]:
            soap = soap_by_pid.get(p.patient_id)
            if soap:
                lines.append(f"  Latest assessment for {p.full_name}: {soap.assessment}")

    return "\n".join(lines)


@router.post("/ward/chat")
async def ward_chat(
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Ward-level chat — context covers all active patients across the hospital."""
    _set_env()
    model = _pick_model(data.get("model"))
    messages_in = data.get("messages", [])
    if not messages_in:
        raise HTTPException(400, "messages required")

    system_prompt = await _build_ward_context(str(clinician.hospital_id), db)

    messages = [{"role": "system", "content": system_prompt}]
    for m in messages_in:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=400,
        )
        content = response.choices[0].message.content or ""
        return {"reply": content, "model": model}
    except Exception as exc:
        fallback = _fallback_model(model)
        if fallback:
            try:
                response = await litellm.acompletion(
                    model=fallback,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=400,
                )
                content = response.choices[0].message.content or ""
                return {"reply": content, "model": fallback}
            except Exception:
                pass
        raise HTTPException(500, f"LLM error: {str(exc)}")


@router.get("/patients/{patient_id}/chat/models")
async def list_models(
    clinician=Depends(get_current_clinician),
):
    """Return available models based on configured API keys."""
    available = []
    for model_id, cfg in MODELS.items():
        if getattr(settings, cfg["requires"], ""):
            available.append({"id": model_id, "label": cfg["label"]})
    return {"models": available, "default": _pick_model(None)}


@router.post("/patients/{patient_id}/chat")
async def chat(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Non-streaming chat endpoint with scheduling tool support.
    Body: { "messages": [{"role": "user"|"assistant", "content": "..."}], "model": "gpt-4o" }
    """
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    _set_env()
    model = _pick_model(data.get("model"))
    tz_offset_minutes = data.get("timezone_offset_minutes", 0)  # minutes ahead of UTC
    client_tz = _tz(offset=_td(minutes=int(tz_offset_minutes)))
    messages_in = data.get("messages", [])
    if not messages_in:
        raise HTTPException(400, "messages required")

    system_prompt = await _build_context(patient_id, db)

    # Only offer the scheduling tool when the clinician's message clearly asks for it
    SCHEDULE_KEYWORDS = {
        "schedule a", "schedule the", "schedule an",
        "book a call", "book an appointment", "book a follow", "book the call",
        "arrange a call", "arrange a follow",
        "set up a call", "set up an appointment",
        "add a call", "plan a call", "create a call",
        "follow-up call for", "follow up call for",
        "remind me to call",
    }
    last_user_msg = next(
        (m["content"].lower() for m in reversed(messages_in) if m.get("role") == "user"), ""
    )
    wants_schedule = any(kw in last_user_msg for kw in SCHEDULE_KEYWORDS)

    # Only inject scheduling instructions when the user actually wants to schedule
    if wants_schedule:
        system_prompt += (
            "\n\nThe clinician is asking you to schedule a call. "
            "Use the schedule_call function to do this — do not just suggest it, actually call the function."
        )

    messages = [{"role": "system", "content": system_prompt}]
    for m in messages_in:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})

    async def _call(mdl, use_tools=True):
        kwargs = dict(model=mdl, messages=messages, temperature=0.4, max_tokens=400)
        if use_tools and wants_schedule:
            kwargs["tools"] = [SCHEDULE_TOOL]
            kwargs["tool_choice"] = "auto"
        return await litellm.acompletion(**kwargs)

    async def _try_call(mdl):
        """Try with tools if scheduling intent detected, fall back to no-tools if unsupported."""
        try:
            return await _call(mdl, use_tools=wants_schedule)
        except Exception:
            return await _call(mdl, use_tools=False)

    try:
        response = await _try_call(model)
    except Exception as exc:
        fallback = _fallback_model(model)
        if fallback:
            try:
                response = await _try_call(fallback)
                model = fallback
            except Exception:
                raise HTTPException(500, f"LLM error: {str(exc)}")
        else:
            raise HTTPException(500, f"LLM error: {str(exc)}")

    choice = response.choices[0]

    # Handle tool call — schedule_call
    if choice.finish_reason == "tool_calls" and getattr(choice.message, "tool_calls", None):
        tool_call = choice.message.tool_calls[0]
        if tool_call.function.name == "schedule_call":
            try:
                args = json.loads(tool_call.function.arguments)
                scheduled_for_str = args.get("scheduled_for", "")
                scheduled_for = _dt.fromisoformat(scheduled_for_str)
                if scheduled_for.tzinfo is None:
                    # Treat as the clinician's local time, then convert to UTC for storage
                    scheduled_for = scheduled_for.replace(tzinfo=client_tz).astimezone(_tz.utc)

                call_module = args.get("module", "Routine Check")
                call_type   = args.get("call_type", "routine")

                pid = uuid.UUID(patient_id)
                p = (await db.execute(select(Patient).where(Patient.patient_id == pid))).scalar_one_or_none()
                day_target = None
                if p and p.discharge_date:
                    day_target = (scheduled_for.date() - p.discharge_date).days

                new_schedule = CallSchedule(
                    patient_id=pid,
                    scheduled_for=scheduled_for,
                    module=call_module,
                    call_type=call_type,
                    day_in_recovery_target=day_target,
                    protocol_name="clinician-chat",
                    status="pending",
                )
                db.add(new_schedule)
                await db.commit()

                local_dt = scheduled_for.astimezone(client_tz)
                formatted_dt = local_dt.strftime("%A, %d %B at %H:%M")
                reply = (
                    f"Done — I've scheduled a {call_module} call for {formatted_dt}. "
                    f"You can view or cancel it in the patient's scheduled calls."
                )
                return {"reply": reply, "model": model, "action": "scheduled"}
            except Exception as e:
                return {"reply": f"I tried to schedule that call but ran into an error: {e}. Please use the scheduler directly.", "model": model}

    content = choice.message.content or ""

    # Some models (e.g. Groq/Llama) emit tool calls as inline text rather than
    # structured tool_calls. Detect and execute them here.
    import re as _re
    func_match = _re.search(
        r"<function=schedule_call>\s*(\{.*?\})\s*</function>",
        content,
        _re.DOTALL,
    )
    if func_match:
        try:
            args = json.loads(func_match.group(1))
            scheduled_for_str = args.get("scheduled_for", "")
            scheduled_for = _dt.fromisoformat(scheduled_for_str)
            if scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=client_tz).astimezone(_tz.utc)

            call_module = args.get("module", "Routine Check")
            call_type   = args.get("call_type", "routine")

            pid = uuid.UUID(patient_id)
            p = (await db.execute(select(Patient).where(Patient.patient_id == pid))).scalar_one_or_none()
            day_target = None
            if p and p.discharge_date:
                day_target = (scheduled_for.date() - p.discharge_date).days

            new_schedule = CallSchedule(
                patient_id=pid,
                scheduled_for=scheduled_for,
                module=call_module,
                call_type=call_type,
                day_in_recovery_target=day_target,
                protocol_name="clinician-chat",
                status="pending",
            )
            db.add(new_schedule)
            await db.commit()

            # Strip everything from the inline function call onwards so the
            # clinical summary text before it is preserved as the reply.
            clean_text = content[:func_match.start()].strip()
            local_dt = scheduled_for.astimezone(client_tz)
            formatted_dt = local_dt.strftime("%A, %d %B at %H:%M")
            confirmation = f"Done — I've scheduled a {call_module} call for {formatted_dt}."
            reply = f"{clean_text}\n\n{confirmation}".strip() if clean_text else confirmation
            return {"reply": reply, "model": model, "action": "scheduled"}
        except Exception:
            # If parsing fails, just strip the raw function tag from the reply
            content = _re.sub(r"<function=schedule_call>.*?</function>", "", content, flags=_re.DOTALL).strip()

    return {"reply": content, "model": model}
