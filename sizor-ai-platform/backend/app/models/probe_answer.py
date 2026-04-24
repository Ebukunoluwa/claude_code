"""ProbeAnswer — one row per clinician-requested probe question.

Phase 2.5 Fix 1 scaffolding. Ingest writes these rows at the moment a probe
call is ingested, one per entry in ProbeCall.questions_list, with
extraction_status='pending'. The actual transcript-to-answer extraction
(populating patient_answer / confidence / asked_at) is Phase 4 scope.

The table is the coverage audit trail for the specific questions the
clinician asked — separate from the broader ClinicalExtraction which
carries the domain-score view of the call.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ProbeAnswer(Base):
    __tablename__ = "probe_answers"

    probe_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    probe_call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("probe_calls.probe_call_id", ondelete="CASCADE"),
        nullable=False,
    )
    prompt_question: Mapped[str] = mapped_column(Text, nullable=False)
    patient_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Enum-like VARCHAR: 'high' | 'medium' | 'low'. Populated in Phase 4.
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    asked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Enum-like VARCHAR: 'pending' | 'extracted' | 'failed'.
    extraction_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
