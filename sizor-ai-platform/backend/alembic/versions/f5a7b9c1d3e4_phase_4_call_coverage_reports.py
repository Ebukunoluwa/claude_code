"""phase 4 call_coverage_reports table

Revision ID: f5a7b9c1d3e4
Revises: e4f6a8c0b5d2
Create Date: 2026-04-24

Phase 4 coverage enforcement. Creates the call_coverage_reports table
that stores one row per call, populated by pipeline_tasks.py Task 1b
after clinical extraction runs.

Schema matches app.models.call.CallCoverageReport 1:1. Adding fields
requires updating BOTH this migration (new migration, not editing
this one) AND the ORM class — ORM↔DB parity test guards against drift.

Columns:
  coverage_report_id UUID PK
  call_id UUID FK -> call_records.call_id (not nullable)
  patient_id UUID FK -> patients.patient_id (not nullable)
  opcs_code VARCHAR(20) NULL — denormalised from pathway lookup
  day_in_recovery INTEGER NULL
  required_questions_expected / _asked / _patient_declined JSONB
  red_flag_probes_expected / _asked / _positive JSONB
  socrates_probes_triggered / _completed JSONB
  coverage_percentage DOUBLE PRECISION NULL — computed in Python
  incomplete_items JSONB
  raw_classifier_output JSONB — full LLM response, audit only
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()

Indexes:
  ix_call_coverage_reports_patient_created (patient_id, created_at DESC)
    Supports dashboard-style "last N coverage reports for patient X"
    queries without a sequential scan on the full table.

Downgrade drops the table unconditionally. No backfill on upgrade —
the table is populated prospectively from the next pipeline run.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f5a7b9c1d3e4"
down_revision: Union[str, None] = "e4f6a8c0b5d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_coverage_reports",
        sa.Column(
            "coverage_report_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_records.call_id"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.patient_id"),
            nullable=False,
        ),
        sa.Column("opcs_code", sa.String(20), nullable=True),
        sa.Column("day_in_recovery", sa.Integer, nullable=True),
        sa.Column(
            "required_questions_expected",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "required_questions_asked",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "required_questions_patient_declined",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "red_flag_probes_expected",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "red_flag_probes_asked",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "red_flag_probes_positive",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "socrates_probes_triggered",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "socrates_probes_completed",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("coverage_percentage", sa.Float, nullable=True),
        sa.Column(
            "incomplete_items",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "raw_classifier_output",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_call_coverage_reports_patient_created",
        "call_coverage_reports",
        ["patient_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_call_coverage_reports_patient_created",
        table_name="call_coverage_reports",
    )
    op.drop_table("call_coverage_reports")
