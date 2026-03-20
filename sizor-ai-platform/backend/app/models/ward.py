import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Ward(Base):
    __tablename__ = "wards"

    ward_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hospitals.hospital_id"), nullable=False)
    ward_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(255), nullable=False)
    escalation_contacts: Mapped[dict] = mapped_column(JSONB, default=dict)

    hospital = relationship("Hospital", back_populates="wards")
    clinicians = relationship("Clinician", back_populates="ward")
    patients = relationship("Patient", back_populates="ward")
