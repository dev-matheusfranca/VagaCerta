from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit.chain import GENESIS, digest
from audit.models import AuditRecord

# Um único escritor por vez: sem isso, duas réplicas poderiam encadear no mesmo registro anterior.
CHAIN_LOCK = 0x617564697400


async def record(session: AsyncSession, topic: str, payload: dict[str, Any]) -> bool:
    """Grava o evento no fim da corrente; devolve False se ele já estava registrado."""
    await session.execute(select(func.pg_advisory_xact_lock(CHAIN_LOCK)))
    event_id = UUID(payload["event_id"])
    if await session.scalar(select(AuditRecord.seq).where(AuditRecord.event_id == event_id)):
        await session.rollback()
        return False
    last = await session.scalar(select(AuditRecord.hash).order_by(AuditRecord.seq.desc()).limit(1))
    prev_hash = last or GENESIS
    data = payload.get("data", {})
    session.add(
        AuditRecord(
            event_id=event_id,
            topic=topic,
            type=payload["type"],
            business_id=data.get("business_id"),
            booking_id=data.get("booking_id"),
            occurred_at=datetime.fromisoformat(payload["occurred_at"]),
            payload=payload,
            prev_hash=prev_hash,
            hash=digest(prev_hash, topic, payload),
        )
    )
    await session.commit()
    return True
