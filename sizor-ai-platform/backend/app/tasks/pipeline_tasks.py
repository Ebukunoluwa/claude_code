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

            if not transcript.strip():
                logger.warning("Empty transcript for call %s — skipping pipeline", call_id)
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

            # Task 4: Evaluate flags
            try:
                flags = await evaluate_flags(scores_raw, ftp_status, day)
            except Exception as exc:
                logger.error("Flag evaluation failed for call %s: %s", call_id, exc, exc_info=True)
                flags = []
            for flag in flags:
                db.add(UrgencyFlag(
                    patient_id=call.patient_id,
                    call_id=call.call_id,
                    severity=flag["severity"],
                    flag_type=flag["flag_type"],
                    trigger_description=flag["trigger_description"],
                ))

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
                                score = max(0, min(4, round(val * 0.4)))
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
