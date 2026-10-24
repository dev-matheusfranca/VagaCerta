import uuid
from datetime import date

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DailyStats(Base):
    """Read model: números de um estabelecimento por dia de atendimento."""

    __tablename__ = "daily_stats"

    business_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(primary_key=True)
    bookings: Mapped[int] = mapped_column(default=0, server_default="0")
    cancellations: Mapped[int] = mapped_column(default=0, server_default="0")
    revenue_cents: Mapped[int] = mapped_column(default=0, server_default="0")
    offers: Mapped[int] = mapped_column(default=0, server_default="0")
    offers_claimed: Mapped[int] = mapped_column(default=0, server_default="0")
    offers_expired: Mapped[int] = mapped_column(default=0, server_default="0")
    recovered_revenue_cents: Mapped[int] = mapped_column(default=0, server_default="0")


class Booking(Base):
    """O que um cancelamento precisa saber do agendamento que ele desfaz."""

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    business_id: Mapped[uuid.UUID]
    day: Mapped[date]
    price_cents: Mapped[int]


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
