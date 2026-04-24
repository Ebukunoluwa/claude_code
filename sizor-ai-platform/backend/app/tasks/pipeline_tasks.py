"""
Celery async tasks for post-call processing pipeline.
All LLM calls go through LLMClient (LiteLLM abstraction).
"""
import asyncio
import json
import logging
import uuid

logger = logging.getLogger(__name__)
from datetime import date
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from .celery_app import celery_app
from ..config import settings
from ..models import (
    CallRecord, ClinicalExtraction, SOAPNote, UrgencyFlag,
    LongitudinalSummary, FTPRecord, Patient, CallSchedule, DomainBenchmark,
)
from ..services.post_call_pipeline import (
    extract_clinical_scores, generate_soap_note, generate_ftp_reasoning,
    evaluate_flags, generate_longitudinal_summary,
)
from ..services.ftp_service import compute_ftp
from ..clinical.risk_score import compute_risk_score, breakdown_to_dict


def _get_session():
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="process_call")
def process_call(call_id: str):
    async def _run():
        SessionLocal = _get_session()
        async with SessionLocal() as db:
            result = await db.execute(
                select(CallRecord).where(CallRecord.call_id == uuid.UUID(call_id))
            )
            call = result.scalar_one_or_none()
            if not call:
                return

            p_result = await db.execute(
                select(Patient).where(Patient.patient_id == call.patient_id)
            )
            patient = p_result.scalar_one_or_none()
            if not patient:
                return

            transcript = call.transcript_raw or ""
            day = call.day_in_recovery or 1

            if call.status in ("missed", "no_answer"):
                logger.warning("Call %s has status '%s' — skipping pipeline", call_id, call.status)
                return

            if not transcript.strip():
                logger.warning("Empty transcript for call %s — skipping pipeline", call_id)
                return

            # Voicemail detection: if the transcript is dominated by answerphone system
            # prompts with no real patient interaction, skip scoring entirely.
            _patient_lines = [l for l in transcript.splitlines() if l.startswith("[PATIENT]")]
            _voicemail_phrases = (
                "press one", "press two", "press three", "press four", "press five",
                "press hash", "leave a message", "after the tone", "you've recorded",
                "your message has been", "listen back", "to rerecord", "hang up",
                "another line", "leave your message", "confidentiality settings",
            )
            if _patient_lines:
                _vm_count = sum(
                    1 for l in _patient_lines
                    if any(p in l.lower() for p in _voicemail_phrases)
                )
                _is_voicemail = _vm_count / len(_patient_lines) >= 0.6
                if _is_voicemail:
                    logger.warning("Call %s appears to be a voicemail (%d/%d lines match) — skipping clinical pipeline",
                                   call_id, _vm_count, len(_patient_lines))
                    return

            # Fetch pathway domains so extraction captures 0-4 domain scores
            from ..clinical.pathway_map import OPCS_TO_NICE_MAP
            _pw_row = await db.execute(text("""
                SELECT opcs_code, domains FROM patient_pathways
                WHERE patient_id = :pid AND active = true
                LIMIT 1
            """), {"pid": str(patient.patient_id)})
            _pw = _pw_row.mappings().first()
            _opcs_code = _pw["opcs_code"] if _pw else None
            _pathway_domains = (
                (_pw["domains"] if _pw and _pw["domains"] else None)
                or (OPCS_TO_NICE_MAP.get(_opcs_code or "", {}).get("monitoring_domains"))
            )

            # Task 1: Extract clinical scores
            try:
                scores_raw = await extract_clinical_scores(transcript, domains=_pathway_domains)
            except Exception as exc:
                logger.error("Score extraction failed for call %s: %s", call_id, exc, exc_info=True)
                scores_raw = {}

            # ── Domain → generic score bridge ───────────────────────────────
            # Pathway-specific calls (e.g. R18, W37) collect domain scores on a
            # 0-4 scale rather than the generic 0-10 channels.  If the 0-10
            # generic fields are null after extraction, derive them from the
            # domain scores so the EWMA smoothing and risk-score computation
            # have meaningful inputs.  Scale: 0-4 × 2.5 = 0-10.
            #
            # Domain score carry-forward: domains not discussed in this call
            # keep their last known score from the prior extraction. This prevents
            # a call that only covers some domains from wiping out scores for
            # domains that weren't touched in this session.
            _prior_domain_scores: dict = {}
            try:
                _prior_ext_for_domains = await db.execute(
                    select(ClinicalExtraction)
                    .where(
                        ClinicalExtraction.patient_id == call.patient_id,
                        ClinicalExtraction.call_id != call.call_id,
                    )
                    .order_by(ClinicalExtraction.extracted_at.desc())
                    .limit(1)
                )
                _prior_ext_row = _prior_ext_for_domains.scalar_one_or_none()
                if _prior_ext_row and _prior_ext_row.condition_specific_flags:
                    _prior_domain_scores = (
                        (_prior_ext_row.condition_specific_flags or {}).get("domain_scores") or {}
                    )
            except Exception:
                pass

            # Current call's domain scores — only covers domains the LLM saw evidence for
            _current_domain_scores: dict = (
                (scores_raw.get("condition_specific_flags") or {}).get("domain_scores") or {}
            )

            # Merge: prior scores as baseline, current call scores override where present
            _domain_scores: dict = {**_prior_domain_scores, **_current_domain_scores}

            # Write the merged set back into scores_raw so it's persisted
            if _domain_scores:
                if "condition_specific_flags" not in scores_raw or scores_raw["condition_specific_flags"] is None:
                    scores_raw["condition_specific_flags"] = {}
                scores_raw["condition_specific_flags"]["domain_scores"] = _domain_scores

            if _domain_scores:
                def _d2t(keys: list[str], invert: bool = False):
                    """Return 0-10 from the first matching domain key (0-4 × 2.5)."""
                    for k in keys:
                        v = _domain_scores.get(k)
                        if v is not None:
                            scaled = float(v) * 2.5
                            return round((10.0 - scaled) if invert else scaled, 1)
                    return None

                if scores_raw.get("pain_score") is None:
                    b = _d2t(["pain_management", "pain", "wound_healing_pfannenstiel",
                               "wound_healing", "headache", "chest_pain_monitoring"])
                    if b is not None:
                        scores_raw["pain_score"] = b

                if scores_raw.get("breathlessness_score") is None:
                    b = _d2t(["breathlessness", "breathlessness_and_cough",
                               "oxygen_saturation", "breathlessness_recovery"])
                    if b is not None:
                        scores_raw["breathlessness_score"] = b

                if scores_raw.get("mobility_score") is None:
                    b = _d2t(["mobility_progress", "mobility", "mobility_and_rehabilitation",
                               "falls_risk"])
                    if b is not None:
                        scores_raw["mobility_score"] = b

                if scores_raw.get("appetite_score") is None:
                    b = _d2t(["appetite", "nutrition", "swallowing_and_nutrition",
                               "fatigue_and_recovery", "fatigue_and_functional_recovery"])
                    if b is not None:
                        scores_raw["appetite_score"] = b

                # Mood is inverted: domain 0 = no problem (good mood), 4 = severe (bad mood).
                # Map to generic mood_score where 10 = great, 0 = terrible.
                if scores_raw.get("mood_score") is None:
                    b = _d2t(
                        ["postnatal_depression_screen", "postnatal_mood", "mood",
                         "mood_and_depression", "mood_and_anxiety", "mood_screen",
                         "emotional_processing_of_birth", "emotional_recovery",
                         "psychological_impact", "safety_and_suicidality"],
                        invert=True,
                    )
                    if b is not None:
                        scores_raw["mood_score"] = b
            # ────────────────────────────────────────────────────────────────

            # Upsert: update existing extraction if one already exists for this call
            existing_ext = await db.execute(
                select(ClinicalExtraction).where(ClinicalExtraction.call_id == call.call_id)
                .order_by(ClinicalExtraction.extracted_at.desc()).limit(1)
            )
            extraction = existing_ext.scalar_one_or_none()
            if extraction:
                extraction.pain_score = scores_raw.get("pain_score")
                extraction.breathlessness_score = scores_raw.get("breathlessness_score")
                extraction.mobility_score = scores_raw.get("mobility_score")
                extraction.appetite_score = scores_raw.get("appetite_score")
                extraction.mood_score = scores_raw.get("mood_score")
                extraction.medication_adherence = scores_raw.get("medication_adherence")
                extraction.condition_specific_flags = scores_raw.get("condition_specific_flags", {})
                extraction.raw_extraction_json = scores_raw
            else:
                extraction = ClinicalExtraction(
                    call_id=call.call_id,
                    patient_id=call.patient_id,
                    pain_score=scores_raw.get("pain_score"),
                    breathlessness_score=scores_raw.get("breathlessness_score"),
                    mobility_score=scores_raw.get("mobility_score"),
                    appetite_score=scores_raw.get("appetite_score"),
                    mood_score=scores_raw.get("mood_score"),
                    medication_adherence=scores_raw.get("medication_adherence"),
                    condition_specific_flags=scores_raw.get("condition_specific_flags", {}),
                    raw_extraction_json=scores_raw,
                )
                db.add(extraction)

            # Task 2: Generate SOAP note
            try:
                soap_data = await generate_soap_note(transcript)
                logger.info("SOAP note generated for call %s", call_id)
            except Exception as exc:
                logger.error("SOAP generation failed for call %s: %s", call_id, exc, exc_info=True)
                soap_data = {}
            def _str(v):
                """Coerce any value to string — LLM sometimes returns dicts for SOAP fields."""
                if v is None:
                    return ""
                if isinstance(v, str):
                    return v
                if isinstance(v, dict):
                    return "; ".join(f"{k}: {val}" for k, val in v.items())
                return str(v)

            # Upsert: update existing SOAP note if one already exists for this call
            existing_soap = await db.execute(
                select(SOAPNote).where(SOAPNote.call_id == call.call_id)
                .order_by(SOAPNote.generated_at.desc()).limit(1)
            )
            soap = existing_soap.scalar_one_or_none()
            if soap:
                soap.subjective = _str(soap_data.get("subjective"))
                soap.objective = _str(soap_data.get("objective"))
                soap.assessment = _str(soap_data.get("assessment"))
                soap.plan = _str(soap_data.get("plan"))
                soap.model_used = settings.llm_model
            else:
                soap = SOAPNote(
                    call_id=call.call_id,
                    patient_id=call.patient_id,
                    subjective=_str(soap_data.get("subjective")),
                    objective=_str(soap_data.get("objective")),
                    assessment=_str(soap_data.get("assessment")),
                    plan=_str(soap_data.get("plan")),
                    model_used=settings.llm_model,
                )
                db.add(soap)
            await db.flush()

            # Task 3: FTP assessment
            actual = {k: v for k, v in {
                "pain": scores_raw.get("pain_score"),
                "breathlessness": scores_raw.get("breathlessness_score"),
                "mobility": scores_raw.get("mobility_score"),
                "mood": scores_raw.get("mood_score"),
                "appetite": scores_raw.get("appetite_score"),
            }.items() if v is not None}

            try:
                expected, _, variance, ftp_status = compute_ftp(patient.condition, day, actual)
                ftp_reasoning = await generate_ftp_reasoning(
                    patient.condition, day, expected, actual, variance, ftp_status
                )
            except Exception as exc:
                logger.error("FTP assessment failed for call %s: %s", call_id, exc, exc_info=True)
                expected, variance, ftp_status, ftp_reasoning = {}, {}, "unknown", ""
            ftp = FTPRecord(
                call_id=call.call_id,
                patient_id=call.patient_id,
                condition=patient.condition,
                module=patient.program_module,
                day_in_recovery=day,
                expected_scores=expected,
                actual_scores=actual,
                variance_per_domain=variance,
                ftp_status=ftp_status,
                reasoning_text=ftp_reasoning,
            )
            db.add(ftp)

            # Task 4: Evaluate flags + compute smoothed scores + risk score
            # Load prior ClinicalExtraction for this patient (excluding current call)
            # to drive EWMA smoothing across calls.
            prior_smoothed: dict | None = None
            try:
                prior_ext_result = await db.execute(
                    select(ClinicalExtraction)
                    .where(
                        ClinicalExtraction.patient_id == call.patient_id,
                        ClinicalExtraction.call_id != call.call_id,
                    )
                    .order_by(ClinicalExtraction.extracted_at.desc())
                    .limit(1)
                )
                prior_ext = prior_ext_result.scalar_one_or_none()
                if prior_ext and prior_ext.smoothed_scores:
                    prior_smoothed = prior_ext.smoothed_scores
            except Exception as exc:
                logger.warning(
                    "Could not load prior smoothed state for patient %s: %s",
                    call.patient_id, exc,
                )

            # TODO: drive `critical_medication` from Patient/medication model once
            # medication criticality is represented. For now: conservative default.
            critical_medication = False

            try:
                flags, smoothed_state = await evaluate_flags(
                    scores_raw, ftp_status, day,
                    prior_smoothed=prior_smoothed,
                    critical_medication=critical_medication,
                )
            except Exception as exc:
                logger.error("Flag evaluation failed for call %s: %s", call_id, exc, exc_info=True)
                flags, smoothed_state = [], {}

            for flag in flags:
                db.add(UrgencyFlag(
                    patient_id=call.patient_id,
                    call_id=call.call_id,
                    severity=flag["severity"],
                    flag_type=flag["flag_type"],
                    trigger_description=flag["trigger_description"],
                ))

            # Compute 0-100 risk score from smoothed state + context.
            # Populates extraction.risk_score for the dashboard to read.
            try:
                has_red_flag = any(f["severity"] == "red" for f in flags)
                from ..clinical_intelligence.smoothing import SmoothedScores
                smoothed_obj = SmoothedScores(
                    pain=smoothed_state.get("pain"),
                    breathlessness=smoothed_state.get("breathlessness"),
                    mobility=smoothed_state.get("mobility"),
                    appetite=smoothed_state.get("appetite"),
                    mood=smoothed_state.get("mood"),
                    max_smoothed=max(
                        (v for v in (
                            smoothed_state.get("pain"),
                            smoothed_state.get("breathlessness"),
                            smoothed_state.get("mobility"),
                            smoothed_state.get("appetite"),
                        ) if v is not None),
                        default=0.0,
                    ),
                    modifier_total=smoothed_state.get("modifier_total", 0.0),
                    modifier_detail=smoothed_state.get("modifier_detail", {}),
                    lam=smoothed_state.get("lam", 0.3),
                )
                breakdown = compute_risk_score(
                    smoothed_obj,
                    ftp_status=ftp_status,
                    day_in_recovery=day,
                    has_active_red_flag=has_red_flag,
                    raw_pain=scores_raw.get("pain_score"),
                    raw_breathlessness=scores_raw.get("breathlessness_score"),
                )
                extraction.smoothed_scores = smoothed_state
                extraction.risk_score = breakdown.final_score
                bd_dict = breakdown_to_dict(breakdown)
                # Embed domain scores so the frontend WHY panel can display them
                # even when generic weighted contributions are also present.
                if _domain_scores:
                    bd_dict["domain_scores"] = _domain_scores
                extraction.risk_score_breakdown = bd_dict
            except Exception as exc:
                logger.error(
                    "Risk score computation failed for call %s: %s",
                    call_id, exc, exc_info=True,
                )
                # Leave fields at DB defaults. Do not fail the pipeline.

            # Task 5: Longitudinal summary
            prev_result = await db.execute(
                select(LongitudinalSummary).where(
                    LongitudinalSummary.patient_id == call.patient_id,
                    LongitudinalSummary.is_current == True,
                ).order_by(LongitudinalSummary.version_number.desc()).limit(1)
            )
            prev = prev_result.scalar_one_or_none()
            version = (prev.version_number + 1) if prev else 1
            if prev:
                prev.is_current = False

            age = None
            if patient.date_of_birth:
                today = date.today()
                dob = patient.date_of_birth
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            try:
                summary_data = await generate_longitudinal_summary(
                    patient_name=patient.full_name,
                    age=age,
                    discharge_date=str(patient.discharge_date) if patient.discharge_date else "unknown",
                    condition=patient.condition,
                    procedure=patient.procedure,
                    day=day,
                    soap_assessment=soap_data.get("assessment", ""),
                    scores={
                        "pain": scores_raw.get("pain_score"),
                        "breathlessness": scores_raw.get("breathlessness_score"),
                        "mobility": scores_raw.get("mobility_score"),
                        "mood": scores_raw.get("mood_score"),
                        "adherence": scores_raw.get("medication_adherence"),
                    },
                    ftp_status=ftp_status,
                    ftp_reasoning=ftp_reasoning,
                    flags=flags,
                    probe_instructions=call.probe_instructions,
                    previous_narrative=prev.narrative_text if prev else None,
                    version=version,
                )
                logger.info("Longitudinal summary generated for call %s (v%s)", call_id, version)
            except Exception as exc:
                logger.error("Longitudinal summary failed for call %s: %s", call_id, exc, exc_info=True)
                summary_data = {"narrative_text": "", "active_concerns_snapshot": [], "trend_snapshot": {}}
            db.add(LongitudinalSummary(
                patient_id=call.patient_id,
                triggered_by_call_id=call.call_id,
                narrative_text=summary_data["narrative_text"],
                active_concerns_snapshot=summary_data["active_concerns_snapshot"],
                trend_snapshot=summary_data["trend_snapshot"],
                version_number=version,
                is_current=True,
            ))
            await db.commit()
            logger.info("Pipeline complete for call %s", call_id)

            # ── Task 6: Regenerate playbook for next scheduled call ───────────
            try:
                from ..clinical.playbook import generate_playbook
                from ..services.llm_client import LLMClient
                from ..services.rag_service import retrieve_nice_context

                # Get patient's active pathway
                pathway_row = await db.execute(text("""
                    SELECT opcs_code, domains, risk_flags
                    FROM patient_pathways
                    WHERE patient_id = :pid AND active = true
                    LIMIT 1
                """), {"pid": str(call.patient_id)})
                pw = pathway_row.mappings().first()

                if pw:
                    opcs_code = pw["opcs_code"]

                    # Get next pending scheduled call
                    next_result = await db.execute(
                        select(CallSchedule)
                        .where(
                            CallSchedule.patient_id == call.patient_id,
                            CallSchedule.status == "pending",
                        )
                        .order_by(CallSchedule.scheduled_for)
                        .limit(1)
                    )
                    next_call = next_result.scalar_one_or_none()
                    next_day = (next_call.day_in_recovery_target or day + 1) if next_call else day + 1

                    # Fetch benchmark rows for LLM context
                    bench_result = await db.execute(
                        select(DomainBenchmark).where(DomainBenchmark.opcs_code == opcs_code)
                    )
                    bench_rows = bench_result.scalars().all()

                    # Build previous scores for trajectory context (domain → {day, score, ftp_flag})
                    # Use the actual 0-4 domain scores captured during this call if available
                    prev_scores: dict = {}
                    domain_scores = scores_raw.get("condition_specific_flags", {}).get("domain_scores", {})
                    if domain_scores:
                        for domain, score in domain_scores.items():
                            if score is not None:
                                prev_scores[domain] = {"day": day, "score": score, "ftp_flag": False}
                    else:
                        # Fallback: approximate from generic 0-10 scores
                        for generic_domain, pathway_domains in {
                            "pain":           ["pain_management", "chest_pain_monitoring"],
                            "mobility":       ["mobility_progress", "mobility_and_rehabilitation"],
                            "breathlessness": ["breathlessness_score", "breathlessness"],
                            "mood":           ["mood_and_depression", "mood_and_anxiety"],
                        }.items():
                            val = actual.get(generic_domain)
                            if val is not None:
                                from ..clinical_intelligence.scoring import score_0_10_to_0_4
                                score = score_0_10_to_0_4(val)
                                var_d = variance.get(generic_domain, {})
                                for pd in pathway_domains:
                                    prev_scores[pd] = {"day": day, "score": score, "ftp_flag": var_d.get("worse", False)}

                    from ..clinical.pathway_map import OPCS_TO_NICE_MAP
                    pw_data = OPCS_TO_NICE_MAP.get(opcs_code, {})
                    nice_ids = pw_data.get("nice_ids", [])

                    # Retrieve NICE guidance RAG context for this pathway + trajectory
                    rag_query = (
                        f"{pw_data.get('label', opcs_code)} day {next_day} "
                        f"post-discharge recovery monitoring"
                    )
                    rag_chunks = await retrieve_nice_context(db, nice_ids=nice_ids, query=rag_query, n=6)

                    pb = await generate_playbook(
                        opcs_code=opcs_code,
                        pathway_label=pw_data.get("label", opcs_code),
                        category=pw_data.get("category", "surgical"),
                        domains=pw["domains"] or pw_data.get("monitoring_domains", []),
                        call_days=[next_day],
                        risk_flags=pw["risk_flags"] or [],
                        llm_client=LLMClient(),
                        benchmark_rows=bench_rows,
                        previous_scores=prev_scores,
                        rag_chunks=rag_chunks,
                        pathway_nice_ids=nice_ids,
                        pathway_red_flags=pw_data.get("red_flags", []),
                    )
                    await db.execute(text("""
                        UPDATE patient_pathways
                        SET playbook = cast(:playbook as jsonb)
                        WHERE patient_id = :pid AND opcs_code = :opcs_code
                    """), {
                        "playbook": json.dumps(pb),
                        "pid": str(call.patient_id),
                        "opcs_code": opcs_code,
                    })
                    await db.commit()
                    logger.info("Playbook regenerated for patient %s next day %s", call.patient_id, next_day)
            except Exception as exc:
                logger.warning("Playbook regeneration failed after call %s: %s", call_id, exc)

    asyncio.run(_run())
