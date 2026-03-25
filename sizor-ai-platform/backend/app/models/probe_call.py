import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class ProbeCall(Base):
    __tablename__ = "probe_calls"

    probe_call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    clinician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    call_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending/initiated/completed/failed
    call_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    soap_note_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    prompt_source: Mapped[str] = mapped_column(String(20), default="llm")  # llm / fallback
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
