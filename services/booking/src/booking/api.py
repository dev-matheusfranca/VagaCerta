from collections.abc import AsyncIterator, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from opentelemetry import metrics
from sqlalchemy import ColumnElement, and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from booking import events, models, schemas
from booking.auth import Claims, require_role
from booking.catalog_client import Business, CatalogClient, Professional, Service
from booking.domain import available_slots

router = APIRouter()
BOOKINGS = metrics.get_meter("booking").create_counter(
    "vagacerta.bookings", unit="{booking}", description="Agendamentos criados e cancelados"
)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_catalog(request: Request) -> CatalogClient:
    return request.app.state.catalog  # type: ignore[no-any-return]


Session = Annotated[AsyncSession, Depends(get_session)]
Catalog = Annotated[CatalogClient, Depends(get_catalog)]
Owner = Annotated[Claims, Depends(require_role("owner"))]
WaitlistService = Depends(require_role("booking-holds"))


async def load_schedule(
    catalog: CatalogClient, business_id: UUID, professional_id: UUID, service_id: UUID
) -> tuple[Business, Professional, Service]:
    business = await catalog.get_business(business_id)
    if business:
        professional = next((p for p in business.professionals if p.id == professional_id), None)
        service = next((s for s in business.services if s.id == service_id), None)
        if professional and service:
            return business, professional, service
    raise HTTPException(404, "Estabelecimento, profissional ou serviço não encontrado")


async def get_booking_or_404(
    session: AsyncSession, booking_id: UUID, **kwargs: Any
) -> models.Booking:
    booking = await session.get(models.Booking, booking_id, **kwargs)
    if booking is None:
        raise HTTPException(404, "Agendamento não encontrado")
    return booking


def occupies_slot(now: datetime) -> ColumnElement[bool]:
    return or_(
        models.Booking.status == "confirmed",
        and_(models.Booking.status == "held", models.Booking.hold_expires_at > now),
    )


