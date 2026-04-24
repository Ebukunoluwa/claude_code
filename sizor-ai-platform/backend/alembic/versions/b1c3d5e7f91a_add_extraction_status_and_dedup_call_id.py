"""add extraction_status, dedup, and unique call_id to clinical_extractions

Revision ID: b1c3d5e7f91a
Revises: a0b70007db93
Create Date: 2026-04-24

Phase 1 of the clinical intelligence refactor — data integrity.

Steps (executed in order; all within a single transaction):
  1. Create clinical_extraction_audit with full-row JSONB snapshot storage.
  2. Add columns extraction_status (varchar(30), NOT NULL default 'extracted')
     and extraction_status_reason (text, nullable) to clinical_extractions.
  3. Snapshot any duplicate rows (call_id with more than one extraction) into
     the audit table, keeping the most recent by extracted_at; delete the rest.
  4. Add a unique constraint on clinical_extractions.call_id.
  5. Backfill extraction_status based on data state. Order matters:
       stale_pre_calibration  — extracted_at < cutover (pipeline was not yet
                                producing domain_scores).
       failed                 — post-cutover row with no scalar scores, no raw
                                extraction json, and no condition-specific flags.
       empty                  — post-cutover row with raw_extraction_json populated
                                but no clinical signals recovered.
       extracted              — default; the server_default handles the rest.

Cutover:
  The stale_pre_calibration boundary is 2026-03-27 01:45:27.070384+00, the
  timestamp of the first clinical_extractions row whose condition_specific_flags
  contained a non-empty domain_scores object (confirmed against dev DB on
  2026-04-24). This is the earliest point at which the pipeline started
  producing domain scores on the post-calibration scale.

Reversibility:
  downgrade() drops the columns and the unique constraint, but does NOT
  restore deleted duplicate rows. The audit table retains a full JSONB
  snapshot of every deleted row for manual recovery if needed. A DB backup
  is still recommended as defence in depth.

Dev observation (2026-04-24):
  Dev had 0 duplicates at migration time; the dedup SQL is a no-op in dev
  but lands the unique constraint to prevent future drift. Any production
  duplicates will be captured in clinical_extraction_audit with full JSONB
  snapshots, preserving the recovery path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b1c3d5e7f91a'
down_revision: Union[str, None] = 'a0b70007db93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CUTOVER_TIMESTAMP = '2026-03-27 01:45:27.070384+00'


def upgrade() -> None:
    # 1. Audit table — full-row JSONB snapshots of rows removed by dedup.
    op.create_table(
        'clinical_extraction_audit',
        sa.Column(
            'audit_id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column(
            'performed_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.Column('source_extraction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_call_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'row_snapshot',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column('migration_revision', sa.String(32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index(
        'idx_clinical_extraction_audit_call_id',
        'clinical_extraction_audit',
        ['source_call_id'],
    )

    # 2. Columns. server_default keeps existing rows valid under the NOT NULL;
    #    step 5 refines the values.
    op.add_column(
        'clinical_extractions',
        sa.Column(
            'extraction_status',
            sa.String(30),
            nullable=False,
            server_default='extracted',
        ),
    )
    op.add_column(
        'clinical_extractions',
        sa.Column('extraction_status_reason', sa.Text(), nullable=True),
    )

    # 3. Snapshot duplicate rows into audit, then delete losers.
    #    "Loser" = not the most recent by (extracted_at DESC, extraction_id DESC)
    #    per call_id. Tiebreak on extraction_id is deterministic.
    op.execute(
        f"""
        INSERT INTO clinical_extraction_audit
            (action, source_extraction_id, source_call_id, source_patient_id,
             row_snapshot, migration_revision, notes)
        SELECT
            'dedup_delete',
            extraction_id,
            call_id,
            patient_id,
            to_jsonb(ce.*),
            '{revision}',
            'Duplicate extraction row removed; kept most recent per call_id'
        FROM (
            SELECT
                ce.*,
                ROW_NUMBER() OVER (
                    PARTITION BY call_id
                    ORDER BY extracted_at DESC, extraction_id DESC
                ) AS rn
            FROM clinical_extractions ce
        ) ce
        WHERE rn > 1
        """
    )
    op.execute(
        """
        DELETE FROM clinical_extractions
        WHERE extraction_id IN (
            SELECT extraction_id FROM (
                SELECT
                    extraction_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY call_id
                        ORDER BY extracted_at DESC, extraction_id DESC
                    ) AS rn
                FROM clinical_extractions
            ) t
            WHERE rn > 1
        )
        """
    )

    # 4. Unique constraint is safe now that duplicates are gone.
    op.create_unique_constraint(
        'uq_clinical_extractions_call_id',
        'clinical_extractions',
        ['call_id'],
    )

    # 5. Backfill extraction_status.
    op.execute(
        f"""
        UPDATE clinical_extractions
        SET extraction_status = 'stale_pre_calibration',
            extraction_status_reason =
                'Row predates calibration cutover {CUTOVER_TIMESTAMP}'
        WHERE extracted_at < '{CUTOVER_TIMESTAMP}'::timestamptz
        """
    )
    op.execute(
        """
        UPDATE clinical_extractions
        SET extraction_status = 'failed',
            extraction_status_reason =
                'No raw extraction and no domain signals recorded'
        WHERE extraction_status = 'extracted'
          AND pain_score IS NULL
          AND breathlessness_score IS NULL
          AND mobility_score IS NULL
          AND appetite_score IS NULL
          AND mood_score IS NULL
          AND (raw_extraction_json IS NULL OR raw_extraction_json = '{}'::jsonb)
          AND (condition_specific_flags IS NULL
               OR condition_specific_flags = '{}'::jsonb)
        """
    )
    op.execute(
        """
        UPDATE clinical_extractions
        SET extraction_status = 'empty',
            extraction_status_reason =
                'Extraction ran but found no clinical signals'
        WHERE extraction_status = 'extracted'
          AND pain_score IS NULL
          AND breathlessness_score IS NULL
          AND mobility_score IS NULL
          AND appetite_score IS NULL
          AND mood_score IS NULL
          AND raw_extraction_json IS NOT NULL
          AND raw_extraction_json != '{}'::jsonb
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_clinical_extractions_call_id',
        'clinical_extractions',
        type_='unique',
    )
    op.drop_column('clinical_extractions', 'extraction_status_reason')
    op.drop_column('clinical_extractions', 'extraction_status')
    op.drop_index(
        'idx_clinical_extraction_audit_call_id',
        table_name='clinical_extraction_audit',
    )
    op.drop_table('clinical_extraction_audit')
    # Duplicate rows deleted in upgrade() are NOT restored. Recover from the
    # audit table's row_snapshot column if needed:
    #   SELECT row_snapshot FROM clinical_extraction_audit
    #   WHERE action = 'dedup_delete' AND migration_revision = 'b1c3d5e7f91a';
