import uuid
from datetime import datetime, date, time, timezone
from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hospitals.hospital_id"), nullable=False)
    ward_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.ward_id"), nullable=True)
    assigned_clinician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clinicians.clinician_id"), nullable=True)
    nhs_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[str] = mapped_column(String(255), nullable=False)
    procedure: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    discharge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    program_module: Mapped[str] = mapped_column(String(50), nullable=False)  # post_discharge/post_surgery/routine_checks
    status: Mapped[str] = mapped_column(String(50), default="active")  # active/discharged/escalated/completed
    preferred_call_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    postcode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    hospital = relationship("Hospital", back_populates="patients")
    ward = relationship("Ward", back_populates="patients")
    assigned_clinician = relationship("Clinician", foreign_keys=[assigned_clinician_id])
    medical_profile = relationship("PatientMedicalProfile", back_populates="patient", uselist=False)
    calls = relationship("CallRecord", back_populates="patient")
    urgency_flags = relationship("UrgencyFlag", back_populates="patient")
    actions = relationship("ClinicianAction", back_populates="patient", foreign_keys="ClinicianAction.patient_id")
    longitudinal_summaries = relationship("LongitudinalSummary", back_populates="patient")
    ftp_records = relationship("FTPRecord", back_populates="patient")
    decisions = relationship("ClinicalDecision", back_populates="patient")
    schedule = relationship("CallSchedule", back_populates="patient")


class PatientMedicalProfile(Base):
    __tablename__ = "patient_medical_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=False, unique=True)
    primary_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_diagnoses: Mapped[list] = mapped_column(JSONB, default=list)
    current_medications: Mapped[list] = mapped_column(JSONB, default=list)
    allergies: Mapped[list] = mapped_column(JSONB, default=list)
    relevant_comorbidities: Mapped[list] = mapped_column(JSONB, default=list)
    discharge_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    consultant_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="medical_profile")
