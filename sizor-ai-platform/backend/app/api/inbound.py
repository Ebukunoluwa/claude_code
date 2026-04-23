"""
Inbound Call API — routes called by SizorInboundAgent
─────────────────────────────────────────────────────
All endpoints are authenticated with X-Internal-Key (no JWT required).

Routes
  POST /api/patients/verify-inbound   fuzzy name + exact NHS number verification
  POST /api/escalations/inbound       raise RED urgency flag, notify clinician
  POST /api/soap/generate-async       generate SOAP note via Claude Sonnet
  POST /api/calls/save-inbound        persist CallRecord + trigger Celery pipeline
"""
from __future__ import annotations

import difflib
import json
import re
import uuid
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..database import get_db
from ..models import (
    CallRecord,
    Patient,
    PatientMedicalProfile,
    SOAPNote,
    UrgencyFlag,
)
from ..config import settings
from ..services.llm_client import LLMClient
from ..tasks.celery_app import celery_app

router = APIRouter(tags=["inbound"])

_FUZZY_THRESHOLD = 0.65  # minimum SequenceMatcher ratio for full-name comparison


def _auth(key: str) -> None:
    if key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")


def _fuzzy_match(given: str, stored: str) -> bool:
    """
    Accept if ANY of these pass:
      1. Full-string ratio ≥ 0.65
      2. Any token in `given` exactly matches any token in `stored` (first/last name)
      3. Any token in `given` has ratio ≥ 0.80 with any token in `stored`
    """
    g = given.lower().strip()
    s = stored.lower().strip()

    # Full string similarity
    if difflib.SequenceMatcher(None, g, s).ratio() >= _FUZZY_THRESHOLD:
        return True

    # Token-level matching — handles "James" vs "James Smith"
    g_tokens = set(g.split())
    s_tokens = set(s.split())

    # Exact token overlap
    if g_tokens & s_tokens:
        return True

    # Fuzzy token-level match
    for gt in g_tokens:
        for st in s_tokens:
            if difflib.SequenceMatcher(None, gt, st).ratio() >= 0.80:
                return True

    return False


def _parse_json(text: str) -> dict:
    """Extract JSON from an LLM response that may contain surrounding prose."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(text[s : e + 1])
        except Exception:
            pass
    return {}


# ── 1. Verify patient identity ────────────────────────────────────────────────

@router.post("/api/patients/verify-inbound")
async def verify_inbound_patient(
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Body: { "full_name": "...", "nhs_number": "..." }

    Match logic:
      • Exact NHS number lookup in the patients table.
      • Fuzzy name comparison (SequenceMatcher ≥ 72 %).

    Returns on success:
      { "verified": true, "patient": {...}, "recent_summaries": [...] }
      patient  — full record + medical profile fields.
      recent_summaries — last 3 completed calls SOAP assessments (for system-prompt
                         enrichment mid-call).
    """
    _auth(x_internal_key)

    full_name = (data.get("full_name") or "").strip()
    nhs_number = (data.get("nhs_number") or "").replace(" ", "").replace("-", "")

    import logging as _log
    _log.getLogger(__name__).info(
        "verify-inbound received: full_name=%r nhs_number=%r (len=%d)",
        full_name, nhs_number, len(nhs_number),
    )

    if not full_name or not nhs_number:
        return {"verified": False, "reason": "Name and NHS number are required."}

    result = await db.execute(
        select(Patient).where(Patient.nhs_number == nhs_number)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        _log.getLogger(__name__).warning(
            "verify-inbound: no patient found for nhs_number=%r", nhs_number
        )
        return {"verified": False, "reason": "NHS number not found in our records."}

    if not _fuzzy_match(full_name, patient.full_name):
        return {
            "verified": False,
            "reason": "Name does not match our records. Please check and try again.",
        }

    # Pull medical profile for richer system prompt injection
    profile_result = await db.execute(
        select(PatientMedicalProfile).where(
            PatientMedicalProfile.patient_id == patient.patient_id
        )
    )
    profile = profile_result.scalar_one_or_none()

    # Last 3 completed calls + their SOAP notes for prior-call comparison
    calls_result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == patient.patient_id)
        .where(CallRecord.status == "completed")
        .order_by(desc(CallRecord.started_at))
        .limit(3)
    )
    recent_calls = calls_result.scalars().all()

    recent_summaries: list[dict] = []
    for call in recent_calls:
        soap_result = await db.execute(
            select(SOAPNote).where(SOAPNote.call_id == call.call_id)
        )
        soap = soap_result.scalar_one_or_none()
        if soap:
            recent_summaries.append(
                {
                    "call_id": str(call.call_id),
                    "generated_at": soap.generated_at.isoformat(),
                    "subjective": soap.subjective,
                    "assessment": soap.assessment,
                    "plan": soap.plan,
                }
            )

    day_in_recovery = (
        (date.today() - patient.discharge_date).days
        if patient.discharge_date else None
    )

    patient_dict = {
        "patient_id": str(patient.patient_id),
        "full_name": patient.full_name,
        "nhs_number": patient.nhs_number,
        "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
        "condition": patient.condition,
        "procedure": patient.procedure,
        "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
        "day_in_recovery": day_in_recovery,
        "status": patient.status,
        "assigned_clinician_id": (
            str(patient.assigned_clinician_id) if patient.assigned_clinician_id else None
        ),
        "current_medications": profile.current_medications if profile else [],
        "allergies": profile.allergies if profile else [],
        "primary_diagnosis": profile.primary_diagnosis if profile else None,
        "secondary_diagnoses": profile.secondary_diagnoses if profile else [],
    }

    return {
        "verified": True,
        "patient": patient_dict,
        "recent_summaries": recent_summaries,
    }


