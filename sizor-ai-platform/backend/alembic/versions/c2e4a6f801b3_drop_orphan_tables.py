"""drop orphan tables: domain_scores and pathway_soap_notes

Revision ID: c2e4a6f801b3
Revises: b1c3d5e7f91a
Create Date: 2026-04-24

Per PLAN.md Sec 6 D2 (revised by the Phase 2 post-review). Both tables
were defined in db/schema.sql but never written or read by any Python
code in the platform (verified via grep during the Phase 2 planning
pass — zero matches for any SELECT/INSERT/UPDATE/DELETE against either
table). Row counts at drop time: 0 and 0.

  domain_scores
    Duplicated condition_specific_flags.domain_scores JSONB, which is
    the authoritative source the pipeline writes and the dashboard
    reads. Promoting the table would require refactoring 30+ JSON-key
    access sites with no clinical benefit.

  pathway_soap_notes
    A per-domain SOAP split that was never populated. The general
    soap_notes table (modelled as SOAPNote) handles SOAP records in
    the live pipeline. Per-domain SOAP is not a Phase 3/4/5
    requirement; if clinicians later want it, revisit then.

patient_red_flags is NOT dropped in this migration. It has distinct
semantics from the modelled urgency_flags table (per-domain with
explicit resolution tracking) that Phase 4's patient-facing red-flag
probing will likely need. Left in the schema, with a clarifying
comment in db/schema.sql.

Irreversibility:
  downgrade() recreates both tables (and their indexes) from the
  original schema.sql definitions. It does NOT restore any row data —
  the tables were empty at drop time, so there is no data to preserve.
  If either table is ever populated and then dropped in a future run
  of this migration, that data will be lost; callers must gate
  downgrade carefully.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c2e4a6f801b3"
down_revision: Union[str, None] = "b1c3d5e7f91a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # domain_scores — 4 indexes + table
    op.execute("DROP INDEX IF EXISTS idx_domain_scores_patient_id")
    op.execute("DROP INDEX IF EXISTS idx_domain_scores_call_id")
    op.execute("DROP INDEX IF EXISTS idx_domain_scores_opcs_domain")
    op.execute("DROP INDEX IF EXISTS idx_domain_scores_escalation")
    op.execute("DROP TABLE IF EXISTS domain_scores")

    # pathway_soap_notes — 2 indexes + table
    op.execute("DROP INDEX IF EXISTS idx_pathway_soap_notes_patient_id")
    op.execute("DROP INDEX IF EXISTS idx_pathway_soap_notes_call_id")
    op.execute("DROP TABLE IF EXISTS pathway_soap_notes")


def downgrade() -> None:
    # Recreate pathway_soap_notes exactly as defined in db/schema.sql
    # at the time of the drop. Does not restore any data.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pathway_soap_notes (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id          UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
            call_id             UUID REFERENCES call_records(call_id) ON DELETE SET NULL,
            domain              VARCHAR(100) NOT NULL,
            subjective          TEXT,
            objective           TEXT,
            assessment          TEXT,
            plan                TEXT,
            nice_reference      VARCHAR(50),
            escalation_action   TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pathway_soap_notes_patient_id "
        "ON pathway_soap_notes(patient_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pathway_soap_notes_call_id "
        "ON pathway_soap_notes(call_id)"
    )

    # Recreate domain_scores
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_scores (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id          UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
            call_id             UUID REFERENCES call_records(call_id) ON DELETE SET NULL,
            opcs_code           VARCHAR(20) NOT NULL,
            domain              VARCHAR(100) NOT NULL,
            day_post_discharge  INTEGER NOT NULL,
            raw_response        TEXT,
            score               SMALLINT NOT NULL CHECK (score BETWEEN 0 AND 4),
            expected_score      SMALLINT,
            upper_bound_score   SMALLINT,
            above_upper_bound   BOOLEAN,
            trajectory          VARCHAR(30),
            ftp_flag            BOOLEAN NOT NULL DEFAULT FALSE,
            escalation_flag     BOOLEAN NOT NULL DEFAULT FALSE,
            escalation_tier     VARCHAR(20),
            scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_domain_scores_patient_id "
        "ON domain_scores(patient_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_domain_scores_call_id "
        "ON domain_scores(call_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_domain_scores_opcs_domain "
        "ON domain_scores(opcs_code, domain)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_domain_scores_escalation "
        "ON domain_scores(escalation_flag) WHERE escalation_flag = TRUE"
    )
