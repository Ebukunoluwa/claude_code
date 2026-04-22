import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, SmallInteger, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class DomainBenchmark(Base):
    __tablename__ = "domain_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        "id",
        default=uuid.uuid4,
        primary_key=True,
    )
    opcs_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    day_range_start: Mapped[int] = mapped_column(Integer, nullable=False)
    day_range_end: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    upper_bound_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    expected_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    nice_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nice_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(20), default="routine")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