# ── 2. Verify by date of birth (fallback when NHS number fails) ───────────────

@router.post("/api/patients/verify-dob")
async def verify_inbound_patient_dob(
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Body: { "nhs_number": "...", "date_of_birth": "YYYY-MM-DD" }

    Fallback verification when the patient cannot provide their NHS number.
    Looks up by NHS number (or name if provided) and checks date of birth.
    Returns the same patient dict as verify-inbound on success.
    """
    _auth(x_internal_key)

    import logging as _log
    nhs_number = (data.get("nhs_number") or "").replace(" ", "").replace("-", "")
    dob_raw = (data.get("date_of_birth") or "").strip()
    full_name = (data.get("full_name") or "").strip()

    if not dob_raw:
        return {"verified": False, "reason": "Date of birth is required."}

    # Normalise DOB to digits only for comparison (handles YYYY-MM-DD, DD/MM/YYYY etc.)
    dob_digits = re.sub(r"\D", "", dob_raw)

    # Find patient by NHS number first, fallback to name
    patient = None
    if nhs_number:
        result = await db.execute(select(Patient).where(Patient.nhs_number == nhs_number))
        patient = result.scalar_one_or_none()

    if not patient and full_name:
        result = await db.execute(select(Patient))
        all_patients = result.scalars().all()
        for p in all_patients:
            if _fuzzy_match(full_name, p.full_name):
                patient = p
                break

    if not patient:
        return {"verified": False, "reason": "Could not find your records. Please contact your GP directly."}

    # Compare DOB
    expected_digits = re.sub(r"\D", "", str(patient.date_of_birth)) if patient.date_of_birth else ""
    if not expected_digits or dob_digits != expected_digits:
        _log.getLogger(__name__).warning(
            "verify-dob: DOB mismatch for nhs=%r provided=%r expected_len=%d",
            nhs_number, dob_raw, len(expected_digits),
        )
        return {"verified": False, "reason": "Date of birth does not match our records."}

    # DOB matched — return same patient dict as verify-inbound
    profile_result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == patient.patient_id)
    )
    profile = profile_result.scalar_one_or_none()

    calls_result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == patient.patient_id)
        .where(CallRecord.status == "completed")
        .order_by(desc(CallRecord.started_at))
        .limit(3)
    )
    recent_calls = calls_result.scalars().all()

    recent_summaries: list[dict] = []
    for call in recent_calls:
        soap_result = await db.execute(select(SOAPNote).where(SOAPNote.call_id == call.call_id))
        soap = soap_result.scalar_one_or_none()
        if soap:
            recent_summaries.append({
                "call_id": str(call.call_id),
                "generated_at": soap.generated_at.isoformat(),
                "subjective": soap.subjective,
                "assessment": soap.assessment,
                "plan": soap.plan,
            })

    day_in_recovery = (
        (date.today() - patient.discharge_date).days if patient.discharge_date else None
    )

    patient_dict = {
        "patient_id": str(patient.patient_id),
        "full_name": patient.full_name,
        "nhs_number": patient.nhs_number,
        "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
        "condition": patient.condition,
        "procedure": patient.procedure,
        "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
        "day_in_recovery": day_in_recovery,
        "status": patient.status,
        "assigned_clinician_id": str(patient.assigned_clinician_id) if patient.assigned_clinician_id else None,
        "current_medications": profile.current_medications if profile else [],
        "allergies": profile.allergies if profile else [],
        "primary_diagnosis": profile.primary_diagnosis if profile else None,
        "secondary_diagnoses": profile.secondary_diagnoses if profile else [],
    }

    return {"verified": True, "patient": patient_dict, "recent_summaries": recent_summaries}


# ── 3. Escalate patient ───────────────────────────────────────────────────────

@router.post("/api/escalations/inbound")
async def escalate_inbound_patient(
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Body: { "call_id": "...", "patient_id": "...", "nhs_number": "...",
            "patient_name": "...", "reason": "...", "triage_level": "red" }

    Creates a RED UrgencyFlag visible in the clinician dashboard.
    Creates a minimal CallRecord if one does not yet exist.
    Returns { "escalated": true, "flag_id": "...", "patient_id": "..." }.
    """
    _auth(x_internal_key)

    call_id_str = data.get("call_id")
    nhs_number = data.get("nhs_number", "")
    reason = data.get("reason", "Red-flag symptom reported during inbound call")

    # Resolve patient — best-effort; escalation proceeds even if unverified
    patient = None
    if data.get("patient_id"):
        result = await db.execute(
            select(Patient).where(
                Patient.patient_id == uuid.UUID(data["patient_id"])
            )
        )
        patient = result.scalar_one_or_none()

    if not patient and nhs_number:
        result = await db.execute(
            select(Patient).where(Patient.nhs_number == nhs_number)
        )
        patient = result.scalar_one_or_none()

    if not patient:
        # Cannot persist without a valid patient FK — log and return gracefully
        import logging as _log
        _log.getLogger(__name__).warning(
            "escalate_inbound: patient not found — call_id=%s nhs=%s",
            call_id_str, nhs_number,
        )
        return {
            "escalated": True,
            "flag_id": None,
            "note": "Patient not found in DB — verbal escalation still delivered",
        }

    # Ensure a CallRecord exists (create a minimal one if not)
    call_uuid: uuid.UUID | None = None
    if call_id_str:
        try:
            call_uuid = uuid.UUID(call_id_str)
        except ValueError:
            call_uuid = None

    if call_uuid:
        existing_call = (
            await db.execute(
                select(CallRecord).where(CallRecord.call_id == call_uuid)
            )
        ).scalar_one_or_none()

        if not existing_call:
            call_record = CallRecord(
                call_id=call_uuid,
                patient_id=patient.patient_id,
                direction="inbound",
                trigger_type="inbound_patient",
                status="in_progress",
                started_at=datetime.now(timezone.utc),
            )
            db.add(call_record)
            await db.flush()

    flag = UrgencyFlag(
        patient_id=patient.patient_id,
        call_id=call_uuid,
        severity="red",
        flag_type="inbound_escalation",
        trigger_description=reason,
        status="open",
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)

    return {
        "escalated": True,
        "flag_id": str(flag.flag_id),
        "severity": "red",
        "patient_id": str(patient.patient_id),
    }


# ── 3. Generate SOAP note (async, Claude Sonnet) ──────────────────────────────

@router.post("/api/soap/generate-async")
async def generate_inbound_soap(
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Body: { "call_id": "...", "patient_id": "...", "nhs_number": "...",
            "patient_name": "...", "transcript": "...", "direction": "inbound" }

    Generates a structured JSON SOAP note via Claude Sonnet:
      subjective  — what the patient reported
      objective   — from the patient record (meds, condition, prior scores)
      assessment  — risk level GREEN/AMBER/RED, FTP flag, comparison to prior calls
      plan        — urgency (routine/urgent/emergency), recommended action

    Saves the SOAPNote to the DB linked to the CallRecord (created if not yet present).
    Never reads the SOAP note to the patient.
    """
    _auth(x_internal_key)

    call_id_str = data.get("call_id") or str(uuid.uuid4())
    nhs_number = data.get("nhs_number", "")
    transcript = data.get("transcript", "")
    direction = data.get("direction", "inbound")

    # Resolve patient
    patient = None
    if data.get("patient_id"):
        result = await db.execute(
            select(Patient).where(
                Patient.patient_id == uuid.UUID(data["patient_id"])
            )
        )
        patient = result.scalar_one_or_none()

    if not patient and nhs_number:
        result = await db.execute(
            select(Patient).where(Patient.nhs_number == nhs_number)
        )
        patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(404, "Patient not found")

    # Medical profile for objective section
    profile = (
        await db.execute(
            select(PatientMedicalProfile).where(
                PatientMedicalProfile.patient_id == patient.patient_id
            )
        )
    ).scalar_one_or_none()

    # Last 3 SOAP assessments for longitudinal comparison
    prior_calls = (
        await db.execute(
            select(CallRecord)
            .where(CallRecord.patient_id == patient.patient_id)
            .where(CallRecord.status == "completed")
            .order_by(desc(CallRecord.started_at))
            .limit(3)
        )
    ).scalars().all()

    prior_assessments: list[str] = []
    for c in prior_calls:
        s = (
            await db.execute(
                select(SOAPNote).where(SOAPNote.call_id == c.call_id)
            )
        ).scalar_one_or_none()
        if s:
            prior_assessments.append(s.assessment)

    # Build objective context from patient record
    meds = ", ".join(profile.current_medications or []) if profile else "none recorded"
    allergies_str = ", ".join(profile.allergies or []) if profile else "none"
    objective_ctx = (
        f"Condition: {patient.condition}\n"
        f"Current medications: {meds}\n"
        f"Allergies: {allergies_str}\n"
    )
    if profile and profile.primary_diagnosis:
        objective_ctx += f"Primary diagnosis: {profile.primary_diagnosis}\n"
    if patient.discharge_date:
        days = (date.today() - patient.discharge_date).days
        objective_ctx += f"Days post-discharge: {days}\n"

    prior_block = ""
    if prior_assessments:
        prior_block = "\nPrior call assessments (newest first):\n" + "\n".join(
            f"- {a}" for a in prior_assessments
        )

    # Claude Sonnet — async SOAP generation
    llm = LLMClient(model=settings.llm_model)

    system_prompt = (
        "You are an NHS clinician writing a post-consultation SOAP note. "
        "Generate a structured SOAP note from this patient call transcript exactly as a doctor would document it. "
        "Return ONLY valid JSON with exactly these keys: subjective, objective, assessment, plan.\n\n"
        "SUBJECTIVE: The patient's reported symptoms and concerns in their own words. "
        "Start with chief complaint. Include severity, duration, and any changes. "
        "Write in third person: 'Patient reports...', 'Patient denies...', 'Patient states...'\n\n"
        "OBJECTIVE: Clinically measurable data from the record and call — pain scores, mobility ratings, "
        "medication adherence, any specific clinical values stated. "
        "If none captured, write 'No objective data captured on this call.'\n\n"
        "ASSESSMENT: Clinical interpretation of current status — risk level (GREEN / AMBER / RED), "
        "whether progressing as expected, any clinical concerns. Reference prior calls where available. Do not diagnose.\n\n"
        "PLAN: Specific actionable next steps only — e.g. 'GP review within 48 hours', "
        "'Continue current medication regime', 'Escalate to on-call team'. Be directive.\n\n"
        "STRICT RULES:\n"
        "- Never mention missed calls, call attempts, or any call logistics.\n"
        "- Never mention the AI or that this was an automated call.\n"
        "- Write exactly as a doctor documents a clinical consultation.\n"
        "- No padding, no repetition. Return JSON only — no markdown fences."
    )
    user_prompt = (
        f"Patient: {patient.full_name}, NHS {patient.nhs_number}\n"
        f"{objective_ctx}"
        f"{prior_block}\n\n"
        f"CALL TRANSCRIPT:\n{transcript}"
    )

    raw = await llm.complete(system_prompt, user_prompt)
    soap_data = _parse_json(raw)

    if not soap_data:
        soap_data = {
            "subjective": raw[:500] if raw else "Unable to extract subjective.",
            "objective": objective_ctx,
            "assessment": "GREEN — automated parsing failed; clinician review required.",
            "plan": "Routine clinician review.",
        }

    # Ensure CallRecord exists before saving the SOAPNote
    call_uuid = uuid.UUID(call_id_str)
    existing_call = (
        await db.execute(
            select(CallRecord).where(CallRecord.call_id == call_uuid)
        )
    ).scalar_one_or_none()

    if not existing_call:
        day = (date.today() - patient.discharge_date).days if patient.discharge_date else None
        call_record = CallRecord(
            call_id=call_uuid,
            patient_id=patient.patient_id,
            direction=direction,
            trigger_type="inbound_patient",
            day_in_recovery=day,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
            transcript_raw=transcript,
        )
        db.add(call_record)
        await db.flush()

    soap = SOAPNote(
        call_id=call_uuid,
        patient_id=patient.patient_id,
        subjective=soap_data.get("subjective", ""),
        objective=soap_data.get("objective", objective_ctx),
        assessment=soap_data.get("assessment", ""),
        plan=soap_data.get("plan", ""),
        model_used=settings.llm_model,
    )
    db.add(soap)
    await db.commit()
    await db.refresh(soap)

    return {
        "generated": True,
        "soap_id": str(soap.soap_id),
        "call_id": call_id_str,
    }


# ── 4. Save inbound call record ───────────────────────────────────────────────

@router.post("/api/calls/save-inbound")
async def save_inbound_call(
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Body: { "call_id": "...", "patient_id": "...", "nhs_number": "...",
            "patient_name": "...", "transcript": "...", "duration_seconds": int,
            "triage_level": "green|amber|red", "triage_reasons": [...],
            "direction": "inbound", "trigger_type": "inbound_patient",
            "identity_verified": bool }

    Saves or updates the CallRecord (status → completed) and triggers the
    standard Celery processing pipeline (SOAP if not already done, extraction,
    urgency flags, longitudinal summary) via the existing process_call task.
    Also notifies the assigned clinician via the pipeline.
    """
    _auth(x_internal_key)

    call_id_str = data.get("call_id") or str(uuid.uuid4())
    nhs_number = data.get("nhs_number", "")
    transcript = data.get("transcript", "")
    direction = data.get("direction", "inbound")

    # Resolve patient
    patient = None
    if data.get("patient_id"):
        result = await db.execute(
            select(Patient).where(
                Patient.patient_id == uuid.UUID(data["patient_id"])
            )
        )
        patient = result.scalar_one_or_none()

    if not patient and nhs_number:
        result = await db.execute(
            select(Patient).where(Patient.nhs_number == nhs_number)
        )
        patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            404, "Patient not found — register them in the dashboard first"
        )

    call_uuid = uuid.UUID(call_id_str)
    day = (
        (date.today() - patient.discharge_date).days
        if patient.discharge_date
        else None
    )

    existing = (
        await db.execute(
            select(CallRecord).where(CallRecord.call_id == call_uuid)
        )
    ).scalar_one_or_none()

    final_status = data.get("call_status") or ("missed" if not transcript and data.get("duration_seconds", 1) == 0 else "completed")

    if existing:
        existing.status = final_status
        existing.ended_at = datetime.now(timezone.utc)
        if transcript:
            existing.transcript_raw = transcript
        if data.get("duration_seconds") is not None:
            existing.duration_seconds = data["duration_seconds"]
        await db.commit()
    else:
        call = CallRecord(
            call_id=call_uuid,
            patient_id=patient.patient_id,
            direction=direction,
            trigger_type=data.get("trigger_type", "inbound_patient"),
            day_in_recovery=day,
            status=final_status,
            duration_seconds=data.get("duration_seconds"),
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            transcript_raw=transcript,
        )
        db.add(call)
        await db.commit()

    # Trigger full clinical pipeline (extraction, flags, longitudinal summary;
    # SOAP already created if generate_soap_note was called mid-call)
    celery_app.send_task("process_call", args=[call_id_str])

    return {
        "call_id": call_id_str,
        "patient_id": str(patient.patient_id),
        "status": "queued",
        "direction": direction,
    }
