"""
Internal API — called by the voice agent only (no JWT, uses X-Internal-Key).
"""
import uuid
from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from ..database import get_db
from ..models import CallSchedule, Patient, PatientMedicalProfile, CallRecord, SOAPNote, ClinicalExtraction, UrgencyFlag, LongitudinalSummary
from ..config import settings
from ..clinical.pathway_map import OPCS_TO_NICE_MAP
from ..clinical.benchmarks import BENCHMARK_DATA


def _benchmark_for_day(opcs_code: str, domain: str, day: int):
    """
    Return (expected_score, upper_bound, label) from BENCHMARK_DATA for the
    closest call-day to `day`. Returns (None, None, None) if not found.
    """
    domain_data = BENCHMARK_DATA.get(opcs_code, {}).get("domains", {}).get(domain, {})
    if not domain_data:
        return None, None, None
    closest = min(domain_data.keys(), key=lambda d: abs(d - day))
    row = domain_data[closest]
    return row[0], row[1], row[2]  # expected_score, upper_bound, label

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

    out = []
    for s, p in rows:
        # Find the next pending schedule for this patient after the current one
        next_result = await db.execute(
            select(CallSchedule)
            .where(
                CallSchedule.patient_id == p.patient_id,
                CallSchedule.status == "pending",
                CallSchedule.scheduled_for > now,
                CallSchedule.schedule_id != s.schedule_id,
            )
            .order_by(CallSchedule.scheduled_for)
            .limit(1)
        )
        next_sched = next_result.scalar_one_or_none()

        out.append({
            "schedule_id": str(s.schedule_id),
            "patient_id": str(s.patient_id),
            "scheduled_for": s.scheduled_for.isoformat(),
            "call_type": s.call_type,
            "module": s.module,
            "protocol_name": s.protocol_name,
            "probe_instructions": None,
            "patient_name": p.full_name,
            "nhs_number": p.nhs_number,
            "phone_number": p.phone_number,
            "date_of_birth": str(p.date_of_birth) if p.date_of_birth else "",
            "postcode": p.postcode or "",
            "discharge_date": str(p.discharge_date) if p.discharge_date else "",
            "day_in_recovery": (date.today() - p.discharge_date).days if p.discharge_date else None,
            "next_appointment_iso": next_sched.scheduled_for.isoformat() if next_sched else None,
        })
    return out


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

    dt = datetime.fromisoformat(data["scheduled_for"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = CallSchedule(
        patient_id=uuid.UUID(patient_id),
        scheduled_for=dt,
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

    # ── Current day in recovery ──────────────────────────────────────────────
    day_in_recovery = None
    if patient.discharge_date:
        day_in_recovery = (date.today() - patient.discharge_date).days

    # ── Active pathway playbook (always fetch — needed even on first call) ───
    playbook_for_day = None
    opcs_code = None
    pathway_label = None
    red_flags = []

    pw_row = await db.execute(text("""
        SELECT opcs_code, playbook, domains, risk_flags, clinical_red_flags
        FROM patient_pathways
        WHERE patient_id = :pid AND active = true
        LIMIT 1
    """), {"pid": str(patient.patient_id)})
    pw = pw_row.mappings().first()

    risk_flags = []
    custom_domains = []
    if pw:
        opcs_code = pw["opcs_code"]
        pw_meta = OPCS_TO_NICE_MAP.get(opcs_code, {})
        pathway_label = pw_meta.get("label", opcs_code)
        # Use clinician-customised red flags if set, else fall back to pathway map defaults
        red_flags = pw["clinical_red_flags"] or pw_meta.get("red_flags", [])
        risk_flags = pw["risk_flags"] or []
        # Respect clinician-customised domain list; fall back to pathway map
        custom_domains = pw["domains"] or pw_meta.get("monitoring_domains", [])

        if pw["playbook"] and day_in_recovery is not None:
            playbook = pw["playbook"]
            day_keys = sorted(int(k) for k in playbook.keys())
            if day_keys:
                closest = min(day_keys, key=lambda d: abs(d - day_in_recovery))
                playbook_for_day = playbook.get(str(closest)) or {}

        # ALWAYS guarantee a non-null playbook when a pathway is registered.
        # Fill any domain missing from the stored playbook with a template so
        # the voice agent NEVER falls back to the generic assessment script.
        from ..clinical.playbook import _make_template
        playbook_for_day = playbook_for_day or {}
        for _dom in custom_domains:
            if _dom not in playbook_for_day:
                playbook_for_day[_dom] = _make_template(_dom)
        # If still empty (no domains at all configured), add a single catch-all
        # so build_system_prompt always receives a truthy playbook dict.
        if not playbook_for_day:
            playbook_for_day = {"general_recovery": _make_template("general recovery")}

    # ── Medical profile (medications, allergies) ─────────────────────────────
    profile_result = await db.execute(
        select(PatientMedicalProfile).where(PatientMedicalProfile.patient_id == patient.patient_id)
    )
    profile = profile_result.scalar_one_or_none()
    current_medications = profile.current_medications or [] if profile else []
    allergies = profile.allergies or [] if profile else []

    # ── Last 3 completed calls ───────────────────────────────────────────────
    calls_result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == patient.patient_id, CallRecord.status == "completed")
        .order_by(CallRecord.started_at.desc())
        .limit(3)
    )
    recent_calls = calls_result.scalars().all()

    # If no history but pathway exists, return just the playbook context
    if not recent_calls:
        return {
            "has_history": False,
            "day_in_recovery": day_in_recovery,
            "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
            "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
            "postcode": patient.postcode,
            "opcs_code": opcs_code,
            "pathway_label": pathway_label,
            "red_flags": red_flags,
            "risk_flags": risk_flags,
            "current_medications": current_medications,
            "allergies": allergies,
            "playbook": playbook_for_day,
        }

    call_summaries = []
    # domain → latest {day, score, expected, upper_bound, label, above_expected}
    domain_latest: dict[str, dict] = {}

    for call in recent_calls:
        soap_result = await db.execute(
            select(SOAPNote).where(SOAPNote.call_id == call.call_id)
            .order_by(SOAPNote.generated_at.desc()).limit(1)
        )
        soap = soap_result.scalar_one_or_none()

        ext_result = await db.execute(
            select(ClinicalExtraction).where(ClinicalExtraction.call_id == call.call_id)
            .order_by(ClinicalExtraction.extracted_at.desc()).limit(1)
        )
        ext = ext_result.scalar_one_or_none()

        call_day = call.day_in_recovery or 0

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
            # red_flags and concerns live inside condition_specific_flags JSON
            csf = ext.condition_specific_flags or {}
            if csf.get("red_flags"):
                scores["red_flags"] = csf["red_flags"]
            if csf.get("concerns"):
                scores["concerns_noted"] = csf["concerns"]
            if scores:
                summary["scores"] = scores

            # Extract per-domain 0-4 scores and compare to NICE benchmarks
            if opcs_code and ext.condition_specific_flags:
                domain_scores = ext.condition_specific_flags.get("domain_scores", {})
                domain_summary = []
                for domain, score in domain_scores.items():
                    if score is None:
                        continue
                    exp, upper, label = _benchmark_for_day(opcs_code, domain, call_day)
                    above = (upper is not None and score > upper)
                    entry = {
                        "domain": domain,
                        "score": score,
                        "expected": exp,
                        "upper_bound": upper,
                        "label": label,
                        "above_expected": above,
                    }
                    domain_summary.append(entry)
                    # Keep only the most recent entry per domain for priority ranking
                    if domain not in domain_latest:
                        domain_latest[domain] = {**entry, "day": call_day}
                if domain_summary:
                    summary["domain_scores"] = domain_summary

        if summary:
            call_summaries.append(summary)

    # Build domain priority list: above-expected domains first, then by score desc
    # Use the clinician-customised domain list if set, else the pathway map default
    all_pathway_domains = custom_domains or OPCS_TO_NICE_MAP.get(opcs_code or "", {}).get("monitoring_domains", [])
    domain_priority = []
    for domain in all_pathway_domains:
        if domain in domain_latest:
            entry = domain_latest[domain]
            domain_priority.append({
                "domain": domain,
                "last_score": entry["score"],
                "last_day": entry["day"],
                "expected": entry["expected"],
                "upper_bound": entry["upper_bound"],
                "nice_label": entry["label"],
                "above_expected": entry["above_expected"],
                "priority": entry["above_expected"],
            })
        else:
            # No score yet — include as normal priority
            exp, upper, label = _benchmark_for_day(opcs_code or "", domain, day_in_recovery or 1)
            domain_priority.append({
                "domain": domain,
                "last_score": None,
                "last_day": None,
                "expected": exp,
                "upper_bound": upper,
                "nice_label": label,
                "above_expected": False,
                "priority": False,
            })
    # Sort: flagged (above_expected) first, then by last_score desc
    domain_priority.sort(key=lambda x: (not x["priority"], -(x["last_score"] or 0)))

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
        "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
        "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
        "postcode": patient.postcode,
        "call_summaries": call_summaries,
        "open_flags": open_flags,
        "active_concerns": active_concerns,
        "day_in_recovery": day_in_recovery,
        "opcs_code": opcs_code,
        "pathway_label": pathway_label,
        "red_flags": red_flags,
        "risk_flags": risk_flags,
        "current_medications": current_medications,
        "allergies": allergies,
        "playbook": playbook_for_day,
        "domain_priority": domain_priority,
    }
