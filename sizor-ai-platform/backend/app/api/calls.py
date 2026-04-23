import uuid
from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db
from ..models import CallRecord, SOAPNote, ClinicalExtraction, UrgencyFlag, ClinicianAction, Patient, CallSchedule
from .auth import get_current_clinician
from ..tasks.celery_app import celery_app
from ..config import settings

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/ingest")
async def ingest_call_from_voice_agent(
    data: dict,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = Header(default=""),
):
    """
    Called by the voice agent after a call ends.
    No JWT required — uses X-Internal-Key header instead.
    Looks up the patient by patient_id or nhs_number, creates a CallRecord,
    and triggers the post-call processing pipeline via Celery.
    """
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

    # Look up patient
    patient = None
    if data.get("patient_id"):
        result = await db.execute(
            select(Patient).where(Patient.patient_id == uuid.UUID(data["patient_id"]))
        )
        patient = result.scalar_one_or_none()

    if not patient and data.get("nhs_number"):
        result = await db.execute(
            select(Patient).where(Patient.nhs_number == data["nhs_number"])
        )
        patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found — register them in the dashboard first")

    # Calculate day_in_recovery if not provided
    day_in_recovery = data.get("day_in_recovery")
    if day_in_recovery is None and patient.discharge_date:
        day_in_recovery = (date.today() - patient.discharge_date).days

    call_id = data.get("call_id") or str(uuid.uuid4())

    # Check for duplicate
    existing = await db.execute(
        select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id))
    )
    if existing.scalar_one_or_none():
        return {"call_id": call_id, "patient_id": str(patient.patient_id), "status": "already_exists"}

    probe_call_id = data.get("probe_call_id")

    # Determine final call status
    # Agent sends: "missed" for unanswered, "cut_off" for calls that ended unexpectedly mid-session
    transcript = data.get("transcript", "")
    agent_status = data.get("call_status")
    final_status = (
        agent_status
        or ("missed" if not transcript and data.get("duration_seconds", 1) == 0 else "completed")
    )

    call = CallRecord(
        call_id=uuid.UUID(call_id),
        patient_id=patient.patient_id,
        direction=data.get("direction", "outbound"),
        trigger_type=data.get("trigger_type", "scheduled"),
        day_in_recovery=day_in_recovery,
        status=final_status,
        duration_seconds=data.get("duration_seconds"),
        started_at=datetime.now(timezone.utc),
        transcript_raw=transcript,
        call_sid=data.get("call_sid"),
        probe_instructions=data.get("probe_instructions"),
    )
    db.add(call)
    await db.flush()

    # Update the matching dispatched CallSchedule → completed / missed
    # Match by patient + status=dispatched, pick the one closest in time to now
    sched_result = await db.execute(
        select(CallSchedule)
        .where(
            CallSchedule.patient_id == patient.patient_id,
            CallSchedule.status == "dispatched",
        )
        .order_by(CallSchedule.scheduled_for.desc())
        .limit(1)
    )
    dispatched_sched = sched_result.scalar_one_or_none()
    if dispatched_sched:
        dispatched_sched.status = "completed" if final_status == "completed" else "missed"

    # For missed calls: schedule a retry 2 hours later if no pending call already exists
    if final_status == "missed":
        now_utc = datetime.now(timezone.utc)
        retry_window_end = now_utc + timedelta(hours=24)
        existing_pending = (await db.execute(
            select(CallSchedule).where(
                CallSchedule.patient_id == patient.patient_id,
                CallSchedule.status == "pending",
                CallSchedule.scheduled_for > now_utc,
                CallSchedule.scheduled_for < retry_window_end,
            ).limit(1)
        )).scalar_one_or_none()

        if not existing_pending:
            retry_time = now_utc + timedelta(hours=2)
            retry_sched = CallSchedule(
                patient_id=patient.patient_id,
                scheduled_for=retry_time,
                module="post_discharge",
                call_type="retry",
                protocol_name="missed_call_retry",
                status="pending",
            )
            db.add(retry_sched)
            await db.commit()
            await db.refresh(retry_sched)

            celery_app.send_task(
                "fire_scheduled_call",
                args=[str(retry_sched.schedule_id)],
                eta=retry_time,
            )

    await db.commit()

    # Trigger full pipeline (SOAP, extraction, FTP, flags, longitudinal summary)
    # Run for completed AND cut-off calls — partial data is clinically valuable
    if final_status in ("completed", "cut_off") and transcript.strip():
        celery_app.send_task("process_call", args=[call_id])

    # If this is a probe call, update its status and link SOAP note after pipeline
    if probe_call_id:
        celery_app.send_task("link_probe_call", args=[probe_call_id, call_id], countdown=30)

    # For cut-off calls: schedule a continuation call 5 minutes later
    if final_status == "cut_off":
        now_utc = datetime.now(timezone.utc)
        continuation_time = now_utc + timedelta(minutes=5)
        cont_sched = CallSchedule(
            patient_id=patient.patient_id,
            scheduled_for=continuation_time,
            module="post_discharge",
            call_type="continuation",
            protocol_name="cut_off_continuation",
            status="pending",
        )
        db.add(cont_sched)
        await db.commit()
        await db.refresh(cont_sched)

        celery_app.send_task(
            "fire_scheduled_call",
            args=[str(cont_sched.schedule_id)],
            eta=continuation_time,
        )

    return {"call_id": call_id, "patient_id": str(patient.patient_id), "status": final_status}


