"""
Internal API — called by the voice agent only (no JWT, uses X-Internal-Key).
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import CallSchedule, Patient
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
