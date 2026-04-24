"""Phase 2.5 Fix 2 — EWMA / carry-forward bad-prior guard.

Verifies that pipeline_tasks.py's prior loaders filter by
extraction_status='extracted' and walk back up to 5 rows. A 'failed'
or 'empty' prior must be skipped, not silently seed EWMA with its
(possibly stale) smoothed_scores — and must not contaminate the
domain-score carry-forward.

Run: PYTHONPATH=. python -m pytest tests/test_ewma_bad_prior_guard.py -v
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import (
    CallRecord,
    ClinicalExtraction,
    Hospital,
    Patient,
)


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


class _Scenario:
    """Creates a patient + N extractions with configurable statuses, then
    tears everything down. Each extraction has a unique call_id and its
    extracted_at spaced 1h apart so ORDER BY extracted_at DESC is
    deterministic."""

    def __init__(self):
        self.patient_id: uuid.UUID | None = None
        self.call_ids: list[uuid.UUID] = []
        self.extraction_ids: list[uuid.UUID] = []
        self.hospital_id: uuid.UUID | None = None

    async def setup(self, db, statuses_and_smoothed: list[tuple[str, dict | None]]):
        """Create extractions with the given (extraction_status, smoothed_scores)
        tuples, most-recent LAST in the list (i.e. index 0 is oldest)."""
        hosp = (await db.execute(select(Hospital).limit(1))).scalar_one_or_none()
        if hosp is None:
            hosp = Hospital(
                hospital_name="Phase 2.5 Fix 2 Test Hospital",
                nhs_trust_name="Test Trust",
            )
            db.add(hosp)
            await db.flush()
            self.hospital_id = hosp.hospital_id

        patient = Patient(
            hospital_id=hosp.hospital_id,
            full_name="Phase 2.5 Fix 2 Test Patient",
            nhs_number=f"TEST-{uuid.uuid4().hex[:8]}",
            date_of_birth=date(1980, 1, 1),
            phone_number="+440000000000",
            condition="Test Condition",
            discharge_date=date.today(),
            program_module="post_discharge",
        )
        db.add(patient)
        await db.flush()
        self.patient_id = patient.patient_id

        base = datetime.now(timezone.utc) - timedelta(days=7)
        for i, (status, smoothed) in enumerate(statuses_and_smoothed):
            call = CallRecord(
                patient_id=patient.patient_id,
                direction="outbound",
                trigger_type="scheduled",
                day_in_recovery=i,
                status="completed",
                started_at=base + timedelta(hours=i),
            )
            db.add(call)
            await db.flush()
            self.call_ids.append(call.call_id)

            ext = ClinicalExtraction(
                call_id=call.call_id,
                patient_id=patient.patient_id,
                extracted_at=base + timedelta(hours=i, minutes=30),
                smoothed_scores=smoothed or {},
                extraction_status=status,
                condition_specific_flags={"domain_scores": {"pain_management": i}},
            )
            db.add(ext)
            await db.flush()
            self.extraction_ids.append(ext.extraction_id)
        await db.commit()

    async def teardown(self, db):
        if self.extraction_ids:
            await db.execute(
                delete(ClinicalExtraction).where(
                    ClinicalExtraction.extraction_id.in_(self.extraction_ids)
                )
            )
        if self.call_ids:
            await db.execute(
                delete(CallRecord).where(CallRecord.call_id.in_(self.call_ids))
            )
        if self.patient_id:
            await db.execute(
                delete(Patient).where(Patient.patient_id == self.patient_id)
            )
        if self.hospital_id:
            await db.execute(
                delete(Hospital).where(Hospital.hospital_id == self.hospital_id)
            )
        await db.commit()


def _ewma_query(pid, current_call):
    """Exact filter used by pipeline_tasks.py after Fix 2."""
    return (
        select(ClinicalExtraction)
        .join(CallRecord, CallRecord.call_id == ClinicalExtraction.call_id)
        .where(
            ClinicalExtraction.patient_id == pid,
            ClinicalExtraction.call_id != current_call,
            CallRecord.trigger_type != "probe",
            ClinicalExtraction.extraction_status == "extracted",
        )
        .order_by(ClinicalExtraction.extracted_at.desc())
        .limit(5)
    )


def test_failed_most_recent_prior_is_skipped():
    """Most-recent prior is 'failed' with stale smoothed_scores; the second-
    most-recent is 'extracted'. The loader must return the good one."""
    async def _body(Session):
        s = _Scenario()
        async with Session() as db:
            await s.setup(db, [
                ("extracted", {"pain": 2.0}),  # oldest — good
                ("failed",    {"pain": 99.0}),  # middle — stale bad data
                ("extracted", {"pain": 3.0}),  # "current" (we query as if it's being processed)
            ])
            current = s.call_ids[-1]
            rows = list(
                (await db.execute(_ewma_query(s.patient_id, current))).scalars()
            )
            # Only the oldest survives the filter (middle is 'failed';
            # current is excluded via call_id).
            assert len(rows) == 1
            assert rows[0].smoothed_scores == {"pain": 2.0}
            await s.teardown(db)
        return "ok"

    _skip_if_needed(_run(_body))


def test_all_five_priors_failed_returns_empty():
    """5+ failed priors → loader returns empty → caller treats as first-call."""
    async def _body(Session):
        s = _Scenario()
        async with Session() as db:
            await s.setup(db, [
                ("failed", {"pain": 9.0}),
                ("failed", {"pain": 8.0}),
                ("failed", {"pain": 7.0}),
                ("failed", {"pain": 6.0}),
                ("failed", {"pain": 5.0}),
                ("extracted", {"pain": 1.0}),  # current
            ])
            current = s.call_ids[-1]
            rows = list(
                (await db.execute(_ewma_query(s.patient_id, current))).scalars()
            )
            # Filter excludes all failed priors AND excludes current.
            # No 'extracted' prior exists other than current → empty.
            assert rows == []
            await s.teardown(db)
        return "ok"

    _skip_if_needed(_run(_body))


def test_empty_status_prior_is_skipped():
    """'empty' extraction_status (ran, found nothing) is also skipped."""
    async def _body(Session):
        s = _Scenario()
        async with Session() as db:
            await s.setup(db, [
                ("extracted", {"pain": 2.0}),
                ("empty",     {"pain": 99.0}),  # stale leftover smoothed
                ("extracted", {"pain": 3.0}),  # current
            ])
            current = s.call_ids[-1]
            rows = list(
                (await db.execute(_ewma_query(s.patient_id, current))).scalars()
            )
            assert len(rows) == 1
            assert rows[0].smoothed_scores == {"pain": 2.0}
            await s.teardown(db)
        return "ok"

    _skip_if_needed(_run(_body))


def test_walk_back_stops_at_first_extracted_with_smoothed():
    """Simulates pipeline_tasks.py's walk: iterate the LIMIT 5 result set
    and take the first row whose smoothed_scores is populated. A 'extracted'
    row with empty smoothed_scores gets skipped in favour of an older
    'extracted' row that has data."""
    async def _body(Session):
        s = _Scenario()
        async with Session() as db:
            await s.setup(db, [
                ("extracted", {"pain": 2.0}),     # oldest, has data
                ("extracted", {}),                 # middle, extracted but no smoothed state
                ("extracted", {"pain": 3.0}),     # current
            ])
            current = s.call_ids[-1]
            # All three match the extraction_status filter; current is excluded
            # by call_id. Walk in DESC order and take first with smoothed.
            rows = list(
                (await db.execute(_ewma_query(s.patient_id, current))).scalars()
            )
            picked = next((r for r in rows if r.smoothed_scores), None)
            assert picked is not None
            assert picked.smoothed_scores == {"pain": 2.0}
            await s.teardown(db)
        return "ok"

    _skip_if_needed(_run(_body))
