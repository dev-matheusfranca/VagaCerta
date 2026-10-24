from datetime import datetime
from uuid import UUID

from opentelemetry import metrics
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from waitlist.booking_client import BookingClient
from waitlist.events import BookingCancelled, offer_created
from waitlist.models import Entry, Offer, ProcessedEvent

OFFERS = metrics.get_meter("waitlist").create_counter(
    "vagacerta.waitlist.offers",
    unit="{offer}",
    description="Ofertas da lista de espera por resultado",
)


async def offer_slot(
    session: AsyncSession,
    booking: BookingClient,
    professional_id: UUID,
    starts_at: datetime,
    minutes: int,
) -> Offer | None:
    """Reserva o horário liberado para a primeira pessoa da fila que ainda não o recebeu."""
    already_offered = exists().where(Offer.entry_id == Entry.id, Offer.starts_at == starts_at)
    queue = await session.scalars(
        select(Entry)
        .where(
            Entry.professional_id == professional_id,
            Entry.status == "waiting",
            Entry.window_start <= starts_at,
            Entry.window_end > starts_at,
            ~already_offered,
        )
        .order_by(Entry.created_at)
        .with_for_update(skip_locked=True)
    )
    for entry in queue:
        # O serviço de quem está na fila pode não caber no horário: aí passa para o próximo.
        if hold := await booking.hold(entry, starts_at, minutes):
            offer = Offer(
                entry=entry,
                booking_id=hold.id,
                starts_at=hold.starts_at,
                ends_at=hold.ends_at,
                expires_at=hold.hold_expires_at,
            )
            entry.status = "offered"
            session.add(offer)
            await session.flush()
            session.add(offer_created(offer))
            OFFERS.add(1, {"outcome": "offered"})
            return offer
    return None


async def handle_cancellation(
    event: BookingCancelled, session: AsyncSession, booking: BookingClient, minutes: int
) -> None:
    if await session.get(ProcessedEvent, event.event_id):
        return
    session.add(ProcessedEvent(id=event.event_id))
    await offer_slot(session, booking, event.data.professional_id, event.data.starts_at, minutes)
    await session.commit()


async def claim(
    session: AsyncSession, booking: BookingClient, offer_id: UUID, now: datetime
) -> Offer | None:
    offer = await session.get(Offer, offer_id, with_for_update=True)
    if offer and offer.status == "pending" and offer.expires_at > now:
        if await booking.confirm(offer.booking_id):
            offer.status, offer.entry.status = "claimed", "booked"
            OFFERS.add(1, {"outcome": "claimed"})
            await session.commit()
    return offer


async def expire_offers(
    session: AsyncSession, booking: BookingClient, now: datetime, minutes: int
) -> None:
    """Compensação da saga: libera a reserva vencida e oferece o horário ao próximo da fila."""
    offers = await session.scalars(
        select(Offer)
        .where(Offer.status == "pending", Offer.expires_at <= now)
        .with_for_update(skip_locked=True)
    )
    for offer in offers:
        if await booking.release(offer.booking_id):
            offer.status, offer.entry.status = "expired", "waiting"
            OFFERS.add(1, {"outcome": "expired"})
            await offer_slot(
                session, booking, offer.entry.professional_id, offer.starts_at, minutes
            )
        else:
            offer.status, offer.entry.status = "claimed", "booked"
            OFFERS.add(1, {"outcome": "claimed"})
    await session.commit()
