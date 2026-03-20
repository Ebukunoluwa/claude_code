import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class LongitudinalSummary(Base):
    __tablename__ = "longitudinal_summaries"

    summary_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    triggered_by_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=True)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    active_concerns_snapshot: Mapped[list] = mapped_column(JSONB, default=list)
    trend_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    clinician_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    clinician_edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient = relationship("Patient", back_populates="longitudinal_summaries")


class FTPRecord(Base):
    __tablename__ = "ftp_records"

    ftp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    day_in_recovery: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    actual_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    variance_per_domain: Mapped[dict] = mapped_column(JSONB, default=dict)
    ftp_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reasoning_text: Mapped[str] = mapped_column(Text, nullable=False)

    patient = relationship("Patient", back_populates="ftp_records")
    call = relationship("CallRecord", back_populates="ftp_record")


class ClinicalDecision(Base):
    __tablename__ = "clinical_decisions"

    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=False)
    clinician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    clinical_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    differential_diagnoses: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSONB, default=list)
    risk_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty_flags: Mapped[list] = mapped_column(JSONB, default=list)
    nice_references: Mapped[list] = mapped_column(JSONB, default=list)
    full_reasoning_text: Mapped[str] = mapped_column(Text, nullable=False)
    clinician_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinician_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actioned: Mapped[bool] = mapped_column(Boolean, default=False)

    patient = relationship("Patient", back_populates="decisions")
    call = relationship("CallRecord", back_populates="decisions")
    clinician = relationship("Clinician", foreign_keys=[clinician_id])


class CallSchedule(Base):
    __tablename__ = "call_schedule"

    schedule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    day_in_recovery_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_type: Mapped[str] = mapped_column(String(20), nullable=False, default="routine")
    protocol_name: Mapped[str] = mapped_column(String(100), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    triggered_by_action_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="schedule")
