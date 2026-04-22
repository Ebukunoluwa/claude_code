"""add smoothed_scores and risk_score to clinical_extractions

Revision ID: a0b70007db93
Revises:
Create Date: 2026-04-22 10:06:13.806632

MANUALLY EDITED: the autogenerate output wanted to drop several tables
(domain_scores, patient_pathways, patient_red_flags, pathway_soap_notes)
that exist in the DB but are not yet represented as SQLAlchemy models.
Those drops have been REMOVED from this migration. This migration only
adds three columns to clinical_extractions, nothing else.

The model/DB drift should be addressed separately by reflecting those
tables as SQLAlchemy models.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a0b70007db93'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # JSONB columns need a server_default so existing rows get an empty object.
    op.add_column(
        'clinical_extractions',
        sa.Column(
            'smoothed_scores',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        'clinical_extractions',
        sa.Column('risk_score', sa.Float(), nullable=True),
    )
    op.add_column(
        'clinical_extractions',
        sa.Column(
            'risk_score_breakdown',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column('clinical_extractions', 'risk_score_breakdown')
    op.drop_column('clinical_extractions', 'risk_score')
    op.drop_column('clinical_extractions', 'smoothed_scores')
