from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from ..database import get_db
from ..models import Patient, CallRecord, SOAPNote, UrgencyFlag, FTPRecord, CallSchedule, Ward
from .auth import get_current_clinician

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_active = await db.scalar(
        select(func.count(Patient.patient_id)).where(Patient.status == "active")
    ) or 0
    calls_today = await db.scalar(
        select(func.count(CallRecord.call_id)).where(CallRecord.started_at >= today_start)
    ) or 0
    calls_missed = await db.scalar(
        select(func.count(CallRecord.call_id)).where(
            CallRecord.status == "missed"
        )
    ) or 0

    missed_result = await db.execute(
        select(CallRecord, Patient)
        .join(Patient, CallRecord.patient_id == Patient.patient_id)
        .where(CallRecord.status == "missed")
        .order_by(CallRecord.started_at.desc())
        .limit(50)
    )
    missed_calls = [
        {
            "call_id":      str(r.CallRecord.call_id),
            "patient_id":   str(r.CallRecord.patient_id),
            "patient_name": r.Patient.full_name,
            "condition":    r.Patient.condition,
            "direction":    r.CallRecord.direction,
            "trigger_type": r.CallRecord.trigger_type,
            "day_in_recovery": r.CallRecord.day_in_recovery,
            "started_at":   r.CallRecord.started_at.isoformat() if r.CallRecord.started_at else None,
        }
        for r in missed_result.all()
    ]
    awaiting_review = await db.scalar(
        select(func.count(SOAPNote.soap_id)).where(SOAPNote.clinician_reviewed == False)
    ) or 0
    open_escalations = await db.scalar(
        select(func.count(UrgencyFlag.flag_id)).where(
            UrgencyFlag.status.in_(["open", "reviewing"])
        )
    ) or 0

    patients_result = await db.execute(
        select(Patient, Ward.ward_name, Ward.specialty)
        .outerjoin(Ward, Patient.ward_id == Ward.ward_id)
        .where(Patient.status.in_(["active", "escalated", "monitoring"]))
    )
    patients_rows = patients_result.all()
    patients = [(p, wn, ws) for p, wn, ws in patients_rows]

    worklist = []
    for p, ward_name, ward_specialty in patients:
        call_result = await db.execute(
            select(CallRecord)
            .where(CallRecord.patient_id == p.patient_id)
            .order_by(CallRecord.started_at.desc())
            .limit(1)
        )
        last_call = call_result.scalar_one_or_none()

        flag_result = await db.execute(
            select(UrgencyFlag)
            .where(
                and_(
                    UrgencyFlag.patient_id == p.patient_id,
                    UrgencyFlag.status.in_(["open", "reviewing"]),
                )
            )
            .order_by(UrgencyFlag.raised_at.desc())
            .limit(1)
        )
        flag = flag_result.scalar_one_or_none()

        ftp_result = await db.execute(
            select(FTPRecord)
            .where(FTPRecord.patient_id == p.patient_id)
            .order_by(FTPRecord.assessed_at.desc())
            .limit(1)
        )
        ftp = ftp_result.scalar_one_or_none()

        reviewed = True
        if last_call:
            soap_result = await db.execute(
                select(SOAPNote)
                .where(SOAPNote.call_id == last_call.call_id)
                .order_by(SOAPNote.generated_at.desc())
                .limit(1)
            )
            soap = soap_result.scalar_one_or_none()
            reviewed = soap.clinician_reviewed if soap else True

        next_schedule_result = await db.execute(
            select(CallSchedule)
            .where(CallSchedule.patient_id == p.patient_id, CallSchedule.status == "pending")
            .order_by(CallSchedule.scheduled_for)
            .limit(1)
        )
        next_schedule = next_schedule_result.scalar_one_or_none()

        day = None
        if p.discharge_date:
            day = (datetime.now(timezone.utc).date() - p.discharge_date).days

        severity = flag.severity if flag else "green"
        severity_order = {"red": 0, "amber": 1, "green": 2}

        worklist.append({
            "patient_id": str(p.patient_id),
            "patient_name": p.full_name,
            "nhs_number": p.nhs_number,
            "condition": p.condition,
            "day_in_recovery": day,
            "last_call_at": last_call.started_at.isoformat() if last_call else None,
            "last_call_duration": last_call.duration_seconds if last_call else None,
            "last_call_direction": last_call.direction if last_call else None,
            "next_scheduled_call": next_schedule.scheduled_for.isoformat() if next_schedule else None,
            "ftp_status": ftp.ftp_status if ftp else None,
            "urgency_severity": severity,
            "reviewed": reviewed,
            "severity_order": severity_order.get(severity, 2),
            "ward_name": ward_name,
            "ward_specialty": ward_specialty,
        })

    # Sort: RED unreviewed → AMBER unreviewed → GREEN unreviewed → reviewed by urgency
    worklist.sort(key=lambda x: (1 if x["reviewed"] else 0, x["severity_order"]))

    return {
        "stats": {
            "total_active_patients": total_active,
            "calls_today": calls_today,
            "calls_missed": calls_missed,
            "awaiting_review": awaiting_review,
            "open_escalations": open_escalations,
        },
        "worklist": worklist,
        "missed_calls": missed_calls,
    }