@router.get("/availability", response_model=schemas.Availability)
async def get_availability(
    business_id: UUID,
    professional_id: UUID,
    service_id: UUID,
    date: date,
    session: Session,
    catalog: Catalog,
) -> dict[str, list[datetime]]:
    business, professional, service = await load_schedule(
        catalog, business_id, professional_id, service_id
    )
    tz = ZoneInfo(business.timezone)
    day_start = datetime.combine(date, time(), tz)
    now = datetime.now(UTC)
    busy = await session.execute(
        select(models.Booking.starts_at, models.Booking.ends_at).where(
            models.Booking.professional_id == professional_id,
            occupies_slot(now),
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
        now,
    )
    return {"slots": slots}


async def reserve(
    data: schemas.BookingIn, session: AsyncSession, catalog: CatalogClient, **fields: Any
) -> tuple[models.Booking, Business, Professional, Service]:
    business, professional, service = await load_schedule(
        catalog, data.business_id, data.professional_id, data.service_id
    )
    tz = ZoneInfo(business.timezone)
    day = data.starts_at.astimezone(tz).date()
    duration = timedelta(minutes=service.duration_minutes)
    open_slots = available_slots(
        day, tz, professional.periods_on(day), duration, busy=[], now=datetime.now(UTC)
    )
    if data.starts_at not in open_slots:
        raise HTTPException(422, "Horário fora do expediente do profissional ou já passou")

    # Reservas vencidas não podem continuar bloqueando o horário na constraint do banco.
    await session.execute(
        update(models.Booking)
        .where(models.Booking.status == "held", models.Booking.hold_expires_at <= func.now())
        .values(status="released")
    )
    booking = models.Booking(
        id=uuid4(),
        **data.model_dump(exclude={"hold_minutes"}),
        ends_at=data.starts_at + duration,
        **fields,
    )
    return booking, business, professional, service


async def commit_or_conflict(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError:
        raise HTTPException(409, "Esse horário acabou de ser reservado por outra pessoa") from None


@router.post("/bookings", response_model=schemas.Booking, status_code=201)
async def create_booking(
    data: schemas.BookingIn, session: Session, catalog: Catalog
) -> models.Booking:
    booking, business, professional, service = await reserve(data, session, catalog)
    session.add_all([booking, events.booking_created(booking, business, professional, service)])
    await commit_or_conflict(session)
    BOOKINGS.add(1, {"event": "created", "source": "site"})
    return booking


@router.post(
    "/holds", response_model=schemas.Booking, status_code=201, dependencies=[WaitlistService]
)
async def create_hold(data: schemas.HoldIn, session: Session, catalog: Catalog) -> models.Booking:
    booking, *_ = await reserve(
        data,
        session,
        catalog,
        status="held",
        hold_expires_at=datetime.now(UTC) + timedelta(minutes=data.hold_minutes),
    )
    session.add(booking)
    await commit_or_conflict(session)
    return booking


@router.get("/bookings/{booking_id}", response_model=schemas.Booking)
async def get_booking(booking_id: UUID, session: Session) -> models.Booking:
    return await get_booking_or_404(session, booking_id)


@router.post(
    "/bookings/{booking_id}/confirm", response_model=schemas.Booking, dependencies=[WaitlistService]
)
async def confirm_booking(booking_id: UUID, session: Session, catalog: Catalog) -> models.Booking:
    booking = await get_booking_or_404(session, booking_id, with_for_update=True)
    if booking.status == "confirmed":
        return booking
    if booking.status != "held" or booking.hold_expires_at <= datetime.now(UTC):  # type: ignore[operator]
        raise HTTPException(409, "A reserva expirou")
    business, professional, service = await load_schedule(
        catalog, booking.business_id, booking.professional_id, booking.service_id
    )
    booking.status, booking.hold_expires_at = "confirmed", None
    session.add(events.booking_created(booking, business, professional, service))
    await session.commit()
    BOOKINGS.add(1, {"event": "created", "source": "waitlist"})
    return booking


@router.post(
    "/bookings/{booking_id}/release", response_model=schemas.Booking, dependencies=[WaitlistService]
)
async def release_booking(booking_id: UUID, session: Session) -> models.Booking:
    booking = await get_booking_or_404(session, booking_id, with_for_update=True)
    if booking.status not in ("held", "released"):
        raise HTTPException(409, "Só reservas temporárias podem ser liberadas")
    booking.status = "released"
    await session.commit()
    return booking


@router.post("/bookings/{booking_id}/cancel", response_model=schemas.Booking)
async def cancel_booking(booking_id: UUID, session: Session) -> models.Booking:
    booking = await get_booking_or_404(session, booking_id, with_for_update=True)
    if booking.status == "cancelled":
        return booking
    if booking.status != "confirmed":
        raise HTTPException(409, "Só agendamentos confirmados podem ser cancelados")
    if booking.starts_at <= datetime.now(UTC):
        raise HTTPException(409, "Não é possível cancelar um atendimento que já começou")
    booking.status = "cancelled"
    session.add(events.booking_cancelled(booking))
    await session.commit()
    BOOKINGS.add(1, {"event": "cancelled"})
    return booking


@router.get("/businesses/{business_id}/agenda", response_model=list[schemas.Booking])
async def get_agenda(
    business_id: UUID, date: date, session: Session, catalog: Catalog, claims: Owner
) -> Sequence[models.Booking]:
    # Cada dono pertence, no Keycloak, ao grupo com o id do seu estabelecimento.
    if str(business_id) not in claims.get("businesses", []):
        raise HTTPException(403, "Você não tem acesso a este estabelecimento")
    business = await catalog.get_business(business_id)
    if business is None:
        raise HTTPException(404, "Estabelecimento não encontrado")
    day_start = datetime.combine(date, time(), ZoneInfo(business.timezone))
    bookings = await session.scalars(
        select(models.Booking)
        .where(
            models.Booking.business_id == business_id,
            occupies_slot(datetime.now(UTC)),
            models.Booking.starts_at >= day_start,
            models.Booking.starts_at < day_start + timedelta(days=1),
        )
        .order_by(models.Booking.starts_at)
    )
    return bookings.all()
