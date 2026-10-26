from collections.abc import AsyncIterator, Sequence
from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.models import DailyStats, HourlyStats
from vagacerta_auth import Claims, require_role

router = APIRouter()
MAX_DAYS = 92


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
Owner = Annotated[Claims, Depends(require_role("owner"))]


class DayStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    bookings: int = 0
    cancellations: int = 0
    revenue_cents: int = 0
    offers: int = 0
    offers_claimed: int = 0
    offers_expired: int = 0
    recovered_revenue_cents: int = 0
    completed: int = 0
    no_shows: int = 0
    booked_minutes: int = 0
    capacity_minutes: int | None = None


class HourStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weekday: int
    hour: int
    bookings: int


def check_owner(claims: Claims, business_id: UUID) -> None:
    if str(business_id) not in claims.get("businesses", []):
        raise HTTPException(403, "Você não tem acesso a este estabelecimento")


@router.get("/businesses/{business_id}/stats", response_model=list[DayStats])
async def get_stats(
    business_id: UUID,
    request: Request,
    session: Session,
    claims: Owner,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> list[DayStats]:
    check_owner(claims, business_id)
    if not 0 <= (end - start).days < MAX_DAYS:
        raise HTTPException(422, f"Escolha um período de até {MAX_DAYS} dias")
    rows = await session.scalars(
        select(DailyStats).where(
            DailyStats.business_id == business_id, DailyStats.day.between(start, end)
        )
    )
    by_day = {row.day: DayStats.model_validate(row) for row in rows}
    # Sem o Catalog, os números saem sem a capacidade, e a ocupação fica em branco.
    schedule = await request.app.state.catalog.schedule(business_id)
    days = (start + timedelta(days=i) for i in range((end - start).days + 1))
    return [
        by_day.get(day, DayStats(day=day)).model_copy(
            update={"capacity_minutes": schedule.capacity_minutes(day) if schedule else None}
        )
        for day in days
    ]


@router.get("/businesses/{business_id}/peak-hours", response_model=list[HourStats])
async def get_peak_hours(
    business_id: UUID, session: Session, claims: Owner
) -> Sequence[HourlyStats]:
    check_owner(claims, business_id)
    hours = await session.scalars(
        select(HourlyStats)
        .where(HourlyStats.business_id == business_id, HourlyStats.bookings > 0)
        .order_by(HourlyStats.weekday, HourlyStats.hour)
    )
    return hours.all()
