import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class CallRecord(Base):
    __tablename__ = "call_records"

    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    clinician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    day_in_recovery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    probe_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Twilio CallSid
    outcome_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=True)

    patient = relationship("Patient", back_populates="calls")
    clinician = relationship("Clinician", foreign_keys=[clinician_id])
    extraction = relationship("ClinicalExtraction", back_populates="call", uselist=False)
    soap_note = relationship("SOAPNote", back_populates="call", uselist=False)
    urgency_flags = relationship("UrgencyFlag", back_populates="call")
    actions = relationship("ClinicianAction", back_populates="call", foreign_keys="ClinicianAction.call_id")
    ftp_record = relationship("FTPRecord", back_populates="call", uselist=False)
    decisions = relationship("ClinicalDecision", back_populates="call")


class ClinicalExtraction(Base):
    __tablename__ = "clinical_extractions"

    extraction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    pain_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    breathlessness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mobility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    appetite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    medication_adherence: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    condition_specific_flags: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_extraction_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    call = relationship("CallRecord", back_populates="extraction")


class SOAPNote(Base):
    __tablename__ = "soap_notes"

    soap_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    subjective: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    assessment: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    clinician_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    clinician_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    call = relationship("CallRecord", back_populates="soap_note")


class UrgencyFlag(Base):
    __tablename__ = "urgency_flags"

    flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=True)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    flag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open")
    assigned_to_clinician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=True)
    raised_by_clinician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient = relationship("Patient", back_populates="urgency_flags")
    call = relationship("CallRecord", back_populates="urgency_flags")


class ClinicianAction(Base):
    __tablename__ = "clinician_actions"

    action_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False)
    call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.call_id"), nullable=True)
    clinician_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    notes_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    probe_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    patient = relationship("Patient", back_populates="actions", foreign_keys=[patient_id])
    call = relationship("CallRecord", back_populates="actions", foreign_keys=[call_id])
    clinician = relationship("Clinician", back_populates="actions", foreign_keys=[clinician_id])
