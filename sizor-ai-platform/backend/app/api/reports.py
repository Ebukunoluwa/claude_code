"""
Patient Summary Report API
GET  /patients/{patient_id}/report/pdf   — download PDF
POST /patients/{patient_id}/report/email — email PDF to GP / recipient
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from ..database import get_db
from ..models import (
    Patient, PatientMedicalProfile, CallRecord, SOAPNote,
    ClinicalExtraction, UrgencyFlag, ClinicianAction, LongitudinalSummary,
)
from .auth import get_current_clinician
from ..clinical_intelligence.pathway_map import OPCS_TO_NICE_MAP
from ..services.report_service import build_patient_summary_pdf, send_summary_email

router = APIRouter(prefix="/patients", tags=["reports"])


async def _gather_report_data(patient_id: str, db: AsyncSession) -> dict:
    """Assemble all data needed for the PDF from the database."""
    pid = uuid.UUID(patient_id)

    # Patient core
    p_result = await db.execute(select(Patient).where(Patient.patient_id == pid))
    patient = p_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Medical profile
    prof_result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == pid)
    )
    profile = prof_result.scalar_one_or_none()

    # Pathway
    pw_row = await db.execute(text("""
        SELECT opcs_code, domains, risk_flags, clinical_red_flags
        FROM patient_pathways
        WHERE patient_id = :pid AND active = true
        LIMIT 1
    """), {"pid": str(pid)})
    pw = pw_row.mappings().first()
    pathway = None
    if pw:
        pw_meta = OPCS_TO_NICE_MAP.get(pw["opcs_code"], {})
        pathway = {
            "opcs_code": pw["opcs_code"],
            "pathway_label": pw_meta.get("label", pw["opcs_code"]),
            "domains": pw["domains"] or [],
            "risk_flags": pw["risk_flags"] or [],
            "clinical_red_flags": pw["clinical_red_flags"] or [],
        }

    # All completed calls with SOAP + extraction
    calls_result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == pid, CallRecord.status == "completed")
        .order_by(CallRecord.started_at)
    )
    call_records = calls_result.scalars().all()

    call_data = []
    for call in call_records:
        # SOAP
        soap_result = await db.execute(
            select(SOAPNote).where(SOAPNote.call_id == call.call_id)
            .order_by(SOAPNote.generated_at.desc()).limit(1)
        )
        soap = soap_result.scalar_one_or_none()

        # Extraction
        ext_result = await db.execute(
            select(ClinicalExtraction).where(ClinicalExtraction.call_id == call.call_id)
            .order_by(ClinicalExtraction.extracted_at.desc()).limit(1)
        )
        ext = ext_result.scalar_one_or_none()

        call_data.append({
            "call_id": str(call.call_id),
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "duration_seconds": call.duration_seconds,
            "day_in_recovery": call.day_in_recovery,
            "direction": call.direction,
            "trigger_type": call.trigger_type,
            "soap": {
                "subjective": soap.subjective,
                "objective": soap.objective,
                "assessment": soap.assessment,
                "plan": soap.plan,
            } if soap else {},
            "extraction": {
                "pain_score": ext.pain_score,
                "mood_score": ext.mood_score,
                "mobility_score": ext.mobility_score,
                "breathlessness_score": ext.breathlessness_score,
                "medication_adherence": ext.medication_adherence,
                "condition_specific_flags": ext.condition_specific_flags,
            } if ext else {},
        })

    # All urgency flags (all statuses, chronological)
    flags_result = await db.execute(
        select(UrgencyFlag)
        .where(UrgencyFlag.patient_id == pid)
        .order_by(UrgencyFlag.raised_at)
    )
    flags = [
        {
            "severity": f.severity,
            "flag_type": f.flag_type,
            "status": f.status,
            "raised_at": f.raised_at.isoformat() if f.raised_at else None,
            "trigger_description": f.trigger_description,
        }
        for f in flags_result.scalars().all()
    ]

    # Longitudinal summary
    ls_result = await db.execute(
        select(LongitudinalSummary)
        .where(LongitudinalSummary.patient_id == pid, LongitudinalSummary.is_current == True)
        .order_by(LongitudinalSummary.version_number.desc())
        .limit(1)
    )
    ls = ls_result.scalar_one_or_none()
    longitudinal = {
        "narrative_text": ls.narrative_text,
        "active_concerns_snapshot": ls.active_concerns_snapshot,
        "version_number": ls.version_number,
        "generated_at": ls.generated_at.isoformat() if ls.generated_at else None,
    } if ls else {}

    # Clinician actions
    actions_result = await db.execute(
        select(ClinicianAction)
        .where(ClinicianAction.patient_id == pid)
        .order_by(ClinicianAction.action_at)
    )
    actions = [
        {
            "action_type": a.action_type,
            "action_at": a.action_at.isoformat() if a.action_at else None,
            "notes_text": a.notes_text,
            "probe_instructions": a.probe_instructions,
        }
        for a in actions_result.scalars().all()
    ]

    return {
        "patient": {
            "full_name": patient.full_name,
            "nhs_number": patient.nhs_number,
            "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
            "phone_number": patient.phone_number,
            "postcode": patient.postcode,
            "condition": patient.condition,
            "procedure": patient.procedure,
            "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
            "status": patient.status,
        },
        "profile": {
            "primary_diagnosis": profile.primary_diagnosis,
            "secondary_diagnoses": profile.secondary_diagnoses,
            "current_medications": profile.current_medications,
            "allergies": profile.allergies,
            "consultant_notes": profile.consultant_notes,
            "discharge_summary_text": profile.discharge_summary_text,
        } if profile else None,
        "pathway": pathway,
        "calls": call_data,
        "urgency_flags": flags,
        "longitudinal_summary": longitudinal,
        "clinician_actions": actions,
    }


@router.get("/{patient_id}/report/pdf")
async def download_patient_report(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Generate and stream the patient summary PDF."""
    data = await _gather_report_data(patient_id, db)
    pdf_bytes = build_patient_summary_pdf(data)
    safe_name = data["patient"]["full_name"].replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Sizor_Summary_{safe_name}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.post("/{patient_id}/report/email")
async def email_patient_report(
    patient_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Generate the PDF and email it to the given recipient.
    Body: { "to_email": "gp@surgery.nhs.uk", "recipient_name": "Dr Smith" (optional) }
    """
    to_email = body.get("to_email", "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(400, "A valid to_email is required.")

    data = await _gather_report_data(patient_id, db)
    pdf_bytes = build_patient_summary_pdf(data)

    sender_name = f"Dr {clinician.full_name}" if hasattr(clinician, "full_name") else "Sizor AI Clinician"
    try:
        await send_summary_email(
            to_email=to_email,
            patient_name=data["patient"]["full_name"],
            pdf_bytes=pdf_bytes,
            sender_name=sender_name,
        )
    except ValueError as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Email delivery failed: {exc}")

    return {"status": "sent", "to": to_email}
