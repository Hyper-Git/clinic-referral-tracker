"""The referrals table."""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

PRIORITIES = ("urgent", "routine")
STATUSES = ("received", "triaged", "booked", "seen")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    referring_practice: Mapped[str] = mapped_column(String(120), nullable=False)
    priority: Mapped[str] = mapped_column(
        Enum(*PRIORITIES, name="referral_priority", native_enum=False, create_constraint=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(*STATUSES, name="referral_status", native_enum=False, create_constraint=True),
        nullable=False,
        default="received",
    )
    date_received: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
