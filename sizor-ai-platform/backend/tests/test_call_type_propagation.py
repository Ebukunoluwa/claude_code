"""Phase 2.5 Fix 3 — call_type on CallRecord + backfill proximity match.

Verifies:
  - ORM declares call_type on CallRecord.
  - ORM<->DB schema parity still passes (via test_orm_db_schema_parity).
  - Backfill SQL matches within 15min and tie-breaks by closest delta.
  - Outside ±15min window: no match.

Ingest-time population is covered indirectly by the backfill SQL test
+ the static ORM test — the ingest path's call_type_value assignment
is trivial (probe → 'probe'; CallSchedule lookup → call_type). Full
end-to-end ingest-endpoint testing would require a TestClient against
FastAPI; that's Phase 4's integration-test infra.

Run: PYTHONPATH=. python -m pytest tests/test_call_type_propagation.py -v
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import CallRecord, CallSchedule, Hospital, Patient


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


def test_call_type_attribute_declared_on_orm():
    """Static check — doesn't need DB access. If someone removes the
    attribute, this fails immediately."""
    assert hasattr(CallRecord, "call_type")
    col = CallRecord.__table__.c.call_type
    assert col.nullable is True
    assert str(col.type) in ("VARCHAR(20)", "String(20)")


def _make_scenario(hosp_id):
    from datetime import date as _date
    return Patient(
        hospital_id=hosp_id,
        full_name="Phase 2.5 Fix 3 Patient",
        nhs_number=f"TEST-{uuid.uuid4().hex[:8]}",
        date_of_birth=_date(1980, 1, 1),
        phone_number="+440000000000",
        condition="Test",
        discharge_date=_date.today(),
        program_module="post_discharge",
    )


def test_backfill_matches_within_15min():
    """A CallRecord.started_at 10 minutes before a CallSchedule.scheduled_for
    with call_type='retry' should backfill to call_type='retry'."""
    async def _body(Session):
        async with Session() as db:
            hosp = (await db.execute(select(Hospital).limit(1))).scalar_one_or_none()
            if hosp is None:
                hosp = Hospital(
                    hospital_name="Fix3 Test Hospital",
                    nhs_trust_name="Trust",
                )
                db.add(hosp)
                await db.flush()

            patient = _make_scenario(hosp.hospital_id)
            db.add(patient)
            await db.flush()

            # Schedule at 12:00, call at 11:50 (10 min before)
            sched_time = datetime.now(timezone.utc).replace(microsecond=0)
            call_time = sched_time - timedelta(minutes=10)

            sched = CallSchedule(
                patient_id=patient.patient_id,
                scheduled_for=sched_time,
                module="post_discharge",
                call_type="retry",
                protocol_name="missed_call_retry",
                status="completed",
            )
            db.add(sched)

            call = CallRecord(
                patient_id=patient.patient_id,
                direction="outbound",
                trigger_type="scheduled",
                day_in_recovery=1,
                status="completed",
                started_at=call_time,
                call_type=None,
            )
            db.add(call)
            await db.flush()

            # Run the backfill SQL on this patient's rows only.
            await db.execute(text(
                """
                WITH matches AS (
                    SELECT DISTINCT ON (cr.call_id)
                        cr.call_id,
                        cs.call_type AS sched_call_type
                    FROM call_records cr
                    JOIN call_schedule cs ON cs.patient_id = cr.patient_id
                    WHERE cr.call_type IS NULL
                      AND cr.patient_id = :pid
                      AND ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) <= 900
                    ORDER BY cr.call_id,
                             ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) ASC
                )
                UPDATE call_records cr
                SET call_type = m.sched_call_type
                FROM matches m
                WHERE cr.call_id = m.call_id
                """
            ), {"pid": str(patient.patient_id)})
            await db.flush()

            reread = (await db.execute(
                select(CallRecord)
                .where(CallRecord.call_id == call.call_id)
                .execution_options(populate_existing=True)
            )).scalar_one()
            assert reread.call_type == "retry"

            await db.execute(delete(CallRecord).where(CallRecord.call_id == call.call_id))
            await db.execute(delete(CallSchedule).where(CallSchedule.schedule_id == sched.schedule_id))
            await db.execute(delete(Patient).where(Patient.patient_id == patient.patient_id))
            await db.commit()
        return "ok"

    _skip_if_needed(_run(_body))


def test_backfill_does_not_match_beyond_15min():
    """16 minutes off → no match → call_type stays NULL."""
    async def _body(Session):
        async with Session() as db:
            hosp = (await db.execute(select(Hospital).limit(1))).scalar_one_or_none()
            if hosp is None:
                hosp = Hospital(hospital_name="Fix3 Test H2", nhs_trust_name="Trust")
                db.add(hosp)
                await db.flush()

            patient = _make_scenario(hosp.hospital_id)
            db.add(patient)
            await db.flush()

            sched_time = datetime.now(timezone.utc).replace(microsecond=0)
            call_time = sched_time - timedelta(minutes=16)

            sched = CallSchedule(
                patient_id=patient.patient_id,
                scheduled_for=sched_time,
                module="post_discharge",
                call_type="retry",
                protocol_name="missed_call_retry",
                status="completed",
            )
            db.add(sched)

            call = CallRecord(
                patient_id=patient.patient_id,
                direction="outbound",
                trigger_type="scheduled",
                day_in_recovery=1,
                status="completed",
                started_at=call_time,
                call_type=None,
            )
            db.add(call)
            await db.flush()

            await db.execute(text(
                """
                WITH matches AS (
                    SELECT DISTINCT ON (cr.call_id)
                        cr.call_id, cs.call_type AS sched_call_type
                    FROM call_records cr
                    JOIN call_schedule cs ON cs.patient_id = cr.patient_id
                    WHERE cr.call_type IS NULL
                      AND cr.patient_id = :pid
                      AND ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) <= 900
                    ORDER BY cr.call_id,
                             ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) ASC
                )
                UPDATE call_records cr
                SET call_type = m.sched_call_type
                FROM matches m
                WHERE cr.call_id = m.call_id
                """
            ), {"pid": str(patient.patient_id)})
            await db.flush()

            reread = (await db.execute(
                select(CallRecord)
                .where(CallRecord.call_id == call.call_id)
                .execution_options(populate_existing=True)
            )).scalar_one()
            assert reread.call_type is None

            await db.execute(delete(CallRecord).where(CallRecord.call_id == call.call_id))
            await db.execute(delete(CallSchedule).where(CallSchedule.schedule_id == sched.schedule_id))
            await db.execute(delete(Patient).where(Patient.patient_id == patient.patient_id))
            await db.commit()
        return "ok"

    _skip_if_needed(_run(_body))


def test_backfill_closest_wins_on_ambiguous_match():
    """Two schedules within ±15min. Closest wins."""
    async def _body(Session):
        async with Session() as db:
            hosp = (await db.execute(select(Hospital).limit(1))).scalar_one_or_none()
            if hosp is None:
                hosp = Hospital(hospital_name="Fix3 Test H3", nhs_trust_name="Trust")
                db.add(hosp)
                await db.flush()

            patient = _make_scenario(hosp.hospital_id)
            db.add(patient)
            await db.flush()

            call_time = datetime.now(timezone.utc).replace(microsecond=0)
            # Schedule A: 14 minutes before (closer). call_type='routine'
            sched_a = CallSchedule(
                patient_id=patient.patient_id,
                scheduled_for=call_time - timedelta(minutes=14),
                module="post_discharge",
                call_type="routine",
                protocol_name="standard",
                status="completed",
            )
            # Schedule B: 2 minutes after (closest). call_type='retry'
            sched_b = CallSchedule(
                patient_id=patient.patient_id,
                scheduled_for=call_time + timedelta(minutes=2),
                module="post_discharge",
                call_type="retry",
                protocol_name="missed_call_retry",
                status="completed",
            )
            db.add(sched_a)
            db.add(sched_b)

            call = CallRecord(
                patient_id=patient.patient_id,
                direction="outbound",
                trigger_type="scheduled",
                day_in_recovery=1,
                status="completed",
                started_at=call_time,
                call_type=None,
            )
            db.add(call)
            await db.flush()

            await db.execute(text(
                """
                WITH matches AS (
                    SELECT DISTINCT ON (cr.call_id)
                        cr.call_id, cs.call_type AS sched_call_type
                    FROM call_records cr
                    JOIN call_schedule cs ON cs.patient_id = cr.patient_id
                    WHERE cr.call_type IS NULL
                      AND cr.patient_id = :pid
                      AND ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) <= 900
                    ORDER BY cr.call_id,
                             ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) ASC
                )
                UPDATE call_records cr
                SET call_type = m.sched_call_type
                FROM matches m
                WHERE cr.call_id = m.call_id
                """
            ), {"pid": str(patient.patient_id)})
            await db.flush()

            reread = (await db.execute(
                select(CallRecord)
                .where(CallRecord.call_id == call.call_id)
                .execution_options(populate_existing=True)
            )).scalar_one()
            # Schedule B (2min) is closer than Schedule A (14min).
            assert reread.call_type == "retry"

            await db.execute(delete(CallRecord).where(CallRecord.call_id == call.call_id))
            await db.execute(delete(CallSchedule).where(
                CallSchedule.schedule_id.in_([sched_a.schedule_id, sched_b.schedule_id])
            ))
            await db.execute(delete(Patient).where(Patient.patient_id == patient.patient_id))
            await db.commit()
        return "ok"

    _skip_if_needed(_run(_body))


def test_probe_trigger_type_already_backfilled_on_dev():
    """Smoke check that the migration's probe backfill step worked on dev:
    any CallRecord with trigger_type='probe' has call_type='probe'."""
    async def _body(Session):
        async with Session() as db:
            result = (await db.execute(
                select(CallRecord).where(CallRecord.trigger_type == "probe").limit(5)
            )).scalars().all()
            if not result:
                return "skip_no_probes"
            for row in result:
                assert row.call_type == "probe", (
                    f"Probe call {row.call_id} has call_type={row.call_type!r}; "
                    f"expected 'probe' after Fix 3 backfill"
                )
        return "ok"

    result = _run(_body)
    _skip_if_needed(result)
    if result == "skip_no_probes":
        pytest.skip("No probe CallRecords in dev DB")
