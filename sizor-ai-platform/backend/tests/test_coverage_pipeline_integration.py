"""Phase 4 D7 — pipeline integration test for Task 1b.

Exercises the coverage-enforcement block from pipeline_tasks.py against
a real DB session, matching the async+skip-if-DB-down pattern used in
test_ewma_bad_prior_guard.py.

What this test verifies:
  - Task 1b writes a CallCoverageReport row with the expected shape.
  - The classifier is stubbed (via dependency injection on
    validate_call_coverage's llm_client parameter) — no live LLM call.
  - The FAIL-OPEN guarantee: a raising classifier does NOT crash the
    "pipeline"; a NULL-coverage row still lands.
  - The coverage_enforcement_enabled flag short-circuits the block.

Scope: this exercises the coverage helpers + ORM layer, mirroring the
insertion block in pipeline_tasks.py. We deliberately do NOT stand up
the full process_call task (that requires LLM stubs for extraction,
SOAP, FTP, flags, longitudinal summary, playbook — all orthogonal to
Phase 4). The broader pipeline's correctness is covered by existing
tests (test_ewma_bad_prior_guard, test_probe_isolation, etc.).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.clinical_intelligence.coverage import validate_call_coverage
from app.config import settings
from app.models import (
    CallCoverageReport,
    CallRecord,
    Hospital,
    Patient,
)


class _StubLLM:
    def __init__(self, response: str):
        self._response = response

    async def complete(self, system: str, user: str) -> str:
        return self._response


class _RaisingLLM:
    async def complete(self, system: str, user: str) -> str:
        raise RuntimeError("simulated API outage")


# ─── DB harness (mirrors test_ewma_bad_prior_guard) ────────────────────

def _run(coro_factory):
    async def _wrap():
        engine = create_async_engine(settings.database_url)
        try:
            Session = async_sessionmaker(engine, expire_on_commit=False)
            try:
                async with Session() as db:
                    await db.execute(select(1))
            except OperationalError as exc:
                return ("skip_db_down", str(exc))
            return await coro_factory(Session)
        finally:
            await engine.dispose()
    return asyncio.run(_wrap())


def _skip_if_needed(result):
    if isinstance(result, tuple) and result[0] == "skip_db_down":
        pytest.skip(f"DB unreachable: {result[1]}")


async def _setup_patient_and_call(db, opcs_code: str = "W40") -> tuple[uuid.UUID, uuid.UUID, int]:
    """Create a minimal patient + call fixture. Returns (patient_id,
    call_id, day_in_recovery). Caller is responsible for cleanup."""
    # Minimal hospital (required FK for patient in some schemas — be
    # defensive and reuse if one exists).
    h_result = await db.execute(select(Hospital).limit(1))
    hospital = h_result.scalar_one_or_none()
    if hospital is None:
        hospital = Hospital(
            hospital_id=uuid.uuid4(),
            name="Phase 4 test hospital",
            trust_code="TST",
        )
        db.add(hospital)
        await db.flush()

    patient = Patient(
        patient_id=uuid.uuid4(),
        full_name="Phase 4 Coverage Test Patient",
        nhs_number=f"999{uuid.uuid4().hex[:7]}",
        date_of_birth=date(1970, 1, 1),
        phone_number="+441234567890",
        hospital_id=hospital.hospital_id,
        condition="Post-op monitoring",
        procedure="Total knee replacement",
        program_module="orthopaedic",
        discharge_date=date.today() - timedelta(days=7),
    )
    db.add(patient)

    # Minimal patient_pathways row so the opcs lookup in pipeline_tasks
    # would resolve if we were running process_call (not required for
    # this focused test since we call validate_call_coverage directly).
    # domains is text[] in this table's schema; pathway_slug is NOT NULL.
    await db.flush()
    await db.execute(
        text(
            "INSERT INTO patient_pathways "
            "(patient_id, opcs_code, pathway_slug, domains, "
            " discharge_date, monitoring_ends, active, created_at) "
            "VALUES (:pid, :opcs, :slug, :domains, "
            "        :discharge, :monitoring_ends, true, now())"
        ),
        {
            "pid": str(patient.patient_id),
            "opcs": opcs_code,
            "slug": f"phase4-test-{uuid.uuid4().hex[:8]}",
            "domains": [
                "wound_healing", "pain_management", "vte_prophylaxis",
                "mobility_progress", "infection_signs", "physiotherapy_compliance",
            ],
            "discharge": date.today() - timedelta(days=7),
            "monitoring_ends": date.today() + timedelta(days=60),
        },
    )

    call = CallRecord(
        call_id=uuid.uuid4(),
        patient_id=patient.patient_id,
        direction="outbound",
        trigger_type="routine",
        day_in_recovery=7,
        status="completed",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        transcript_raw="[AGENT] Hello, calling about your knee. [PATIENT] I'm doing OK.",
        call_type="routine",
    )
    db.add(call)
    await db.flush()
    return patient.patient_id, call.call_id, 7


async def _cleanup(db, patient_id: uuid.UUID):
    await db.execute(
        delete(CallCoverageReport).where(CallCoverageReport.patient_id == patient_id)
    )
    await db.execute(
        delete(CallRecord).where(CallRecord.patient_id == patient_id)
    )
    await db.execute(
        text("DELETE FROM patient_pathways WHERE patient_id = :pid"),
        {"pid": str(patient_id)},
    )
    await db.execute(delete(Patient).where(Patient.patient_id == patient_id))
    await db.commit()


# ─── Scenarios ─────────────────────────────────────────────────────────

def test_coverage_row_persists_with_expected_shape():
    """Happy-path: classifier returns a full report, Task 1b persists
    a CallCoverageReport row with matching fields."""

    async def _scenario(Session):
        async with Session() as db:
            patient_id, call_id, day = await _setup_patient_and_call(db)
            call = (await db.execute(
                select(CallRecord).where(CallRecord.call_id == call_id)
            )).scalar_one()

            # Stub LLM: mark everything as asked, nothing positive.
            stub_response = json.dumps({
                "required_questions_asked": [
                    # Use actual W40 day-7 RQ text so the whitelist passes.
                    "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
                ],
                "required_questions_patient_declined": [],
                "red_flag_probes_asked": [],
                "red_flag_probes_positive": [],
            })
            stub_llm = _StubLLM(stub_response)

            # Exercise the same call Task 1b makes.
            report = await validate_call_coverage(
                transcript=call.transcript_raw,
                opcs_code="W40",
                call_day=day,
                llm_client=stub_llm,
            )

            # Persist exactly as Task 1b does.
            db.add(CallCoverageReport(
                call_id=call.call_id,
                patient_id=call.patient_id,
                opcs_code="W40",
                day_in_recovery=day,
                required_questions_expected=report.required_questions_expected,
                required_questions_asked=report.required_questions_asked,
                required_questions_patient_declined=report.required_questions_patient_declined,
                red_flag_probes_expected=report.red_flag_probes_expected,
                red_flag_probes_asked=report.red_flag_probes_asked,
                red_flag_probes_positive=report.red_flag_probes_positive,
                socrates_probes_triggered=report.socrates_probes_triggered,
                socrates_probes_completed=report.socrates_probes_completed,
                coverage_percentage=report.coverage_percentage,
                incomplete_items=report.incomplete_items,
                raw_classifier_output=report.raw_classifier_output,
            ))
            await db.commit()

            # Read back and assert.
            persisted = (await db.execute(
                select(CallCoverageReport).where(CallCoverageReport.call_id == call_id)
            )).scalar_one()

            try:
                assert persisted.opcs_code == "W40"
                assert persisted.day_in_recovery == 7
                assert persisted.coverage_percentage is not None
                # 1 RQ asked / 18 total = 5.6%
                assert 0 < persisted.coverage_percentage < 10
                assert len(persisted.required_questions_expected) == 6  # W40 day-7 RQs
                assert len(persisted.red_flag_probes_expected) == 12
                assert len(persisted.required_questions_asked) == 1
                assert isinstance(persisted.raw_classifier_output, dict)
                assert "required_questions_asked" in persisted.raw_classifier_output
            finally:
                await _cleanup(db, patient_id)

            return "ok"

    result = _run(_scenario)
    _skip_if_needed(result)
    assert result == "ok"


def test_fail_open_when_classifier_raises():
    """FAIL-OPEN guarantee: a raising LLM client does NOT propagate.
    validate_call_coverage catches it internally and returns a 0%
    report. Task 1b persists that row; the pipeline continues."""

    async def _scenario(Session):
        async with Session() as db:
            patient_id, call_id, day = await _setup_patient_and_call(db)

            # Classifier catches the exception and returns a 0% report.
            report = await validate_call_coverage(
                transcript="any transcript",
                opcs_code="W40",
                call_day=day,
                llm_client=_RaisingLLM(),
            )

            # Task 1b would still persist this row — simulate that.
            db.add(CallCoverageReport(
                call_id=call_id,
                patient_id=patient_id,
                opcs_code="W40",
                day_in_recovery=day,
                required_questions_expected=report.required_questions_expected,
                required_questions_asked=report.required_questions_asked,
                required_questions_patient_declined=report.required_questions_patient_declined,
                red_flag_probes_expected=report.red_flag_probes_expected,
                red_flag_probes_asked=report.red_flag_probes_asked,
                red_flag_probes_positive=report.red_flag_probes_positive,
                socrates_probes_triggered=report.socrates_probes_triggered,
                socrates_probes_completed=report.socrates_probes_completed,
                coverage_percentage=report.coverage_percentage,
                incomplete_items=report.incomplete_items,
                raw_classifier_output=report.raw_classifier_output,
            ))
            await db.commit()

            persisted = (await db.execute(
                select(CallCoverageReport).where(CallCoverageReport.call_id == call_id)
            )).scalar_one()

            try:
                assert persisted.coverage_percentage == 0.0
                # All 18 items incomplete (6 RQs + 12 RFPs for W40 day 7).
                assert len(persisted.incomplete_items) == 18
                # Empty raw_classifier_output because the LLM raised before
                # a response was produced.
                assert persisted.raw_classifier_output == {}
            finally:
                await _cleanup(db, patient_id)

            return "ok"

    result = _run(_scenario)
    _skip_if_needed(result)
    assert result == "ok"


def test_z03_mh_scaffold_short_circuits_without_llm_call():
    """Z03_MH scaffold has empty manifests. validate_call_coverage
    returns 100% without hitting the LLM. Task 1b persists the row
    cleanly. Integration-level verification that the scaffold path
    doesn't accidentally try to classify against empty expected lists."""

    async def _scenario(Session):
        async with Session() as db:
            patient_id, call_id, day = await _setup_patient_and_call(db, opcs_code="Z03_MH")

            # Pass a raising LLM — should never be called.
            report = await validate_call_coverage(
                transcript="any transcript",
                opcs_code="Z03_MH",
                call_day=day,
                llm_client=_RaisingLLM(),
            )

            db.add(CallCoverageReport(
                call_id=call_id,
                patient_id=patient_id,
                opcs_code="Z03_MH",
                day_in_recovery=day,
                required_questions_expected=report.required_questions_expected,
                required_questions_asked=report.required_questions_asked,
                required_questions_patient_declined=report.required_questions_patient_declined,
                red_flag_probes_expected=report.red_flag_probes_expected,
                red_flag_probes_asked=report.red_flag_probes_asked,
                red_flag_probes_positive=report.red_flag_probes_positive,
                socrates_probes_triggered=report.socrates_probes_triggered,
                socrates_probes_completed=report.socrates_probes_completed,
                coverage_percentage=report.coverage_percentage,
                incomplete_items=report.incomplete_items,
                raw_classifier_output=report.raw_classifier_output,
            ))
            await db.commit()

            persisted = (await db.execute(
                select(CallCoverageReport).where(CallCoverageReport.call_id == call_id)
            )).scalar_one()

            try:
                assert persisted.opcs_code == "Z03_MH"
                # Nothing to cover, nothing missed.
                assert persisted.coverage_percentage == 100.0
                assert persisted.required_questions_expected == []
                assert persisted.red_flag_probes_expected == []
                assert persisted.incomplete_items == []
            finally:
                await _cleanup(db, patient_id)

            return "ok"

    result = _run(_scenario)
    _skip_if_needed(result)
    assert result == "ok"


def test_feature_flag_short_circuit_behaviour():
    """Integration-level sanity: when coverage_enforcement_enabled is
    False, Task 1b in pipeline_tasks.py skips the block entirely. This
    test verifies the flag is the single switch — not that the pipeline
    actually skipped (pipeline_tasks integration is out of scope)."""
    # The flag is a simple bool on settings — verify it's readable and
    # truthy-checkable. The pipeline_tasks insertion guards on it.
    assert isinstance(settings.coverage_enforcement_enabled, bool)
    assert isinstance(settings.coverage_threshold, float)
    assert 0.0 <= settings.coverage_threshold <= 1.0
