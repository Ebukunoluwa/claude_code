"""phase 2.5 call_type on CallRecord + backfill from CallSchedule proximity

Revision ID: e4f6a8c0b5d2
Revises: d3e5f7a9b2c4
Create Date: 2026-04-24

Phase 2.5 Fix 3. Adds call_records.call_type and backfills historical
rows by matching each CallRecord.started_at to the closest
CallSchedule.scheduled_for within a 15-minute window.

Schema:
  call_records.call_type VARCHAR(20) NULL
    New column. Nullable for legacy rows that the backfill can't match.
    New rows populated at ingest (app/api/calls.py) going forward.

Backfill:
  For each CallRecord with call_type IS NULL:
    1. If trigger_type='probe' or probe_call_id (not a column, but
       present in voice-agent payloads that set trigger_type='probe')
       -> set call_type = 'probe' directly. Probes bypass CallSchedule.
    2. Else find CallSchedule matching by patient_id with
       |scheduled_for - started_at| <= INTERVAL '15 minutes', closest
       delta wins -> set call_type from that schedule.
    3. Else leave NULL and log as unmatched.

The 15-minute window is defended in PLAN.md Phase 2.5 Q3: tight
enough to avoid cross-matching schedules in high-frequency clusters;
loose enough to absorb Celery queue backlog under load.

Downgrade drops the column. Backfill data is lost; subsequent runs
can re-backfill deterministically from the same CallSchedule history.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f6a8c0b5d2"
down_revision: Union[str, None] = "d3e5f7a9b2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the column nullable for legacy rows.
    op.add_column(
        "call_records",
        sa.Column("call_type", sa.String(20), nullable=True),
    )

    # 2. Backfill probes — any row with trigger_type='probe' gets
    #    call_type='probe'.
    op.execute(
        """
        UPDATE call_records
        SET call_type = 'probe'
        WHERE call_type IS NULL
          AND trigger_type = 'probe'
        """
    )

    # 3. Backfill non-probe rows from CallSchedule proximity.
    #    DISTINCT ON picks the closest schedule per call_record by
    #    absolute time delta within the 15-minute window.
    op.execute(
        """
        WITH matches AS (
            SELECT DISTINCT ON (cr.call_id)
                cr.call_id,
                cs.call_type AS sched_call_type,
                ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) AS delta_sec
            FROM call_records cr
            JOIN call_schedule cs ON cs.patient_id = cr.patient_id
            WHERE cr.call_type IS NULL
              AND cr.started_at IS NOT NULL
              AND ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at)))
                  <= 15 * 60
            ORDER BY cr.call_id,
                     ABS(EXTRACT(EPOCH FROM (cs.scheduled_for - cr.started_at))) ASC
        )
        UPDATE call_records cr
        SET call_type = m.sched_call_type
        FROM matches m
        WHERE cr.call_id = m.call_id
          AND cr.call_type IS NULL
        """
    )

    # 4. Log the unmatched count for operator awareness. Alembic shows
    #    NOTICE output; this gives a running tally in the upgrade log.
    op.execute(
        """
        DO $$
        DECLARE
            unmatched_count INTEGER;
            total_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO total_count FROM call_records;
            SELECT COUNT(*) INTO unmatched_count
                FROM call_records WHERE call_type IS NULL;
            RAISE NOTICE 'call_type backfill: % of % rows remain unmatched (NULL).',
                unmatched_count, total_count;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_column("call_records", "call_type")
