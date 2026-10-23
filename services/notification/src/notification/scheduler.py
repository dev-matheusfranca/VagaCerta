import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notification import emails
from notification.consumer import Publish
from notification.events import BookingDetails
from notification.models import Booking


async def send_due_reminders(session: AsyncSession, publish: Publish, now: datetime) -> int:
    bookings = await session.scalars(
        select(Booking)
        .where(
            Booking.remind_at <= now,
            Booking.reminded_at.is_(None),
            Booking.cancelled_at.is_(None),
        )
        .with_for_update(skip_locked=True)
    )
    sent = 0
    for booking in bookings:
        await publish(emails.reminder(BookingDetails.model_validate(booking.details)))
        booking.reminded_at = now
        sent += 1
    await session.commit()
    return sent


async def run_scheduler(sessionmaker: async_sessionmaker[AsyncSession], publish: Publish) -> None:
    while True:
        async with sessionmaker() as session:
            await send_due_reminders(session, publish, datetime.now(UTC))
        await asyncio.sleep(30)
