import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from ..database import get_db
from ..models import (
    Patient, PatientMedicalProfile, ClinicalExtraction, CallRecord,
    UrgencyFlag, FTPRecord, ClinicianAction, LongitudinalSummary, CallSchedule,
    ClinicalDecision, SOAPNote, Clinician, Ward,
)
from .auth import get_current_clinician
from ..services.nice_guidelines import get_guidelines_for_condition
from ..services.ftp_service import interpolate_expected
from ..config import settings
from ..clinical_intelligence.pathway_map import OPCS_TO_NICE_MAP

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/wards")
async def list_wards(
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Return all wards for the clinician's hospital."""
    result = await db.execute(
        select(Ward).where(Ward.hospital_id == clinician.hospital_id).order_by(Ward.ward_name)
    )
    wards = result.scalars().all()
    return [{"ward_id": str(w.ward_id), "ward_name": w.ward_name, "specialty": w.specialty} for w in wards]


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
        "preferred_call_time": p.preferred_call_time.strftime("%H:%M") if p.preferred_call_time else None,
        "postcode": p.postcode,
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
    result = await db.execute(
        select(Patient, Ward.ward_name, Ward.specialty)
        .outerjoin(Ward, Patient.ward_id == Ward.ward_id)
        .order_by(Patient.created_at.desc())
    )
    rows = result.all()
    out = []
    for p, ward_name, ward_specialty in rows:
        day = None
        if p.discharge_date:
            day = (datetime.now(timezone.utc).date() - p.discharge_date).days
        d = _patient_dict(p, day)
        d["ward_name"] = ward_name
        d["ward_specialty"] = ward_specialty
        out.append(d)
    return out


@router.post("")
async def create_patient(
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    from datetime import date as date_type
    import uuid as uuid_mod

    profile_data = data.pop("medical_profile", None)

    # Coerce date strings → date objects
    for field in ("date_of_birth", "discharge_date", "admission_date"):
        val = data.get(field)
        if val and isinstance(val, str):
            try:
                data[field] = date_type.fromisoformat(val)
            except ValueError:
                data.pop(field, None)

    # Coerce hospital_id / ward_id strings → UUID objects
    for field in ("hospital_id", "ward_id", "assigned_clinician_id"):
        val = data.get(field)
        if val and isinstance(val, str):
            try:
                data[field] = uuid_mod.UUID(val)
            except ValueError:
                data.pop(field, None)

    # Only pass fields that exist on the model
    allowed = {c.key for c in Patient.__table__.columns}
    data = {k: v for k, v in data.items() if k in allowed}

    if not data.get("hospital_id"):
        data["hospital_id"] = clinician.hospital_id

    try:
        patient = Patient(**data)
        db.add(patient)
        await db.flush()
        if profile_data:
            profile = PatientMedicalProfile(patient_id=patient.patient_id, **profile_data)
            db.add(profile)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    return {"patient_id": str(patient.patient_id)}


@router.get("/clinicians-list")
async def list_clinicians(
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Return all clinicians in the same hospital (excluding self)."""
    result = await db.execute(
        select(Clinician).where(
            Clinician.hospital_id == clinician.hospital_id,
            Clinician.clinician_id != clinician.clinician_id,
        ).order_by(Clinician.full_name)
    )
    rows = result.scalars().all()
    return [
        {
            "clinician_id": str(r.clinician_id),
            "full_name": r.full_name,
            "role": r.role,
            "email": r.email,
        }
        for r in rows
    ]


@router.get("/escalations/inbox")
async def escalations_inbox(
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Return clinician-escalated flags assigned to the current user."""
    result = await db.execute(
        select(UrgencyFlag).where(
            UrgencyFlag.assigned_to_clinician_id == clinician.clinician_id,
            UrgencyFlag.flag_type == "clinician_escalation",
        ).order_by(UrgencyFlag.raised_at.desc())
    )
    flags = result.scalars().all()

    out = []
    for f in flags:
        p_result = await db.execute(select(Patient).where(Patient.patient_id == f.patient_id))
        patient = p_result.scalar_one_or_none()
        sender_name = None
        if f.raised_by_clinician_id:
            s_result = await db.execute(select(Clinician).where(Clinician.clinician_id == f.raised_by_clinician_id))
            sender = s_result.scalar_one_or_none()
            if sender:
                sender_name = sender.full_name
        out.append({
            "flag_id": str(f.flag_id),
            "patient_id": str(f.patient_id),
            "patient_name": patient.full_name if patient else "Unknown",
            "condition": patient.condition if patient else None,
            "severity": f.severity,
            "note": f.trigger_description,
            "from_clinician": sender_name,
            "raised_at": f.raised_at.isoformat() if f.raised_at else None,
            "status": f.status,
            "resolution_notes": f.resolution_notes,
        })
    return out


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
        .order_by(LongitudinalSummary.version_number.desc())
        .limit(1)
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

    # Two most recent extractions — latest for score, second for delta
    latest_ext_result = await db.execute(
        select(ClinicalExtraction)
        .where(ClinicalExtraction.patient_id == patient.patient_id)
        .order_by(ClinicalExtraction.extracted_at.desc())
        .limit(2)
    )
    ext_rows = latest_ext_result.scalars().all()
    latest_ext = ext_rows[0] if ext_rows else None
    prior_ext  = ext_rows[1] if len(ext_rows) > 1 else None

    # Domain scores — find the most recent extraction that has non-empty domain_scores.
    # The latest call might have empty domain_scores if the LLM found nothing new to score,
    # so we walk back through extractions to surface the most recently assessed state.
    domain_scores_result = await db.execute(
        select(ClinicalExtraction)
        .where(ClinicalExtraction.patient_id == patient.patient_id)
        .order_by(ClinicalExtraction.extracted_at.desc())
        .limit(10)
    )
    _domain_scores = None
    for _ext in domain_scores_result.scalars().all():
        _ds = (_ext.condition_specific_flags or {}).get("domain_scores")
        if _ds:
            _domain_scores = _ds
            break

    out = _patient_dict(patient, day)
    out["urgency_severity"] = latest_flag.severity if latest_flag else "green"
    out["risk_score"] = latest_ext.risk_score if latest_ext else None
    out["risk_score_band"] = (
        latest_ext.risk_score_breakdown.get("band_if_computed")
        if latest_ext and latest_ext.risk_score_breakdown else None
    )
    out["risk_score_breakdown"] = latest_ext.risk_score_breakdown if latest_ext else None
    out["domain_scores"] = _domain_scores
    out["risk_score_delta"] = (
        round(latest_ext.risk_score - prior_ext.risk_score, 1)
        if latest_ext and prior_ext
        and latest_ext.risk_score is not None
        and prior_ext.risk_score is not None
        else None
    )
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


@router.get("/{patient_id}/pathway-details")
async def get_pathway_details(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Return editable pathway fields: domains, risk_flags, clinical_red_flags."""
    pw_row = await db.execute(text("""
        SELECT opcs_code, domains, risk_flags, clinical_red_flags
        FROM patient_pathways
        WHERE patient_id = :pid AND active = true
        LIMIT 1
    """), {"pid": patient_id})
    pw = pw_row.mappings().first()
    if not pw:
        raise HTTPException(404, "Pathway not found")
    pw_meta = OPCS_TO_NICE_MAP.get(pw["opcs_code"], {})
    return {
        "opcs_code": pw["opcs_code"],
        "pathway_label": pw_meta.get("label", pw["opcs_code"]),
        "domains": pw["domains"] or [],
        "risk_flags": pw["risk_flags"] or [],
        "clinical_red_flags": pw["clinical_red_flags"] or [],
    }


@router.patch("/{patient_id}/pathway")
async def update_pathway(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Update editable pathway fields: domains, risk_flags, clinical_red_flags.
    When domains or clinical_red_flags change the playbook is regenerated in the
    background so call scripts stay aligned with the active domain/flag set.
    """
    updates = []
    params: dict = {"pid": patient_id}
    if "domains" in data:
        updates.append("domains = :domains")
        params["domains"] = data["domains"]
    if "risk_flags" in data:
        updates.append("risk_flags = :risk_flags")
        params["risk_flags"] = data["risk_flags"]
    if "clinical_red_flags" in data:
        updates.append("clinical_red_flags = :clinical_red_flags")
        params["clinical_red_flags"] = data["clinical_red_flags"]
    if not updates:
        return {"status": "ok"}
    await db.execute(
        text(f"UPDATE patient_pathways SET {', '.join(updates)} WHERE patient_id = :pid AND active = true"),
        params,
    )
    await db.commit()

    # Regenerate playbook when the domain list or red flags change so call
    # scripts stay aligned with the updated configuration.
    if "domains" in data or "clinical_red_flags" in data:
        pw_row = await db.execute(text("""
            SELECT opcs_code, domains, clinical_red_flags
            FROM patient_pathways
            WHERE patient_id = :pid AND active = true
            LIMIT 1
        """), {"pid": patient_id})
        pw = pw_row.mappings().first()
        if pw and pw["opcs_code"] and OPCS_TO_NICE_MAP.get(pw["opcs_code"]):
            _pid = patient_id
            _opcs = pw["opcs_code"]
            _pathway = OPCS_TO_NICE_MAP[_opcs]
            _domains = pw["domains"] or _pathway["monitoring_domains"]
            _red_flags = pw["clinical_red_flags"] or _pathway.get("red_flags", [])

            async def _regen_playbook():
                import logging as _logging
                _log = _logging.getLogger(__name__)
                try:
                    from ..clinical.playbook import generate_playbook
                    from ..services.llm_client import LLMClient
                    from ..services.rag_service import retrieve_nice_context
                    from ..models import DomainBenchmark
                    from ..database import AsyncSessionLocal
                    async with AsyncSessionLocal() as session:
                        bench_result = await session.execute(
                            select(DomainBenchmark).where(DomainBenchmark.opcs_code == _opcs)
                        )
                        bench_rows = bench_result.scalars().all()
                        rag_chunks = await retrieve_nice_context(
                            session,
                            nice_ids=_pathway["nice_ids"],
                            query=f"{_pathway['label']} post-discharge recovery monitoring",
                            n=6,
                        )
                        pb = await generate_playbook(
                            opcs_code=_opcs,
                            pathway_label=_pathway["label"],
                            category=_pathway["category"],
                            domains=_domains,
                            call_days=_pathway["call_days"],
                            risk_flags=_red_flags,
                            llm_client=LLMClient(),
                            benchmark_rows=bench_rows,
                            rag_chunks=rag_chunks,
                            pathway_nice_ids=_pathway["nice_ids"],
                            pathway_red_flags=_pathway.get("red_flags", []),
                        )
                        await session.execute(text("""
                            UPDATE patient_pathways
                            SET playbook = cast(:playbook as jsonb)
                            WHERE patient_id = :patient_id AND opcs_code = :opcs_code
                        """), {
                            "playbook": __import__("json").dumps(pb),
                            "patient_id": _pid,
                            "opcs_code": _opcs,
                        })
                        await session.commit()
                        _log.info("Playbook regenerated for patient %s after pathway update", _pid)
                except Exception as exc:
                    _logging.getLogger(__name__).error(
                        "Playbook regen failed for patient %s: %s", _pid, exc, exc_info=True
                    )

            import asyncio
            asyncio.ensure_future(_regen_playbook())

    return {"status": "ok"}


# Maps generic extraction field names → pathway domain names they represent
_EXTRACTION_TO_PATHWAY_DOMAINS: dict[str, list[str]] = {
    "pain": [
        "pain_management", "chest_pain_monitoring", "chest_pain_recurrence",
    ],
    "mobility": [
        "mobility_progress", "mobility_and_rehabilitation", "mobility_and_fatigue",
        "mobility", "rehabilitation_attendance",
    ],
    "breathlessness": [
        "breathlessness", "breathlessness_score", "breathlessness_and_cough",
        "breathlessness_recovery", "activity_tolerance", "activity_progression",
    ],
    "mood": [
        "mood_and_depression", "mood_and_anxiety", "postnatal_depression_screen",
        "mood_and_post_stroke_depression", "mood_and_psychological_state",
        "mood_and_mental_state", "psychological_impact",
    ],
    "appetite": [
        "diet_and_nutrition", "diet_and_digestion",
    ],
    "adherence": [
        "medication_adherence", "antiplatelet_adherence", "anticoagulation_adherence",
        "lmwh_adherence", "inhaler_adherence_and_technique",
        "insulin_or_medication_adherence", "antipsychotic_adherence",
        "medication_concordance",
    ],
}


@router.get("/{patient_id}/scores")
async def get_patient_scores(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Returns per-domain actual scores for a patient with full call metadata for chart tooltips.
    Primary source: condition_specific_flags.domain_scores (real 0-4 LLM-extracted values).
    Fallback: generic field mapping from 0-10 scores.
    Response: { domain: [{ day, score, ftp_flag, call_id, date, assessment, subjective, ftp_status }] }
    """
    result = await db.execute(
        select(ClinicalExtraction, CallRecord, FTPRecord, SOAPNote)
        .join(CallRecord, ClinicalExtraction.call_id == CallRecord.call_id)
        .outerjoin(FTPRecord, FTPRecord.call_id == ClinicalExtraction.call_id)
        .outerjoin(SOAPNote, SOAPNote.call_id == ClinicalExtraction.call_id)
        .where(ClinicalExtraction.patient_id == uuid.UUID(patient_id))
        .order_by(CallRecord.day_in_recovery, ClinicalExtraction.extracted_at)
    )
    rows = result.all()

    # Deduplicate: keep the latest extraction per call_id
    seen: dict[str, tuple] = {}
    for ext, call, ftp, soap in rows:
        cid = str(call.call_id)
        if cid not in seen:
            seen[cid] = (ext, call, ftp, soap)

    grouped: dict[str, list] = {}
    for cid, (ext, call, ftp, soap) in seen.items():
        day = call.day_in_recovery or 0
        variance = (ftp.variance_per_domain or {}) if ftp else {}
        ftp_status = ftp.ftp_status if ftp else None

        meta = {
            "call_id":    str(call.call_id),
            "date":       call.started_at.isoformat() if call.started_at else None,
            "assessment": (soap.assessment or "")[:220] if soap else None,
            "subjective": (soap.subjective or "")[:220] if soap else None,
            "ftp_status": ftp_status,
        }

        # Primary: use domain_scores from condition_specific_flags (real 0-4 values)
        domain_scores: dict = {}
        if ext.condition_specific_flags:
            domain_scores = ext.condition_specific_flags.get("domain_scores", {}) or {}

        if domain_scores:
            for domain, score in domain_scores.items():
                if score is None:
                    continue
                score = max(0, min(4, int(round(score))))
                ftp_flag = bool(variance.get(domain, {}).get("worse", False))
                grouped.setdefault(domain, []).append({
                    "day": day, "score": score, "ftp_flag": ftp_flag, **meta,
                })
        else:
            # Fallback: convert 0-10 generic scores to 0-4 pathway domains
            raw: dict[str, float | None] = {
                "pain":           ext.pain_score,
                "mobility":       ext.mobility_score,
                "breathlessness": ext.breathlessness_score,
                "mood":           ext.mood_score,
                "appetite":       ext.appetite_score,
            }
            if ext.medication_adherence is not None:
                raw["adherence"] = 0.0 if ext.medication_adherence else 3.0

            from ..clinical_intelligence.scoring import score_0_10_to_0_4
            for generic, val in raw.items():
                if val is None:
                    continue
                score = int(val) if generic == "adherence" else score_0_10_to_0_4(val)
                ftp_flag = bool(variance.get(generic, {}).get("worse", False))
                for pathway_domain in _EXTRACTION_TO_PATHWAY_DOMAINS.get(generic, []):
                    grouped.setdefault(pathway_domain, []).append({
                        "day": day, "score": score, "ftp_flag": ftp_flag, **meta,
                    })

    return grouped


@router.get("/{patient_id}/risk-history")
async def get_risk_history(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Returns per-call risk scores ordered chronologically.
    Used to render the risk score history sparkline on the patient detail page.
    """
    result = await db.execute(
        select(ClinicalExtraction, CallRecord)
        .join(CallRecord, ClinicalExtraction.call_id == CallRecord.call_id)
        .where(
            ClinicalExtraction.patient_id == uuid.UUID(patient_id),
            ClinicalExtraction.risk_score.is_not(None),
        )
        .order_by(CallRecord.started_at)
    )
    rows = result.all()

    # Deduplicate: one entry per call (take the row with the highest risk_score
    # if multiple extractions exist for the same call — shouldn't happen but safe)
    seen: dict[str, dict] = {}
    for ext, call in rows:
        cid = str(call.call_id)
        entry = {
            "call_id": cid,
            "date": call.started_at.isoformat() if call.started_at else None,
            "day_in_recovery": call.day_in_recovery,
            "risk_score": ext.risk_score,
            "band": (
                ext.risk_score_breakdown.get("band_if_computed")
                if ext.risk_score_breakdown else None
            ),
            "dominant_driver": (
                ext.risk_score_breakdown.get("dominant_driver")
                if ext.risk_score_breakdown else None
            ),
        }
        if cid not in seen or ext.risk_score > seen[cid]["risk_score"]:
            seen[cid] = entry

    return list(seen.values())


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


@router.get("/{patient_id}/pathway-info")
async def get_pathway_info(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Return the registered pathway details for the scheduler:
    opcs_code, pathway_label, call_days, discharge_date, default_call_time.
    """
    patient_result = await db.execute(
        select(Patient).where(Patient.patient_id == uuid.UUID(patient_id))
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    pw_row = await db.execute(text("""
        SELECT opcs_code, call_schedule
        FROM patient_pathways
        WHERE patient_id = :pid AND active = true
        LIMIT 1
    """), {"pid": str(patient.patient_id)})
    pw = pw_row.mappings().first()

    if not pw:
        return {"has_pathway": False}

    from ..clinical_intelligence.pathway_map import OPCS_TO_NICE_MAP
    opcs_code = pw["opcs_code"]
    pw_meta = OPCS_TO_NICE_MAP.get(opcs_code, {})

    # call_schedule is [{day, scheduled_for, call_number}] stored at registration
    call_schedule = pw["call_schedule"] or []
    call_days = [entry["day"] for entry in call_schedule if "day" in entry]
    if not call_days:
        call_days = pw_meta.get("call_days", [])

    return {
        "has_pathway": True,
        "opcs_code": opcs_code,
        "pathway_label": pw_meta.get("label", opcs_code),
        "call_days": call_days,
        "discharge_date": str(patient.discharge_date) if patient.discharge_date else None,
        "default_call_time": patient.preferred_call_time or "10:00",
        "module": pw_meta.get("category", "post_discharge"),
    }


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
            "protocol_name": s.protocol_name,
            "status": s.status,
            "call_number": s.day_in_recovery_target,
            "created_at": s.created_at.isoformat(),
        }
        for s in items
    ]


@router.get("/{patient_id}/call-prompt")
async def get_call_prompt(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Return structured call-prompt data for the next scheduled call:
    pathway info, playbook for the next call day, domain priority list
    with NICE benchmark comparisons, and red flags.
    """
    from datetime import date
    from ..clinical_intelligence.benchmarks import BENCHMARK_DATA

    patient_result = await db.execute(
        select(Patient).where(Patient.patient_id == uuid.UUID(patient_id))
    )
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    day_in_recovery = (date.today() - patient.discharge_date).days if patient.discharge_date else None

    # Active pathway
    pw_row = await db.execute(text("""
        SELECT opcs_code, playbook, domains, risk_flags
        FROM patient_pathways
        WHERE patient_id = :pid AND active = true
        LIMIT 1
    """), {"pid": str(patient.patient_id)})
    pw = pw_row.mappings().first()

    if not pw:
        return {"has_pathway": False}

    opcs_code = pw["opcs_code"]
    pw_meta = OPCS_TO_NICE_MAP.get(opcs_code, {})
    pathway_label = pw_meta.get("label", opcs_code)
    nice_ids = pw_meta.get("nice_ids", [])
    red_flags = pw_meta.get("red_flags", [])
    all_domains = pw.get("domains") or pw_meta.get("monitoring_domains", [])

    # Playbook for next call day
    playbook_for_day = None
    next_day = day_in_recovery
    raw_playbook = pw.get("playbook")
    if raw_playbook and day_in_recovery is not None:
        day_keys = sorted(int(k) for k in raw_playbook.keys())
        if day_keys:
            # Next call day = next key after today, or today's
            future = [d for d in day_keys if d >= day_in_recovery]
            closest_key = future[0] if future else max(day_keys)
            next_day = closest_key
            playbook_for_day = raw_playbook.get(str(closest_key))

    # Latest domain scores from most recent completed call
    from ..models import ClinicalExtraction
    recent_call_result = await db.execute(
        select(CallRecord)
        .where(CallRecord.patient_id == patient.patient_id, CallRecord.status == "completed")
        .order_by(CallRecord.started_at.desc())
        .limit(1)
    )
    recent_call = recent_call_result.scalar_one_or_none()

    domain_latest: dict[str, dict] = {}
    if recent_call:
        ext_result = await db.execute(
            select(ClinicalExtraction).where(ClinicalExtraction.call_id == recent_call.call_id)
            .order_by(ClinicalExtraction.extracted_at.desc()).limit(1)
        )
        ext = ext_result.scalar_one_or_none()
        if ext and ext.condition_specific_flags:
            domain_scores = ext.condition_specific_flags.get("domain_scores", {})
            call_day = recent_call.day_in_recovery or 0
            for domain, score in domain_scores.items():
                if score is None:
                    continue
                domain_data = BENCHMARK_DATA.get(opcs_code, {}).get("domains", {}).get(domain, {})
                exp, upper, label = None, None, None
                if domain_data:
                    closest = min(domain_data.keys(), key=lambda d: abs(d - call_day))
                    row = domain_data[closest]
                    exp, upper, label = row[0], row[1], row[2]
                above = upper is not None and score > upper
                domain_latest[domain] = {
                    "score": score, "day": call_day,
                    "expected": exp, "upper_bound": upper,
                    "label": label, "above_expected": above,
                }

    # Build domain priority list
    def _bench(domain, day):
        domain_data = BENCHMARK_DATA.get(opcs_code, {}).get("domains", {}).get(domain, {})
        if not domain_data:
            return None, None, None
        closest = min(domain_data.keys(), key=lambda d: abs(d - day))
        row = domain_data[closest]
        return row[0], row[1], row[2]

    domain_priority = []
    for domain in all_domains:
        if domain in domain_latest:
            e = domain_latest[domain]
            domain_priority.append({
                "domain": domain,
                "last_score": e["score"],
                "last_day": e["day"],
                "expected": e["expected"],
                "upper_bound": e["upper_bound"],
                "nice_label": e["label"],
                "above_expected": e["above_expected"],
                "priority": e["above_expected"],
            })
        else:
            exp, upper, label = _bench(domain, day_in_recovery or 1)
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
    domain_priority.sort(key=lambda x: (not x["priority"], -(x["last_score"] or 0)))

    return {
        "has_pathway": True,
        "pathway_label": pathway_label,
        "opcs_code": opcs_code,
        "nice_ids": nice_ids,
        "red_flags": red_flags,
        "day_in_recovery": day_in_recovery,
        "next_call_day": next_day,
        "playbook": playbook_for_day,
        "domain_priority": domain_priority,
    }


@router.post("/{patient_id}/schedule")
async def add_schedule(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    if "scheduled_for" in data and isinstance(data["scheduled_for"], str):
        dt = datetime.fromisoformat(data["scheduled_for"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        data["scheduled_for"] = dt
    s = CallSchedule(patient_id=uuid.UUID(patient_id), **data)
    db.add(s)
    await db.commit()

    # Enqueue Celery task to fire the call — ETA fires it at the exact time,
    # past times fire immediately (within seconds).
    from ..tasks.celery_app import celery_app
    eta = data["scheduled_for"] if "scheduled_for" in data else None
    if eta:
        celery_app.send_task("fire_scheduled_call", args=[str(s.schedule_id)], eta=eta)

    return {"schedule_id": str(s.schedule_id)}


@router.post("/{patient_id}/schedule/bulk")
async def bulk_create_schedule(
    patient_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Create multiple scheduled calls at once from a template.
    Expects { protocol_name, module, items: [{scheduled_for, call_number, notes}] }
    Enqueues a Celery ETA task for each.
    """
    from ..tasks.celery_app import celery_app

    items = data.get("items", [])
    protocol_name = data.get("protocol_name", "standard")
    module = data.get("module", "post_discharge")
    created = []

    for item in items:
        raw_dt = item.get("scheduled_for", "")
        dt = datetime.fromisoformat(raw_dt)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        s = CallSchedule(
            patient_id=uuid.UUID(patient_id),
            scheduled_for=dt,
            module=module,
            call_type="routine",
            protocol_name=protocol_name,
            day_in_recovery_target=item.get("call_number"),
            status="pending",
        )
        db.add(s)
        await db.flush()  # get schedule_id without full commit
        celery_app.send_task("fire_scheduled_call", args=[str(s.schedule_id)], eta=dt)
        created.append(str(s.schedule_id))

    await db.commit()
    return {"created": len(created), "schedule_ids": created}


@router.patch("/{patient_id}/schedule/{schedule_id}")
async def update_schedule(
    patient_id: str,
    schedule_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Reschedule or cancel a single call.
    Accepts { scheduled_for?, status? }
    If rescheduled, re-enqueues the Celery task.
    """
    from ..tasks.celery_app import celery_app

    result = await db.execute(
        select(CallSchedule).where(
            CallSchedule.schedule_id == uuid.UUID(schedule_id),
            CallSchedule.patient_id == uuid.UUID(patient_id),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Schedule not found")

    if "scheduled_for" in data:
        dt = datetime.fromisoformat(data["scheduled_for"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        s.scheduled_for = dt
        if s.status == "pending":
            celery_app.send_task("fire_scheduled_call", args=[str(s.schedule_id)], eta=dt)

    if "status" in data:
        s.status = data["status"]

    if "notes" in data:
        # store notes in protocol_name field for now (no separate column)
        pass

    await db.commit()
    return {"schedule_id": schedule_id, "status": s.status, "scheduled_for": s.scheduled_for.isoformat()}


@router.delete("/{patient_id}/schedule/{schedule_id}")
async def delete_schedule(
    patient_id: str,
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(
        select(CallSchedule).where(
            CallSchedule.schedule_id == uuid.UUID(schedule_id),
            CallSchedule.patient_id == uuid.UUID(patient_id),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Schedule not found")
    await db.delete(s)
    await db.commit()
    return {"deleted": schedule_id}


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


@router.get("/{patient_id}/notes")
async def get_patient_notes(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """Return all manually added clinician notes for a patient."""
    result = await db.execute(
        select(ClinicianAction, Clinician)
        .join(Clinician, ClinicianAction.clinician_id == Clinician.clinician_id)
        .where(
            ClinicianAction.patient_id == uuid.UUID(patient_id),
            ClinicianAction.action_type == "note_added",
        )
        .order_by(ClinicianAction.action_at.desc())
    )
    rows = result.all()
    return [
        {
            "action_id":    str(r.ClinicianAction.action_id),
            "notes_text":   r.ClinicianAction.notes_text,
            "action_at":    r.ClinicianAction.action_at.isoformat() if r.ClinicianAction.action_at else None,
            "clinician_name": r.Clinician.full_name,
            "clinician_role": r.Clinician.role,
        }
        for r in rows
    ]


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
    to_clinician_id = data.get("to_clinician_id")
    notes = data.get("notes") or data.get("reason") or "Escalation raised"

    action = ClinicianAction(
        patient_id=uuid.UUID(patient_id),
        clinician_id=clinician.clinician_id,
        action_type="escalated",
        notes_text=notes,
    )
    db.add(action)

    # Create an urgency flag directed at the target clinician
    if to_clinician_id:
        flag = UrgencyFlag(
            patient_id=uuid.UUID(patient_id),
            severity="amber",
            flag_type="clinician_escalation",
            trigger_description=notes,
            status="open",
            assigned_to_clinician_id=uuid.UUID(to_clinician_id),
            raised_by_clinician_id=clinician.clinician_id,
        )
        db.add(flag)

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


@router.post("/pathway-register")
async def pathway_register(
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Register a patient with a full OPCS-linked clinical pathway.
    Creates the patient record and a patient_pathways entry with a computed
    call schedule. Triggers async playbook generation (fire and forget).

    Body fields:
        nhs_number, name, date_of_birth, discharge_date,
        opcs_code, risk_flags, ward, consultant
    """
    from datetime import date as date_type
    import asyncio

    opcs_code = data.get("opcs_code", "").strip()
    if opcs_code not in OPCS_TO_NICE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"OPCS code '{opcs_code}' not found in pathway map. "
                   f"Valid codes: {', '.join(sorted(OPCS_TO_NICE_MAP.keys()))}",
        )

    pathway = OPCS_TO_NICE_MAP[opcs_code]

    # Parse dates
    discharge_date_str = data.get("discharge_date")
    if not discharge_date_str:
        raise HTTPException(status_code=400, detail="discharge_date is required")
    try:
        discharge_date = date_type.fromisoformat(discharge_date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid discharge_date format (use YYYY-MM-DD)")

    monitoring_ends = discharge_date + timedelta(days=pathway["monitoring_window_days"])

    # Compute call schedule
    call_schedule = [
        {
            "date": (discharge_date + timedelta(days=day)).isoformat(),
            "day": day,
            "status": "scheduled",
        }
        for day in pathway["call_days"]
    ]

    # Validate required fields
    nhs_number = data.get("nhs_number", "").strip()
    full_name = data.get("name", "").strip()
    if not nhs_number or not full_name:
        raise HTTPException(status_code=400, detail="nhs_number and name are required")

    # Parse date_of_birth
    dob = None
    dob_str = data.get("date_of_birth")
    if dob_str:
        try:
            dob = date_type.fromisoformat(dob_str)
        except ValueError:
            pass

    # Parse preferred_call_time
    from datetime import time as time_type
    preferred_call_time = None
    pct_str = data.get("preferred_call_time", "").strip()
    if pct_str:
        try:
            preferred_call_time = time_type.fromisoformat(pct_str)
        except ValueError:
            pass

    # Create or update patient
    existing = await db.execute(select(Patient).where(Patient.nhs_number == nhs_number))
    patient = existing.scalar_one_or_none()
    if patient is None:
        patient = Patient(
            hospital_id=clinician.hospital_id,
            nhs_number=nhs_number,
            full_name=full_name,
            date_of_birth=dob,
            discharge_date=discharge_date,
            phone_number=data.get("phone_number", ""),
            condition=pathway["label"],
            procedure=opcs_code,
            program_module="post_discharge",
            status="active",
            preferred_call_time=preferred_call_time,
            postcode=data.get("postcode", "").strip().upper() or None,
        )
        db.add(patient)
        try:
            await db.flush()
        except Exception as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        patient.discharge_date = discharge_date
        patient.condition = pathway["label"]
        patient.procedure = opcs_code
        if preferred_call_time:
            patient.preferred_call_time = preferred_call_time

    risk_flags = data.get("risk_flags", [])
    custom_domains = data.get("domains", pathway["monitoring_domains"])
    clinical_red_flags = data.get("clinical_red_flags", pathway.get("red_flags", []))

    # Insert patient_pathways row using raw SQL (table may not have ORM model)
    try:
        await db.execute(text("""
            INSERT INTO patient_pathways
                (patient_id, opcs_code, pathway_slug, nice_ids, domains, risk_flags,
                 clinical_red_flags, discharge_date, monitoring_ends, call_schedule, active)
            VALUES
                (:patient_id, :opcs_code, :pathway_slug, :nice_ids, :domains, :risk_flags,
                 :clinical_red_flags, :discharge_date, :monitoring_ends, cast(:call_schedule as jsonb), true)
            ON CONFLICT (patient_id, opcs_code) DO UPDATE
                SET discharge_date = EXCLUDED.discharge_date,
                    monitoring_ends = EXCLUDED.monitoring_ends,
                    call_schedule = EXCLUDED.call_schedule,
                    domains = EXCLUDED.domains,
                    risk_flags = EXCLUDED.risk_flags,
                    clinical_red_flags = EXCLUDED.clinical_red_flags,
                    active = true
        """), {
            "patient_id": patient.patient_id,
            "opcs_code": opcs_code,
            "pathway_slug": pathway["pathway_slug"],
            "nice_ids": pathway["nice_ids"],
            "domains": custom_domains,
            "risk_flags": risk_flags,
            "clinical_red_flags": clinical_red_flags,
            "discharge_date": discharge_date,
            "monitoring_ends": monitoring_ends,
            "call_schedule": __import__("json").dumps(call_schedule),
        })
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create pathway record: {exc}")

    await db.commit()

    # Create CallSchedule rows for every pathway call day and enqueue Celery tasks
    from ..tasks.celery_app import celery_app
    from datetime import datetime as datetime_type, time as time_type_inner

    call_time = patient.preferred_call_time or time_type_inner(10, 0)
    for i, day in enumerate(pathway["call_days"]):
        call_date = discharge_date + timedelta(days=day)
        scheduled_for = datetime_type.combine(call_date, call_time).replace(tzinfo=timezone.utc)
        s = CallSchedule(
            patient_id=patient.patient_id,
            scheduled_for=scheduled_for,
            module="post_discharge",
            call_type="routine",
            protocol_name=pathway["label"],
            day_in_recovery_target=day,
            status="pending",
        )
        db.add(s)
        await db.flush()
        celery_app.send_task("fire_scheduled_call", args=[str(s.schedule_id)], eta=scheduled_for)
    await db.commit()

    # Fire-and-forget playbook generation (non-blocking)
    _patient_id_str = str(patient.patient_id)
    async def _generate_playbook_bg():
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        try:
            from ..clinical.playbook import generate_playbook
            from ..services.llm_client import LLMClient
            from ..services.rag_service import retrieve_nice_context
            from ..models import DomainBenchmark
            from ..database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                # Fetch benchmark rows for this pathway to give the LLM benchmark context
                bench_result = await session.execute(
                    select(DomainBenchmark).where(DomainBenchmark.opcs_code == opcs_code)
                )
                bench_rows = bench_result.scalars().all()

                # Retrieve top NICE guidance chunks for this pathway
                rag_chunks = await retrieve_nice_context(
                    session,
                    nice_ids=pathway["nice_ids"],
                    query=f"{pathway['label']} post-discharge recovery monitoring",
                    n=6,
                )

                pb = await generate_playbook(
                    opcs_code=opcs_code,
                    pathway_label=pathway["label"],
                    category=pathway["category"],
                    domains=custom_domains,
                    call_days=pathway["call_days"],
                    risk_flags=risk_flags,
                    llm_client=LLMClient(),
                    benchmark_rows=bench_rows,
                    rag_chunks=rag_chunks,
                    pathway_nice_ids=pathway["nice_ids"],
                    pathway_red_flags=pathway.get("red_flags", []),
                )
                await session.execute(text("""
                    UPDATE patient_pathways
                    SET playbook = cast(:playbook as jsonb)
                    WHERE patient_id = :patient_id AND opcs_code = :opcs_code
                """), {
                    "playbook": __import__("json").dumps(pb),
                    "patient_id": _patient_id_str,
                    "opcs_code": opcs_code,
                })
                await session.commit()
                _logger.info("Playbook generated for patient %s opcs_code=%s", _patient_id_str, opcs_code)
        except Exception as exc:
            _logging.getLogger(__name__).error(
                "Playbook generation failed for patient %s: %s", _patient_id_str, exc, exc_info=True
            )

    asyncio.ensure_future(_generate_playbook_bg())

    return {
        "patient_id": str(patient.patient_id),
        "nhs_number": nhs_number,
        "name": full_name,
        "opcs_code": opcs_code,
        "pathway_label": pathway["label"],
        "pathway_slug": pathway["pathway_slug"],
        "nice_ids": pathway["nice_ids"],
        "monitoring_window_days": pathway["monitoring_window_days"],
        "discharge_date": discharge_date.isoformat(),
        "monitoring_ends": monitoring_ends.isoformat(),
        "call_schedule": call_schedule,
        "domains": pathway["monitoring_domains"],
        "risk_flags": risk_flags,
    }
