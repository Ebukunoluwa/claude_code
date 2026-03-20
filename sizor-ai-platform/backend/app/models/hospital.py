import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    hospital_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_name: Mapped[str] = mapped_column(String(255), nullable=False)
    nhs_trust: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    active_modules: Mapped[list] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    wards = relationship("Ward", back_populates="hospital")
    clinicians = relationship("Clinician", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
