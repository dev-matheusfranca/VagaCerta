from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit.chain import first_broken
from audit.models import AuditRecord
from vagacerta_auth import Claims, require_role

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
Owner = Annotated[Claims, Depends(require_role("owner"))]
Admin = Depends(require_role("admin"))


class TrailEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    type: str
    occurred_at: datetime
    hash: str


class Verification(BaseModel):
    records: int
    valid: bool
    broken_at: int | None


@router.get("/bookings/{booking_id}/trail", response_model=list[TrailEntry])
async def get_trail(booking_id: UUID, session: Session, claims: Owner) -> Sequence[AuditRecord]:
    """Tudo o que aconteceu com um agendamento, na ordem em que foi registrado."""
    records = (
        await session.scalars(
            select(AuditRecord)
            .where(AuditRecord.booking_id == booking_id)
            .order_by(AuditRecord.seq)
        )
    ).all()
    if not records:
        raise HTTPException(404, "Nenhum registro para este agendamento")
    if str(records[0].business_id) not in claims.get("businesses", []):
        raise HTTPException(403, "Você não tem acesso a este estabelecimento")
    return records


@router.get("/verify", response_model=Verification, dependencies=[Admin])
async def verify(session: Session) -> Verification:
    """Recalcula a corrente inteira e aponta o primeiro registro adulterado, se houver."""
    rows = (
        await session.execute(
            select(
                AuditRecord.seq,
                AuditRecord.topic,
                AuditRecord.payload,
                AuditRecord.prev_hash,
                AuditRecord.hash,
            ).order_by(AuditRecord.seq)
        )
    ).all()
    broken_at = first_broken(tuple(row) for row in rows)
    return Verification(records=len(rows), valid=broken_at is None, broken_at=broken_at)
