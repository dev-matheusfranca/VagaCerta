from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.events import BookingCancelled, BookingCreated, BookingOutcome, Event
from analytics.models import Base, Booking, DailyStats, HourlyStats, ProcessedEvent

OFFER_COUNTERS = {
    "waitlist.offer_created": "offers",
    "waitlist.offer_claimed": "offers_claimed",
    "waitlist.offer_expired": "offers_expired",
}
OUTCOME_COUNTERS = {"booking.completed": "completed", "booking.no_show": "no_shows"}


async def bump(
    session: AsyncSession, table: type[Base], keys: dict[str, Any], **increments: int
) -> None:
    """Soma os incrementos na linha das chaves dadas, criando-a no primeiro evento."""
    statement = insert(table).values(**keys, **increments)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=list(keys),
            set_={name: getattr(table, name) + value for name, value in increments.items()},
        )
    )


async def apply(event: Event, session: AsyncSession) -> None:
    if await session.get(ProcessedEvent, event.event_id):
        return
    session.add(ProcessedEvent(id=event.event_id))
    if isinstance(event, BookingCreated):
        slot, local = event.data, event.data.local_start
        session.add(
            Booking(
                id=slot.booking_id,
                business_id=slot.business_id,
                day=slot.day,
                price_cents=slot.price_cents,
                minutes=slot.minutes,
                weekday=local.weekday(),
                hour=local.hour,
            )
        )
        day = {"business_id": slot.business_id, "day": slot.day}
        await bump(
            session,
            DailyStats,
            day,
            bookings=1,
            revenue_cents=slot.price_cents,
            booked_minutes=slot.minutes,
        )
        hour = {"business_id": slot.business_id, "weekday": local.weekday(), "hour": local.hour}
        await bump(session, HourlyStats, hour, bookings=1)
    elif isinstance(event, BookingCancelled):
        if booking := await session.get(Booking, event.data.booking_id):
            day = {"business_id": booking.business_id, "day": booking.day}
            await bump(
                session,
                DailyStats,
                day,
                cancellations=1,
                revenue_cents=-booking.price_cents,
                booked_minutes=-booking.minutes,
            )
            hour = {
                "business_id": booking.business_id,
                "weekday": booking.weekday,
                "hour": booking.hour,
            }
            await bump(session, HourlyStats, hour, bookings=-1)
    elif isinstance(event, BookingOutcome):
        if booking := await session.get(Booking, event.data.booking_id):
            day = {"business_id": booking.business_id, "day": booking.day}
            await bump(session, DailyStats, day, **{OUTCOME_COUNTERS[event.type]: 1})
    else:
        offered = event.data
        increments = {OFFER_COUNTERS[event.type]: 1}
        if event.type == "waitlist.offer_claimed":
            increments["recovered_revenue_cents"] = offered.price_cents
        day = {"business_id": offered.business_id, "day": offered.day}
        await bump(session, DailyStats, day, **increments)
    await session.commit()