@router.get("/{call_id}")
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id))
    )
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call not found")

    soap_result = await db.execute(select(SOAPNote).where(SOAPNote.call_id == call.call_id))
    soap = soap_result.scalar_one_or_none()

    ext_result = await db.execute(
        select(ClinicalExtraction).where(ClinicalExtraction.call_id == call.call_id)
    )
    extraction = ext_result.scalar_one_or_none()

    flags_result = await db.execute(
        select(UrgencyFlag).where(UrgencyFlag.call_id == call.call_id)
    )
    flags = flags_result.scalars().all()

    return {
        "call_id": str(call.call_id),
        "patient_id": str(call.patient_id),
        "direction": call.direction,
        "trigger_type": call.trigger_type,
        "day_in_recovery": call.day_in_recovery,
        "status": call.status,
        "duration_seconds": call.duration_seconds,
        "started_at": call.started_at.isoformat(),
        "transcript_raw": call.transcript_raw,
        "probe_instructions": call.probe_instructions,
        "soap_note": {
            "soap_id": str(soap.soap_id),
            "subjective": soap.subjective,
            "objective": soap.objective,
            "assessment": soap.assessment,
            "plan": soap.plan,
            "clinician_reviewed": soap.clinician_reviewed,
            "clinician_edited": soap.clinician_edited,
            "model_used": soap.model_used,
            "generated_at": soap.generated_at.isoformat(),
        } if soap else None,
        "extraction": {
            "pain_score": extraction.pain_score,
            "breathlessness_score": extraction.breathlessness_score,
            "mobility_score": extraction.mobility_score,
            "appetite_score": extraction.appetite_score,
            "mood_score": extraction.mood_score,
            "medication_adherence": extraction.medication_adherence,
            "condition_specific_flags": extraction.condition_specific_flags,
        } if extraction else None,
        "urgency_flags": [
            {
                "flag_id": str(f.flag_id),
                "severity": f.severity,
                "flag_type": f.flag_type,
                "trigger_description": f.trigger_description,
                "status": f.status,
                "raised_at": f.raised_at.isoformat(),
            }
            for f in flags
        ],
    }


@router.post("/{call_id}/process")
async def process_call_endpoint(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id)))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call not found")
    if call.status in ("missed", "no_answer"):
        raise HTTPException(400, "Cannot process a call that did not connect")
    if not (call.transcript_raw or "").strip():
        raise HTTPException(400, "No transcript available — call may not have connected")
    celery_app.send_task("process_call", args=[call_id])
    return {"status": "processing", "call_id": call_id}


@router.post("/{call_id}/review")
async def review_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(select(SOAPNote).where(SOAPNote.call_id == uuid.UUID(call_id)))
    soap = result.scalar_one_or_none()
    if soap:
        soap.clinician_reviewed = True

    flags_result = await db.execute(
        select(UrgencyFlag).where(UrgencyFlag.call_id == uuid.UUID(call_id))
    )
    for flag in flags_result.scalars().all():
        if flag.status == "open":
            flag.status = "reviewing"

    call_result = await db.execute(
        select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id))
    )
    call = call_result.scalar_one_or_none()
    if call:
        action = ClinicianAction(
            patient_id=call.patient_id,
            call_id=call.call_id,
            clinician_id=clinician.clinician_id,
            action_type="reviewed",
        )
        db.add(action)

    await db.commit()
    return {
        "status": "reviewed",
        "reviewed_by": clinician.full_name,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{call_id}/flag")
async def raise_flag(
    call_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    call_result = await db.execute(
        select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id))
    )
    call = call_result.scalar_one_or_none()
    if not call:
        raise HTTPException(404, "Call not found")

    flag = UrgencyFlag(
        patient_id=call.patient_id,
        call_id=call.call_id,
        severity=data["severity"],
        flag_type=data["flag_type"],
        trigger_description=data["trigger_description"],
    )
    action = ClinicianAction(
        patient_id=call.patient_id,
        call_id=call.call_id,
        clinician_id=clinician.clinician_id,
        action_type="flag_raised",
        notes_text=data["trigger_description"],
    )
    db.add(flag)
    db.add(action)
    await db.commit()
    return {"flag_id": str(flag.flag_id)}
