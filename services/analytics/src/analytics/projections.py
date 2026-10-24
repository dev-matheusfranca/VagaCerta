from datetime import date
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.events import BookingCancelled, BookingCreated, Event
from analytics.models import Booking, DailyStats, ProcessedEvent

OFFER_COUNTERS = {
    "waitlist.offer_created": "offers",
    "waitlist.offer_claimed": "offers_claimed",
    "waitlist.offer_expired": "offers_expired",
}


async def bump(session: AsyncSession, business_id: UUID, day: date, **increments: int) -> None:
    """Soma os incrementos na linha do dia, criando-a se for o primeiro evento daquele dia."""
    statement = insert(DailyStats).values(business_id=business_id, day=day, **increments)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[DailyStats.business_id, DailyStats.day],
            set_={name: getattr(DailyStats, name) + value for name, value in increments.items()},
        )
    )


async def apply(event: Event, session: AsyncSession) -> None:
    if await session.get(ProcessedEvent, event.event_id):
        return
    session.add(ProcessedEvent(id=event.event_id))
    if isinstance(event, BookingCreated):
        slot = event.data
        session.add(
            Booking(
                id=slot.booking_id,
                business_id=slot.business_id,
                day=slot.day,
                price_cents=slot.price_cents,
            )
        )
        await bump(session, slot.business_id, slot.day, bookings=1, revenue_cents=slot.price_cents)
    elif isinstance(event, BookingCancelled):
        if booking := await session.get(Booking, event.data.booking_id):
            await bump(
                session,
                booking.business_id,
                booking.day,
                cancellations=1,
                revenue_cents=-booking.price_cents,
            )
    else:
        offered = event.data
        increments = {OFFER_COUNTERS[event.type]: 1}
        if event.type == "waitlist.offer_claimed":
            increments["recovered_revenue_cents"] = offered.price_cents
        await bump(session, offered.business_id, offered.day, **increments)
    await session.commit()
