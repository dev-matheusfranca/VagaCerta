import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)


class Booking(Base):
    """Projeção local dos agendamentos, alimentada pelos eventos do Booking."""

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
