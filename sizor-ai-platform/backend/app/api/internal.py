"""
Internal API — called by the voice agent only (no JWT, uses X-Internal-Key).
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import CallSchedule, Patient, CallRecord, SOAPNote, ClinicalExtraction, UrgencyFlag, LongitudinalSummary
from ..config import settings

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/schedules/due")
async def get_due_schedules(
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Return all pending CallSchedule rows whose scheduled_for <= now.
    Includes the patient's phone, name, and NHS number so the voice agent
    can initiate the call without a second lookup.
    """
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(CallSchedule, Patient)
        .join(Patient, CallSchedule.patient_id == Patient.patient_id)
        .where(CallSchedule.status == "pending", CallSchedule.scheduled_for <= now)
        .order_by(CallSchedule.scheduled_for)
    )
    rows = result.all()

    return [
        {
            "schedule_id": str(s.schedule_id),
            "patient_id": str(s.patient_id),
            "scheduled_for": s.scheduled_for.isoformat(),
            "call_type": s.call_type,
            "module": s.module,
            "protocol_name": s.protocol_name,
            "probe_instructions": None,  # populated from triggered ClinicianAction if needed
            "patient_name": p.full_name,
            "nhs_number": p.nhs_number,
            "phone_number": p.phone_number,
        }
        for s, p in rows
    ]


@router.post("/schedules/{schedule_id}/dispatch")
async def dispatch_schedule(
    schedule_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Mark a CallSchedule as dispatched and record the resulting call_id.
    Called by the voice agent immediately after initiating the SIP call.
    """
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    result = await db.execute(
        select(CallSchedule).where(CallSchedule.schedule_id == uuid.UUID(schedule_id))
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    schedule.status = "dispatched"
    await db.commit()
    return {"status": "dispatched", "schedule_id": schedule_id}


@router.post("/patients/{patient_id}/schedule")
async def create_schedule_internal(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Create a CallSchedule entry without JWT.
    Used by the CLI schedule_call.py script.
    """
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    from ..models import CallSchedule
    from datetime import datetime

    s = CallSchedule(
        patient_id=uuid.UUID(patient_id),
        scheduled_for=datetime.fromisoformat(data["scheduled_for"]),
        module=data.get("module", "post_discharge"),
        call_type=data.get("call_type", "routine"),
        protocol_name=data.get("protocol_name", "standard"),
    )
    db.add(s)
    await db.commit()
    return {"schedule_id": str(s.schedule_id)}


@router.get("/patients/by-nhs/{nhs_number}")
async def get_patient_by_nhs_internal(
    nhs_number: str,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Look up a patient by NHS number.
    Used by the voice agent's schedule_call script.
    """
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    result = await db.execute(select(Patient).where(Patient.nhs_number == nhs_number))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    from datetime import date
    day = (date.today() - patient.discharge_date).days if patient.discharge_date else None

    return {
        "patient_id": str(patient.patient_id),
        "full_name": patient.full_name,
        "nhs_number": patient.nhs_number,
        "phone_number": patient.phone_number,
        "condition": patient.condition,
        "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
        "day_in_recovery": day,
    }


@router.get("/patients/by-nhs/{nhs_number}/call-context")
async def get_call_context(
    nhs_number: str,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Return previous call context for the voice agent to inject into its system prompt.
    Includes: last 3 SOAP notes, open urgency flags, active concerns, recent extraction scores.
    """
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    patient_result = await db.execute(select(Patient).where(Patient.nhs_number == nhs_number))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        return {"has_history": False}

    # Last 3 completed calls
    calls_result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == patient.patient_id, CallRecord.status == "completed")
        .order_by(CallRecord.started_at.desc())
        .limit(3)
    )
    recent_calls = calls_result.scalars().all()

    if not recent_calls:
        return {"has_history": False}

    call_summaries = []
    for call in recent_calls:
        soap_result = await db.execute(
            select(SOAPNote).where(SOAPNote.call_id == call.call_id)
        )
        soap = soap_result.scalar_one_or_none()

        ext_result = await db.execute(
            select(ClinicalExtraction).where(ClinicalExtraction.call_id == call.call_id)
        )
        ext = ext_result.scalar_one_or_none()

        summary = {}
        if call.day_in_recovery is not None:
            summary["day"] = call.day_in_recovery
        if soap:
            summary["assessment"] = soap.assessment
            summary["plan"] = soap.plan
            if soap.subjective:
                summary["what_patient_reported"] = soap.subjective
        if ext:
            scores = {}
            if ext.pain_score is not None:
                scores["pain"] = ext.pain_score
            if ext.mood_score is not None:
                scores["mood"] = ext.mood_score
            if ext.mobility_score is not None:
                scores["mobility"] = ext.mobility_score
            if ext.medication_adherence is not None:
                scores["medication_adherent"] = ext.medication_adherence
            if ext.red_flags:
                scores["red_flags"] = ext.red_flags
            if ext.concerns:
                scores["concerns_noted"] = ext.concerns
            if scores:
                summary["scores"] = scores
        if summary:
            call_summaries.append(summary)

    # Open urgency flags
    flags_result = await db.execute(
        select(UrgencyFlag)
        .where(
            UrgencyFlag.patient_id == patient.patient_id,
            UrgencyFlag.status.in_(["open", "reviewing"]),
        )
        .order_by(UrgencyFlag.raised_at.desc())
        .limit(5)
    )
    open_flags = [
        {"severity": f.severity, "type": f.flag_type, "description": f.trigger_description}
        for f in flags_result.scalars().all()
    ]

    # Active concerns from longitudinal summary
    summary_result = await db.execute(
        select(LongitudinalSummary)
        .where(
            LongitudinalSummary.patient_id == patient.patient_id,
            LongitudinalSummary.is_current == True,
        )
    )
    long_summary = summary_result.scalar_one_or_none()
    active_concerns = []
    if long_summary and long_summary.active_concerns_snapshot:
        for c in long_summary.active_concerns_snapshot:
            label = c.get("concern") if isinstance(c, dict) else c
            if label:
                active_concerns.append(str(label))

    return {
        "has_history": True,
        "patient_condition": patient.condition,
        "call_summaries": call_summaries,
        "open_flags": open_flags,
        "active_concerns": active_concerns,
    }
