from collections.abc import AsyncIterator, Sequence
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.models import DailyStats
from vagacerta_auth import Claims, require_role

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
Owner = Annotated[Claims, Depends(require_role("owner"))]


class DayStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    bookings: int
    cancellations: int
    revenue_cents: int
    offers: int
    offers_claimed: int
    offers_expired: int
    recovered_revenue_cents: int


@router.get("/businesses/{business_id}/stats", response_model=list[DayStats])
async def get_stats(
    business_id: UUID,
    session: Session,
    claims: Owner,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> Sequence[DailyStats]:
    if str(business_id) not in claims.get("businesses", []):
        raise HTTPException(403, "Você não tem acesso a este estabelecimento")
    stats = await session.scalars(
        select(DailyStats)
        .where(DailyStats.business_id == business_id, DailyStats.day.between(start, end))
        .order_by(DailyStats.day)
    )
    return stats.all()
