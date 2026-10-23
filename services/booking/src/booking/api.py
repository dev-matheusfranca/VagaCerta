from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from booking import models, schemas
from booking.catalog_client import CatalogClient, Professional, Service
from booking.domain import available_slots

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_catalog(request: Request) -> CatalogClient:
    return request.app.state.catalog  # type: ignore[no-any-return]


Session = Annotated[AsyncSession, Depends(get_session)]
Catalog = Annotated[CatalogClient, Depends(get_catalog)]


async def load_schedule(
    catalog: CatalogClient, business_id: UUID, professional_id: UUID, service_id: UUID
) -> tuple[ZoneInfo, Professional, Service]:
    business = await catalog.get_business(business_id)
    if business:
        professional = next((p for p in business.professionals if p.id == professional_id), None)
        service = next((s for s in business.services if s.id == service_id), None)
        if professional and service:
            return ZoneInfo(business.timezone), professional, service
    raise HTTPException(404, "Estabelecimento, profissional ou serviço não encontrado")


async def get_booking_or_404(session: AsyncSession, booking_id: UUID) -> models.Booking:
    booking = await session.get(models.Booking, booking_id)
    if booking is None:
        raise HTTPException(404, "Agendamento não encontrado")
    return booking


@router.get("/availability", response_model=schemas.Availability)
async def get_availability(
    business_id: UUID,
    professional_id: UUID,
    service_id: UUID,
    date: date,
    session: Session,
    catalog: Catalog,
) -> dict[str, list[datetime]]:
    tz, professional, service = await load_schedule(
        catalog, business_id, professional_id, service_id
    )
    day_start = datetime.combine(date, time(), tz)
    busy = await session.execute(
        select(models.Booking.starts_at, models.Booking.ends_at).where(
            models.Booking.professional_id == professional_id,
            models.Booking.status == "confirmed",
            models.Booking.starts_at < day_start + timedelta(days=1),
            models.Booking.ends_at > day_start,
        )
    )
    slots = available_slots(
        date,
        tz,
        professional.periods_on(date),
        timedelta(minutes=service.duration_minutes),
        list(busy.all()),
        datetime.now(UTC),
    )
    return {"slots": slots}


@router.post("/bookings", response_model=schemas.Booking, status_code=201)
async def create_booking(
    data: schemas.BookingIn, session: Session, catalog: Catalog
) -> models.Booking:
    tz, professional, service = await load_schedule(
        catalog, data.business_id, data.professional_id, data.service_id
    )
    day = data.starts_at.astimezone(tz).date()
    duration = timedelta(minutes=service.duration_minutes)
    open_slots = available_slots(
        day, tz, professional.periods_on(day), duration, busy=[], now=datetime.now(UTC)
    )
    if data.starts_at not in open_slots:
        raise HTTPException(422, "Horário fora do expediente do profissional ou já passou")

    booking = models.Booking(**data.model_dump(), ends_at=data.starts_at + duration)
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError:
        raise HTTPException(409, "Esse horário acabou de ser reservado por outra pessoa") from None
    return booking


@router.get("/bookings/{booking_id}", response_model=schemas.Booking)
async def get_booking(booking_id: UUID, session: Session) -> models.Booking:
    return await get_booking_or_404(session, booking_id)


@router.post("/bookings/{booking_id}/cancel", response_model=schemas.Booking)
async def cancel_booking(booking_id: UUID, session: Session) -> models.Booking:
    booking = await get_booking_or_404(session, booking_id)
    if booking.starts_at <= datetime.now(UTC):
        raise HTTPException(409, "Não é possível cancelar um atendimento que já começou")
    booking.status = "cancelled"
    await session.commit()
    return booking
