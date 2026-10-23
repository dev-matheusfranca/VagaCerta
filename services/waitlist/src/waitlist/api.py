from collections.abc import AsyncIterator
from datetime import UTC, datetime, time, timedelta
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from waitlist import models, saga, schemas
from waitlist.booking_client import BookingClient
from waitlist.catalog_client import Business, CatalogClient, Professional, Service

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_catalog(request: Request) -> CatalogClient:
    return request.app.state.catalog  # type: ignore[no-any-return]


def get_booking(request: Request) -> BookingClient:
    return request.app.state.booking  # type: ignore[no-any-return]


Session = Annotated[AsyncSession, Depends(get_session)]
Catalog = Annotated[CatalogClient, Depends(get_catalog)]
Booking = Annotated[BookingClient, Depends(get_booking)]


async def load_choice(
    catalog: CatalogClient, data: schemas.EntryIn
) -> tuple[Business, Professional, Service]:
    business = await catalog.get_business(data.business_id)
    if business:
        professional = next(
            (p for p in business.professionals if p.id == data.professional_id), None
        )
        service = next((s for s in business.services if s.id == data.service_id), None)
        if professional and service:
            return business, professional, service
    raise HTTPException(404, "Estabelecimento, profissional ou serviço não encontrado")


@router.post("/entries", response_model=schemas.Entry, status_code=201)
async def join_waitlist(
    data: schemas.EntryIn, session: Session, catalog: Catalog
) -> dict[str, object]:
    business, professional, service = await load_choice(catalog, data)
    tz = ZoneInfo(business.timezone)
    if data.day < datetime.now(tz).date():
        raise HTTPException(422, "Escolha um dia a partir de hoje")

    window_start = datetime.combine(data.day, time(), tz)
    entry = models.Entry(
        **data.model_dump(),
        window_start=window_start,
        window_end=window_start + timedelta(days=1),
        details={
            "business_name": business.name,
            "business_address": business.address,
            "timezone": business.timezone,
            "professional_name": professional.name,
            "service_name": service.name,
            "price_cents": service.price_cents,
        },
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError:
        raise HTTPException(409, "Você já está na lista de espera deste dia") from None

    position = await session.scalar(
        select(func.count()).where(
            models.Entry.professional_id == entry.professional_id,
            models.Entry.day == entry.day,
            models.Entry.status == "waiting",
            models.Entry.created_at <= entry.created_at,
        )
    )
    return {"id": entry.id, "position": position}


@router.get("/offers/{offer_id}", response_model=schemas.Offer)
async def get_offer(offer_id: UUID, session: Session) -> models.Offer:
    offer = await session.get(models.Offer, offer_id)
    if offer is None:
        raise HTTPException(404, "Oferta não encontrada")
    return offer


@router.post("/offers/{offer_id}/claim", response_model=schemas.Offer)
async def claim_offer(offer_id: UUID, session: Session, booking: Booking) -> models.Offer:
    offer = await saga.claim(session, booking, offer_id, datetime.now(UTC))
    if offer is None:
        raise HTTPException(404, "Oferta não encontrada")
    if offer.status != "claimed":
        raise HTTPException(
            409, "Essa oferta expirou e o horário foi para a próxima pessoa da fila"
        )
    return offer
