"""phase 2.5 probe isolation: probe_answers table + questions_list + scoring_scope

Revision ID: d3e5f7a9b2c4
Revises: b1c3d5e7f91a
Create Date: 2026-04-24

Phase 2.5 Fix 1 schema changes. Three additions:

  1. clinical_extractions.scoring_scope (VARCHAR(20) NOT NULL DEFAULT 'full')
     Values: 'full' | 'probe_focused'. Set to 'probe_focused' at pipeline
     time for any extraction from a CallRecord.trigger_type='probe' call.
     Dashboard metadata so frontend can render probe scores distinctly
     from longitudinal risk (frontend change out of Phase 2.5 scope).

  2. probe_calls.questions_list (JSONB NOT NULL DEFAULT '[]')
     Structured list of the clinician's probe questions, extracted at
     POST /probe-calls time. Phase 2.5 uses whatever _extract_questions()
     returns; Phase 4 will refine with explicit clinician tagging.

  3. probe_answers table (new)
     One row per probe question, written at ingest time with
     extraction_status='pending'. Full transcript-to-answer extraction
     (patient_answer, confidence, asked_at) is Phase 4 scope; Phase 2.5
     lands the scaffolding and ingest hook.

Downgrade reverses all three. The probe_answers table is dropped; any
rows populated in Phase 4 would be lost on a downgrade after that point.

Base revision: b1c3d5e7f91a (Phase 1 data integrity). This migration
does NOT depend on the orphan-drop revision (c2e4a6f801b3, awaiting
PR) — the orphan-drop branch has its own independent head off the
same Phase 1 base. When both merge to main, Alembic sees a branch
point that can either be merged via `alembic merge` or left parallel
if neither depends on the other. Neither does — the orphan-drop
removes tables this migration doesn't touch.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d3e5f7a9b2c4"
down_revision: Union[str, None] = "c2e4a6f801b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. scoring_scope on clinical_extractions.
    op.add_column(
        "clinical_extractions",
        sa.Column(
            "scoring_scope",
            sa.String(20),
            nullable=False,
            server_default="full",
        ),
    )

    # 2. questions_list on probe_calls.
    op.add_column(
        "probe_calls",
        sa.Column(
            "questions_list",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # 3. probe_answers table.
    op.create_table(
        "probe_answers",
        sa.Column(
            "probe_answer_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "probe_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("probe_calls.probe_call_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt_question", sa.Text(), nullable=False),
        sa.Column("patient_answer", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(10), nullable=True),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "extraction_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_probe_answers_probe_call_id",
        "probe_answers",
        ["probe_call_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_probe_answers_probe_call_id", table_name="probe_answers")
    op.drop_table("probe_answers")
    op.drop_column("probe_calls", "questions_list")
    op.drop_column("clinical_extractions", "scoring_scope")
