import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import (
    Patient, PatientMedicalProfile, ClinicalExtraction, CallRecord,
    UrgencyFlag, FTPRecord, ClinicianAction, LongitudinalSummary, CallSchedule,
    ClinicalDecision, SOAPNote,
)
from .auth import get_current_clinician
from ..services.nice_guidelines import get_guidelines_for_condition
from ..services.ftp_service import interpolate_expected
from ..config import settings

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/internal/by-nhs/{nhs_number}")
async def get_patient_by_nhs(
    nhs_number: str,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """Internal endpoint for voice agent to look up a patient by NHS number."""
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")
    result = await db.execute(select(Patient).where(Patient.nhs_number == nhs_number))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    day = None
    if patient.discharge_date:
        from datetime import date
        day = (date.today() - patient.discharge_date).days
    return _patient_dict(patient, day)


def _patient_dict(p: Patient, day: int | None = None) -> dict:
    return {
        "patient_id": str(p.patient_id),
        "full_name": p.full_name,
        "nhs_number": p.nhs_number,
        "date_of_birth": str(p.date_of_birth) if p.date_of_birth else None,
        "phone_number": p.phone_number,
        "condition": p.condition,
        "procedure": p.procedure,
        "admission_date": str(p.admission_date) if p.admission_date else None,
        "discharge_date": str(p.discharge_date) if p.discharge_date else None,
        "program_module": p.program_module,
        "status": p.status,
        "assigned_clinician_id": str(p.assigned_clinician_id) if p.assigned_clinician_id else None,
        "ward_id": str(p.ward_id) if p.ward_id else None,
        "hospital_id": str(p.hospital_id),
        "day_in_recovery": day,
    }


@router.get("")
async def list_patients(
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(select(Patient).order_by(Patient.created_at.desc()))
    patients = result.scalars().all()
    out = []
    for p in patients:
        day = None
        if p.discharge_date:
            day = (datetime.now(timezone.utc).date() - p.discharge_date).days
        out.append(_patient_dict(p, day))
    return out


@router.post("")
async def create_patient(
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    profile_data = data.pop("medical_profile", None)
    patient = Patient(**data)
    db.add(patient)
    await db.flush()
    if profile_data:
        profile = PatientMedicalProfile(patient_id=patient.patient_id, **profile_data)
        db.add(profile)
    await db.commit()
    return {"patient_id": str(patient.patient_id)}


@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(Patient).where(Patient.patient_id == uuid.UUID(patient_id))
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    day = None
    if patient.discharge_date:
        day = (datetime.now(timezone.utc).date() - patient.discharge_date).days

    profile_result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == patient.patient_id)
    )
    profile = profile_result.scalar_one_or_none()

    # Latest urgency flag
    flag_result = await db.execute(
        select(UrgencyFlag)
        .where(UrgencyFlag.patient_id == patient.patient_id, UrgencyFlag.status.in_(["open", "reviewing"]))
        .order_by(UrgencyFlag.raised_at.desc())
        .limit(1)
    )
    latest_flag = flag_result.scalar_one_or_none()

    # Current longitudinal summary
    summary_result = await db.execute(
        select(LongitudinalSummary)
        .where(LongitudinalSummary.patient_id == patient.patient_id, LongitudinalSummary.is_current == True)
    )
    summary = summary_result.scalar_one_or_none()

    # Next schedule
    schedule_result = await db.execute(
        select(CallSchedule)
        .where(CallSchedule.patient_id == patient.patient_id, CallSchedule.status == "pending")
        .order_by(CallSchedule.scheduled_for)
        .limit(1)
    )
    next_schedule = schedule_result.scalar_one_or_none()

    # Clinician actions
    actions_result = await db.execute(
        select(ClinicianAction)
        .where(ClinicianAction.patient_id == patient.patient_id)
        .order_by(ClinicianAction.action_at)
    )
    actions = actions_result.scalars().all()

    out = _patient_dict(patient, day)
    out["urgency_severity"] = latest_flag.severity if latest_flag else "green"
    out["medical_profile"] = {
        "primary_diagnosis": profile.primary_diagnosis,
        "secondary_diagnoses": profile.secondary_diagnoses,
        "current_medications": profile.current_medications,
        "allergies": profile.allergies,
        "relevant_comorbidities": profile.relevant_comorbidities,
        "discharge_summary_text": profile.discharge_summary_text,
        "consultant_notes": profile.consultant_notes,
    } if profile else None
    out["longitudinal_summary"] = {
        "summary_id": str(summary.summary_id),
        "narrative_text": summary.narrative_text,
        "active_concerns_snapshot": summary.active_concerns_snapshot,
        "trend_snapshot": summary.trend_snapshot,
        "version_number": summary.version_number,
        "generated_at": summary.generated_at.isoformat(),
        "clinician_locked": summary.clinician_locked,
        "clinician_edited_text": summary.clinician_edited_text,
    } if summary else None
    out["next_scheduled_call"] = next_schedule.scheduled_for.isoformat() if next_schedule else None
    out["clinician_actions"] = [
        {
            "action_id": str(a.action_id),
            "action_type": a.action_type,
            "action_at": a.action_at.isoformat(),
            "notes_text": a.notes_text,
            "probe_instructions": a.probe_instructions,
            "call_id": str(a.call_id) if a.call_id else None,
            "clinician_id": str(a.clinician_id),
        }
        for a in actions
    ]
    return out


@router.put("/{patient_id}")
async def update_patient(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(select(Patient).where(Patient.patient_id == uuid.UUID(patient_id)))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")
    for k, v in data.items():
        if hasattr(patient, k):
            setattr(patient, k, v)
    await db.commit()
    return {"status": "ok"}


@router.get("/{patient_id}/profile")
async def get_profile(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == uuid.UUID(patient_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    return {
        "primary_diagnosis": profile.primary_diagnosis,
        "secondary_diagnoses": profile.secondary_diagnoses,
        "current_medications": profile.current_medications,
        "allergies": profile.allergies,
        "relevant_comorbidities": profile.relevant_comorbidities,
        "discharge_summary_text": profile.discharge_summary_text,
        "consultant_notes": profile.consultant_notes,
    }


@router.put("/{patient_id}/profile")
async def update_profile(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == uuid.UUID(patient_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    for k, v in data.items():
        if hasattr(profile, k):
            setattr(profile, k, v)
    profile.last_updated = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok"}


@router.get("/{patient_id}/trends")
async def get_trends(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(ClinicalExtraction, CallRecord)
        .join(CallRecord, ClinicalExtraction.call_id == CallRecord.call_id)
        .where(ClinicalExtraction.patient_id == uuid.UUID(patient_id))
        .order_by(CallRecord.day_in_recovery)
    )
    rows = result.all()

    p_result = await db.execute(select(Patient).where(Patient.patient_id == uuid.UUID(patient_id)))
    patient = p_result.scalar_one_or_none()

    guidelines = get_guidelines_for_condition(patient.condition if patient else "")
    curves = guidelines.get("recovery_curves", {})

    domains = ["pain", "breathlessness", "mobility", "appetite", "mood"]
    trend_data = {d: {"actual": [], "expected": []} for d in domains}

    for extraction, call in rows:
        day = call.day_in_recovery or 0
        score_map = {
            "pain": extraction.pain_score,
            "breathlessness": extraction.breathlessness_score,
            "mobility": extraction.mobility_score,
            "appetite": extraction.appetite_score,
            "mood": extraction.mood_score,
        }
        for domain in domains:
            actual = score_map.get(domain)
            if actual is not None:
                trend_data[domain]["actual"].append({"day": day, "score": actual})
            curve = curves.get(domain)
            if curve:
                exp = interpolate_expected(curve, day)
                if exp is not None:
                    trend_data[domain]["expected"].append({"day": day, "score": round(exp, 2)})

    return trend_data


@router.get("/{patient_id}/calls")
async def get_patient_calls(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == uuid.UUID(patient_id))
        .order_by(CallRecord.started_at.desc())
    )
    calls = result.scalars().all()
    return [
        {
            "call_id": str(c.call_id),
            "direction": c.direction,
            "trigger_type": c.trigger_type,
            "day_in_recovery": c.day_in_recovery,
            "status": c.status,
            "duration_seconds": c.duration_seconds,
            "started_at": c.started_at.isoformat(),
        }
        for c in calls
    ]


@router.get("/{patient_id}/schedule")
async def get_schedule(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(CallSchedule)
        .where(CallSchedule.patient_id == uuid.UUID(patient_id))
        .order_by(CallSchedule.scheduled_for)
    )
    items = result.scalars().all()
    return [
        {
            "schedule_id": str(s.schedule_id),
            "scheduled_for": s.scheduled_for.isoformat(),
            "call_type": s.call_type,
            "module": s.module,
            "status": s.status,
        }
        for s in items
    ]


@router.post("/{patient_id}/schedule")
async def add_schedule(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    s = CallSchedule(patient_id=uuid.UUID(patient_id), **data)
    db.add(s)
    await db.commit()
    return {"schedule_id": str(s.schedule_id)}


@router.get("/{patient_id}/decisions")
async def get_patient_decisions(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(ClinicalDecision)
        .where(ClinicalDecision.patient_id == uuid.UUID(patient_id))
        .order_by(ClinicalDecision.requested_at.desc())
    )
    decisions = result.scalars().all()
    return [
        {
            "decision_id": str(d.decision_id),
            "call_id": str(d.call_id),
            "requested_at": d.requested_at.isoformat(),
            "actioned": d.actioned,
            "risk_assessment": d.risk_assessment[:200] if d.risk_assessment else "",
            "clinician_response": d.clinician_response,
        }
        for d in decisions
    ]


@router.post("/{patient_id}/actions/review")
async def action_review(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    call_id = data.get("call_id")
    if call_id:
        result = await db.execute(select(SOAPNote).where(SOAPNote.call_id == uuid.UUID(call_id)))
        soap = result.scalar_one_or_none()
        if soap:
            soap.clinician_reviewed = True
    action = ClinicianAction(
        patient_id=uuid.UUID(patient_id),
        clinician_id=clinician.clinician_id,
        call_id=uuid.UUID(call_id) if call_id else None,
        action_type="reviewed",
        notes_text=data.get("notes"),
    )
    db.add(action)
    await db.commit()
    return {"status": "ok"}


@router.post("/{patient_id}/actions/note")
async def action_note(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    action = ClinicianAction(
        patient_id=uuid.UUID(patient_id),
        clinician_id=clinician.clinician_id,
        call_id=uuid.UUID(data["call_id"]) if data.get("call_id") else None,
        action_type="note_added",
        notes_text=data.get("notes_text"),
    )
    db.add(action)
    await db.commit()
    return {"status": "ok"}


@router.post("/{patient_id}/actions/probe")
async def action_probe(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    action = ClinicianAction(
        patient_id=uuid.UUID(patient_id),
        clinician_id=clinician.clinician_id,
        action_type="probe_triggered",
        probe_instructions=data.get("probe_instructions"),
        notes_text=data.get("notes"),
    )
    db.add(action)
    await db.flush()
    schedule = CallSchedule(
        patient_id=uuid.UUID(patient_id),
        scheduled_for=datetime.fromisoformat(data["scheduled_for"]),
        module=data.get("module", "post_discharge"),
        call_type="probe",
        protocol_name="probe",
        triggered_by_action_id=action.action_id,
    )
    db.add(schedule)
    await db.commit()
    return {"status": "ok", "action_id": str(action.action_id)}


@router.post("/{patient_id}/actions/escalate")
async def action_escalate(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    action = ClinicianAction(
        patient_id=uuid.UUID(patient_id),
        clinician_id=clinician.clinician_id,
        action_type="escalated",
        notes_text=data.get("notes"),
    )
    db.add(action)
    result = await db.execute(select(Patient).where(Patient.patient_id == uuid.UUID(patient_id)))
    patient = result.scalar_one_or_none()
    if patient:
        patient.status = "escalated"
    await db.commit()
    return {"status": "ok"}


@router.post("/{patient_id}/actions/resolve-flag/{flag_id}")
async def resolve_flag(
    patient_id: str,
    flag_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(select(UrgencyFlag).where(UrgencyFlag.flag_id == uuid.UUID(flag_id)))
    flag = result.scalar_one_or_none()
    if flag:
        flag.status = "resolved"
        flag.resolved_at = datetime.now(timezone.utc)
        flag.resolution_notes = data.get("resolution_notes")
    action = ClinicianAction(
        patient_id=uuid.UUID(patient_id),
        clinician_id=clinician.clinician_id,
        action_type="flag_resolved",
        notes_text=data.get("resolution_notes"),
    )
    db.add(action)
    await db.commit()
    return {"status": "ok"}
