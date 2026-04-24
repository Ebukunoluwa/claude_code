"""ORM <-> DB schema parity test.

The systemic fix for PLAN.md §PY4. This class of drift bug has fired
five times in this codebase:
  1-4. Four orphan tables (domain_scores, patient_pathways,
       patient_red_flags, pathway_soap_notes) exist in the DB but have
       no SQLAlchemy model.
  5.   Phase 1 added extraction_status / extraction_status_reason to
       clinical_extractions via migration but forgot the ORM update,
       breaking the reprocess script at runtime.

What this test catches:
  - Columns present in the DB but not declared on the ORM model.
  - Columns declared on the ORM model but missing from the DB.
  - Column TYPE drift (e.g. VARCHAR->INTEGER, TIMESTAMP vs TIMESTAMPTZ,
    SMALLINT vs INTEGER) for columns that exist on both sides.
  - Column NULLABILITY drift (ORM says nullable, DB says NOT NULL or
    vice versa).

What this test intentionally does NOT catch:
  - Orphan tables — DB tables with no corresponding ORM model at all.
    That's a product decision (see PLAN.md §6 D2), not drift.
  - Server-default drift — default-value string representations differ
    too much between ORM declaration and PostgreSQL reflection to
    compare cleanly. Deferred to a dedicated test if needed.

Skips cleanly if the dev DB is unreachable so local developers without
Docker running aren't blocked.

Run: PYTHONPATH=. python -m pytest tests/test_orm_db_schema_parity.py -v
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import MetaData, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
# Importing app.models populates Base.metadata with every declared table.
import app.models  # noqa: F401
from app.database import Base


_PG_DIALECT = postgresql.dialect()


# PostgreSQL aliases that reflection and ORM compilation render differently
# but that are the same physical type. These are NOT drift — they're
# stringification differences in SQLAlchemy's type-to-DDL pipeline.
_PG_TYPE_ALIASES = {
    "DOUBLE PRECISION": "FLOAT",                 # SQLAlchemy Float() <-> PG float8
    "TIMESTAMP WITHOUT TIME ZONE": "TIMESTAMP",  # default timestamp form
    "CHARACTER VARYING": "VARCHAR",              # full name vs abbreviation
    "INT4": "INTEGER",
    "INT2": "SMALLINT",
    "INT8": "BIGINT",
}


def _normalise_type(t) -> str:
    """Render a SQLAlchemy type as its PostgreSQL DDL form and collapse
    known-equivalent aliases.

    Uses dialect.compile() rather than str() because str(Uuid()) renders
    as 'CHAR(32)' (the DB-agnostic fallback) while compile(dialect=pg)
    correctly renders 'UUID'. Same trap hit clinical_knowledge.id and
    domain_benchmarks.id on first run of the strengthened test.
    """
    try:
        compiled = t.compile(dialect=_PG_DIALECT).upper()
    except Exception:
        # Some types (pgvector Vector, ARRAY of custom types) may not
        # compile cleanly under a generic dialect instance; fall back to
        # str() so those columns still get name-level parity.
        compiled = str(t).upper()

    # Strip any trailing COLLATE / constraint noise.
    compiled = compiled.split(" COLLATE ")[0].strip()

    for alias, canonical in _PG_TYPE_ALIASES.items():
        # Only replace whole-token matches to avoid mangling embedded
        # substrings (e.g. VARCHAR inside CHARACTER VARYING).
        if compiled == alias or compiled.startswith(alias + "("):
            compiled = compiled.replace(alias, canonical, 1)
            break

    return compiled


def test_orm_tables_match_db_schema():
    """Every ORM-declared table must match the DB on column names, types,
    and nullability. Mismatches in any direction fail the test with an
    itemised report."""
    async def _run():
        engine = create_async_engine(settings.database_url)
        try:
            # Smoke-check connectivity — cleanly skip if dev DB down.
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            except OperationalError as exc:
                return ("skip", str(exc))

            # Reflect every ORM-modelled table from the live DB.
            reflected = MetaData()
            orm_table_names = list(Base.metadata.tables.keys())
            async with engine.connect() as conn:
                await conn.run_sync(
                    lambda sync_conn: reflected.reflect(
                        sync_conn, only=orm_table_names,
                    )
                )

            report: list[str] = []
            for tablename in sorted(orm_table_names):
                orm_table = Base.metadata.tables[tablename]
                db_table = reflected.tables.get(tablename)
                if db_table is None:
                    report.append(
                        f"  [{tablename}] declared in ORM but table not present in DB"
                    )
                    continue

                orm_cols = {c.name: c for c in orm_table.columns}
                db_cols = {c.name: c for c in db_table.columns}

                # -- Column presence --
                missing_on_model = set(db_cols) - set(orm_cols)
                missing_on_db = set(orm_cols) - set(db_cols)
                if missing_on_model:
                    report.append(
                        f"  [{tablename}] columns in DB not declared on ORM: "
                        f"{sorted(missing_on_model)}"
                    )
                if missing_on_db:
                    report.append(
                        f"  [{tablename}] columns on ORM not present in DB: "
                        f"{sorted(missing_on_db)}"
                    )

                # -- Column type + nullability --
                for colname in sorted(set(orm_cols) & set(db_cols)):
                    orm_col = orm_cols[colname]
                    db_col = db_cols[colname]

                    orm_type = _normalise_type(orm_col.type)
                    db_type = _normalise_type(db_col.type)
                    if orm_type != db_type:
                        report.append(
                            f"  [{tablename}.{colname}] TYPE drift: "
                            f"ORM={orm_type!r} DB={db_type!r}"
                        )

                    # Primary-key columns are implicitly NOT NULL in SQLAlchemy
                    # regardless of how they were declared; skip nullability
                    # on PKs to avoid false positives.
                    if not orm_col.primary_key:
                        if bool(orm_col.nullable) != bool(db_col.nullable):
                            report.append(
                                f"  [{tablename}.{colname}] NULLABILITY drift: "
                                f"ORM nullable={orm_col.nullable} "
                                f"DB nullable={db_col.nullable}"
                            )

            return ("ok", orm_table_names, report)
        finally:
            await engine.dispose()

    result = asyncio.run(_run())
    if result[0] == "skip":
        pytest.skip(f"DB unreachable: {result[1]}")
    _, orm_tables, report = result
    assert not report, (
        f"ORM<->DB schema drift detected across {len(orm_tables)} "
        f"declared tables:\n" + "\n".join(report)
    )
