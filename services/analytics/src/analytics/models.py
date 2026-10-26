import uuid
from datetime import date

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DailyStats(Base):
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
    completed: Mapped[int] = mapped_column(default=0, server_default="0")
    no_shows: Mapped[int] = mapped_column(default=0, server_default="0")
    booked_minutes: Mapped[int] = mapped_column(default=0, server_default="0")


class HourlyStats(Base):
    """Agendamentos por dia da semana e hora, no fuso do estabelecimento."""

    __tablename__ = "hourly_stats"

    business_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    weekday: Mapped[int] = mapped_column(primary_key=True)
    hour: Mapped[int] = mapped_column(primary_key=True)
    bookings: Mapped[int] = mapped_column(default=0, server_default="0")


class Booking(Base):
    """O que um cancelamento precisa saber do agendamento que ele desfaz."""

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    business_id: Mapped[uuid.UUID]
    day: Mapped[date]
    price_cents: Mapped[int]
    minutes: Mapped[int] = mapped_column(server_default="0")
    weekday: Mapped[int] = mapped_column(server_default="0")
    hour: Mapped[int] = mapped_column(server_default="0")


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
