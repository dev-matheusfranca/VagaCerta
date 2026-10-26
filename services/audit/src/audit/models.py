import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditRecord(Base):
    """Um evento de domínio, gravado uma vez e nunca alterado, encadeado ao anterior pelo hash."""

    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    topic: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(100))
    business_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
