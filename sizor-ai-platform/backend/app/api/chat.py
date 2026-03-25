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
    CallRecord, ClinicalExtraction, SOAPNote, UrgencyFlag, ProbeCall,
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

def _pick_model(requested: str | None) -> str:
    """Return the best available model."""
    if requested and requested in MODELS:
        req = MODELS[requested]["requires"]
        if getattr(settings, req, ""):
            return requested

    # priority order
    if settings.openai_api_key:
        return "gpt-4o"
    if settings.groq_api_key:
        return "groq/meta-llama/llama-4-scout-17b-16e-instruct"
    if settings.anthropic_api_key:
        return "claude-opus-4-6"
    return settings.llm_model


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

    lines = [
        "You are Sizor AI, a clinical assistant embedded in a post-discharge monitoring platform.",
        "You are in a live chat with an NHS clinician reviewing this patient.",
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
            lines += [
                "",
                f"── Latest Clinical Scores (Day {latest.day_in_recovery}) ──",
                f"  Pain: {ext.pain_score}/10",
                f"  Breathlessness: {ext.breathlessness_score}/10",
                f"  Mobility: {ext.mobility_score}/10",
                f"  Appetite: {ext.appetite_score}/10",
                f"  Mood: {ext.mood_score}/10",
                f"  Medication adherent: {ext.medication_adherence}",
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
    Non-streaming chat endpoint.
    Body: { "messages": [{"role": "user"|"assistant", "content": "..."}], "model": "gpt-4o" }
    """
    _set_env()
    model = _pick_model(data.get("model"))
    messages_in = data.get("messages", [])
    if not messages_in:
        raise HTTPException(400, "messages required")

    system_prompt = await _build_context(patient_id, db)

    messages = [{"role": "system", "content": system_prompt}]
    for m in messages_in:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=300,
        )
        content = response.choices[0].message.content or ""
        return {"reply": content, "model": model}
    except Exception as exc:
        # fallback to second model
        fallback = "groq/meta-llama/llama-4-scout-17b-16e-instruct" if model != "groq/meta-llama/llama-4-scout-17b-16e-instruct" and settings.groq_api_key else None
        if fallback:
            try:
                response = await litellm.acompletion(
                    model=fallback,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=300,
                )
                content = response.choices[0].message.content or ""
                return {"reply": content, "model": fallback}
            except Exception:
                pass
        raise HTTPException(500, f"LLM error: {str(exc)}")
