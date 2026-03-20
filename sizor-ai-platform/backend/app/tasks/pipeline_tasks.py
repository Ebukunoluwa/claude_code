"""
Celery async tasks for post-call processing pipeline.
All LLM calls go through LLMClient (LiteLLM abstraction).
"""
import asyncio
import uuid
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from .celery_app import celery_app
from ..config import settings
from ..models import (
    CallRecord, ClinicalExtraction, SOAPNote, UrgencyFlag,
    LongitudinalSummary, FTPRecord, Patient,
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

            # Task 1: Extract clinical scores
            scores_raw = await extract_clinical_scores(transcript)
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
            soap_data = await generate_soap_note(transcript)
            soap = SOAPNote(
                call_id=call.call_id,
                patient_id=call.patient_id,
                subjective=soap_data.get("subjective", ""),
                objective=soap_data.get("objective", ""),
                assessment=soap_data.get("assessment", ""),
                plan=soap_data.get("plan", ""),
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

            expected, _, variance, ftp_status = compute_ftp(patient.condition, day, actual)
            ftp_reasoning = await generate_ftp_reasoning(
                patient.condition, day, expected, actual, variance, ftp_status
            )
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
            flags = await evaluate_flags(scores_raw, ftp_status, day)
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
                )
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

    asyncio.get_event_loop().run_until_complete(_run())
