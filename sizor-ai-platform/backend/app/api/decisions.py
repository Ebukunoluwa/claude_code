import uuid
from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import (
    ClinicalDecision, CallRecord, Patient, PatientMedicalProfile,
    ClinicalExtraction, SOAPNote, FTPRecord, UrgencyFlag,
    ClinicianAction, LongitudinalSummary, CallSchedule,
)
from .auth import get_current_clinician
from ..services.clinical_decision import generate_clinical_decision

router = APIRouter(tags=["decisions"])


@router.post("/calls/{call_id}/decision")
async def create_decision(
    call_id: str,
    data: dict = None,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    data = data or {}

    call_result = await db.execute(
        select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id))
    )
    call = call_result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call not found")

    patient_result = await db.execute(
        select(Patient).where(Patient.patient_id == call.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    profile_result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == patient.patient_id)
    )
    profile = profile_result.scalar_one_or_none()

    ext_result = await db.execute(
        select(ClinicalExtraction).where(ClinicalExtraction.call_id == call.call_id)
    )
    extraction = ext_result.scalar_one_or_none()

    soap_result = await db.execute(select(SOAPNote).where(SOAPNote.call_id == call.call_id))
    soap = soap_result.scalar_one_or_none()

    ftp_result = await db.execute(select(FTPRecord).where(FTPRecord.call_id == call.call_id))
    ftp = ftp_result.scalar_one_or_none()

    flags_result = await db.execute(
        select(UrgencyFlag).where(
            UrgencyFlag.patient_id == patient.patient_id,
            UrgencyFlag.status.in_(["open", "reviewing"]),
        )
    )
    open_flags = flags_result.scalars().all()

    summary_result = await db.execute(
        select(LongitudinalSummary).where(
            LongitudinalSummary.patient_id == patient.patient_id,
            LongitudinalSummary.is_current == True,
        )
    )
    summary = summary_result.scalar_one_or_none()

    actions_result = await db.execute(
        select(ClinicianAction)
        .where(ClinicianAction.patient_id == patient.patient_id)
        .order_by(ClinicianAction.action_at)
    )
    actions = actions_result.scalars().all()

    age = None
    if patient.date_of_birth:
        today = date.today()
        dob = patient.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    medical_profile_dict = {}
    if profile:
        medical_profile_dict = {
            "primary_diagnosis": profile.primary_diagnosis,
            "current_medications": profile.current_medications,
            "allergies": profile.allergies,
            "relevant_comorbidities": profile.relevant_comorbidities,
            "discharge_summary_text": profile.discharge_summary_text,
        }

    result = await generate_clinical_decision(
        clinical_question=data.get("clinical_question"),
        patient_name=patient.full_name,
        age=age,
        condition=patient.condition,
        day=call.day_in_recovery or 0,
        medical_profile=medical_profile_dict,
        current_soap=soap.assessment if soap else "",
        current_extraction={
            "pain_score": extraction.pain_score if extraction else None,
            "breathlessness_score": extraction.breathlessness_score if extraction else None,
            "mobility_score": extraction.mobility_score if extraction else None,
            "mood_score": extraction.mood_score if extraction else None,
            "medication_adherence": extraction.medication_adherence if extraction else None,
            "condition_specific_flags": extraction.condition_specific_flags if extraction else {},
        },
        ftp_record={
            "ftp_status": ftp.ftp_status if ftp else "unknown",
            "reasoning_text": ftp.reasoning_text if ftp else "",
        },
        open_flags=[
            {"severity": f.severity, "flag_type": f.flag_type, "trigger_description": f.trigger_description}
            for f in open_flags
        ],
        longitudinal_narrative=summary.narrative_text if summary else "",
        trend_data=[],
        clinician_actions=[
            {"action_type": a.action_type, "action_at": a.action_at.isoformat(), "notes_text": a.notes_text}
            for a in actions
        ],
        probe_outcomes=[],
    )

    decision = ClinicalDecision(
        patient_id=patient.patient_id,
        call_id=call.call_id,
        clinician_id=clinician.clinician_id,
        clinical_question=data.get("clinical_question"),
        patient_context_snapshot={"condition": patient.condition, "day": call.day_in_recovery},
        differential_diagnoses=result["differential_diagnoses"],
        recommended_actions=result["recommended_actions"],
        risk_assessment=result["risk_assessment"],
        uncertainty_flags=result["uncertainty_flags"],
        nice_references=result["nice_references"],
        full_reasoning_text=result["full_reasoning_text"],
    )
    db.add(decision)

    action_log = ClinicianAction(
        patient_id=patient.patient_id,
        call_id=call.call_id,
        clinician_id=clinician.clinician_id,
        action_type="decision_requested",
    )
    db.add(action_log)
    await db.commit()

    return {
        "decision_id": str(decision.decision_id),
        "requested_at": decision.requested_at.isoformat(),
        "differential_diagnoses": result["differential_diagnoses"],
        "recommended_actions": result["recommended_actions"],
        "risk_assessment": result["risk_assessment"],
        "uncertainty_flags": result["uncertainty_flags"],
        "nice_references": result["nice_references"],
        "full_reasoning_text": result["full_reasoning_text"],
        "actioned": False,
        "clinician_response": None,
    }


@router.get("/calls/{call_id}/decision")
async def get_decision(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(ClinicalDecision)
        .where(ClinicalDecision.call_id == uuid.UUID(call_id))
        .order_by(ClinicalDecision.requested_at.desc())
        .limit(1)
    )
    decision = result.scalar_one_or_none()
    if not decision:
        return None
    return {
        "decision_id": str(decision.decision_id),
        "requested_at": decision.requested_at.isoformat(),
        "differential_diagnoses": decision.differential_diagnoses,
        "recommended_actions": decision.recommended_actions,
        "risk_assessment": decision.risk_assessment,
        "uncertainty_flags": decision.uncertainty_flags,
        "nice_references": decision.nice_references,
        "full_reasoning_text": decision.full_reasoning_text,
        "actioned": decision.actioned,
        "clinician_response": decision.clinician_response,
        "clinician_response_at": decision.clinician_response_at.isoformat() if decision.clinician_response_at else None,
    }


@router.post("/decisions/{decision_id}/respond")
async def respond_to_decision(
    decision_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(ClinicalDecision).where(ClinicalDecision.decision_id == uuid.UUID(decision_id))
    )
    decision = result.scalar_one_or_none()
    if not decision:
        raise HTTPException(404, "Decision not found")

    decision.clinician_response = data["clinician_response"]
    decision.clinician_response_at = datetime.now(timezone.utc)
    decision.actioned = True

    action = ClinicianAction(
        patient_id=decision.patient_id,
        call_id=decision.call_id,
        clinician_id=clinician.clinician_id,
        action_type="decision_actioned",
        notes_text=data["clinician_response"],
    )
    db.add(action)
    await db.commit()
    return {"status": "ok"}


@router.get("/schedule/today")
async def schedule_today(
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    result = await db.execute(
        select(CallSchedule).where(
            CallSchedule.scheduled_for >= today,
            CallSchedule.scheduled_for < tomorrow,
            CallSchedule.status == "pending",
        )
    )
    items = result.scalars().all()
    return [
        {
            "schedule_id": str(s.schedule_id),
            "patient_id": str(s.patient_id),
            "scheduled_for": s.scheduled_for.isoformat(),
            "call_type": s.call_type,
            "module": s.module,
        }
        for s in items
    ]
