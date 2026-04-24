"""Pins ORM ↔ DB alignment for the two columns added in migration
b1c3d5e7f91a (extraction_status, extraction_status_reason).

Regression-tests the Phase 1 drift that broke the reprocess script: new
columns landed in the DB via migration but not in ClinicalExtraction, so
any attribute access raised. Any future column drift will fail here before
it fails at runtime.

The DB-touching tests skip cleanly if the dev DB is unreachable.

Run: PYTHONPATH=. python -m pytest tests/test_extraction_status_model.py -v
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import ClinicalExtraction


def _run_with_fresh_engine(coro_factory):
    """Each asyncio.run creates a new loop; asyncpg engines bind to a loop,
    so we build the engine inside the coroutine and dispose it on exit."""
    async def _wrap():
        engine = create_async_engine(settings.database_url)
        try:
            Session = async_sessionmaker(engine, expire_on_commit=False)
            # Smoke-check connectivity — cleanly skips if DB down.
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
    if result == "skip_empty":
        pytest.skip("No eligible rows in dev DB")


def test_orm_can_read_extraction_status():
    """Original breakage: ClinicalExtraction.extraction_status must exist
    on the ORM class and be readable on a real row."""
    async def _body(Session):
        async with Session() as db:
            row = (await db.execute(
                select(ClinicalExtraction)
                .where(ClinicalExtraction.extraction_status == "stale_pre_calibration")
                .limit(1)
            )).scalar_one_or_none()
            if row is None:
                return "skip_empty"
            assert row.extraction_status == "stale_pre_calibration"
            assert row.extraction_status_reason is not None
            assert "calibration cutover" in row.extraction_status_reason
            return "ok"

    _skip_if_needed(_run_with_fresh_engine(_body))


def test_orm_round_trip_write_then_read():
    """Write via the ORM, re-read, confirm persistence. Rolled back so the
    test is side-effect-free."""
    async def _body(Session):
        async with Session() as db:
            row = (await db.execute(
                select(ClinicalExtraction)
                .where(ClinicalExtraction.extraction_status == "stale_pre_calibration")
                .limit(1)
            )).scalar_one_or_none()
            if row is None:
                return "skip_empty"
            ext_id = row.extraction_id
            await db.execute(
                update(ClinicalExtraction)
                .where(ClinicalExtraction.extraction_id == ext_id)
                .values(
                    extraction_status="pending_reprocess",
                    extraction_status_reason="round-trip test marker",
                )
            )
            await db.flush()
            reread = (await db.execute(
                select(ClinicalExtraction)
                .where(ClinicalExtraction.extraction_id == ext_id)
            )).scalar_one()
            assert reread.extraction_status == "pending_reprocess"
            assert reread.extraction_status_reason == "round-trip test marker"
            await db.rollback()
            return "ok"

    _skip_if_needed(_run_with_fresh_engine(_body))


def test_reason_accepts_none():
    """extraction_status_reason is nullable — the ORM must permit None."""
    async def _body(Session):
        async with Session() as db:
            row = (await db.execute(
                select(ClinicalExtraction).limit(1)
            )).scalar_one_or_none()
            if row is None:
                return "skip_empty"
            ext_id = row.extraction_id
            await db.execute(
                update(ClinicalExtraction)
                .where(ClinicalExtraction.extraction_id == ext_id)
                .values(extraction_status_reason=None)
            )
            await db.flush()
            reread = (await db.execute(
                select(ClinicalExtraction)
                .where(ClinicalExtraction.extraction_id == ext_id)
            )).scalar_one()
            assert reread.extraction_status_reason is None
            await db.rollback()
            return "ok"

    _skip_if_needed(_run_with_fresh_engine(_body))


def test_extraction_status_attribute_is_declared():
    """Static ORM check — catches drift even with no DB access. Phase-1
    breakage was that these attributes didn't exist on the class at all."""
    assert hasattr(ClinicalExtraction, "extraction_status")
    assert hasattr(ClinicalExtraction, "extraction_status_reason")
    col = ClinicalExtraction.__table__.c.extraction_status
    assert col.nullable is False
    reason_col = ClinicalExtraction.__table__.c.extraction_status_reason
    assert reason_col.nullable is True
