from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from notification.consumer import handle_event
from notification.events import BookingCancelled, BookingCreated, BookingRef
from notification.models import Booking
from notification.scheduler import send_due_reminders


class Mailbox(list):
    async def __call__(self, message):
        self.append(message["Subject"].split(":")[0])


@pytest.fixture(scope="module")
def sessionmaker():
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield async_sessionmaker(create_async_engine(url), expire_on_commit=False)


@pytest.fixture
async def session(sessionmaker):
    async with sessionmaker() as session:
        yield session
    async with sessionmaker() as cleanup:
        await cleanup.execute(text("TRUNCATE bookings, processed_events"))
        await cleanup.commit()


def created(details):
    return BookingCreated(event_id=uuid4(), type="booking.created", data=details)


def cancelled(details):
    return BookingCancelled(
        event_id=uuid4(), type="booking.cancelled", data=BookingRef(booking_id=details.booking_id)
    )


async def test_new_booking_sends_confirmation_and_schedules_reminder(session, details):
    mailbox = Mailbox()

    await handle_event(created(details), session, mailbox, details.starts_at - timedelta(days=3))

    booking = await session.get(Booking, details.booking_id)
    assert mailbox == ["Agendamento confirmado"]
    assert booking.remind_at == details.starts_at - timedelta(hours=24)


async def test_redelivered_event_is_handled_once(session, details):
    mailbox, event = Mailbox(), created(details)
    now = details.starts_at - timedelta(days=3)

    await handle_event(event, session, mailbox, now)
    await handle_event(event, session, mailbox, now)

    assert mailbox == ["Agendamento confirmado"]


async def test_due_reminder_is_sent_exactly_once(session, details):
    mailbox = Mailbox()
    await handle_event(created(details), session, mailbox, details.starts_at - timedelta(days=3))
    due = details.starts_at - timedelta(hours=23)

    first = await send_due_reminders(session, mailbox, due)
    second = await send_due_reminders(session, mailbox, due)

    assert (first, second) == (1, 0)
    assert mailbox == ["Agendamento confirmado", "Lembrete"]


async def test_cancelled_booking_is_notified_and_not_reminded(session, details):
    mailbox = Mailbox()
    now = details.starts_at - timedelta(days=3)
    await handle_event(created(details), session, mailbox, now)

    await handle_event(cancelled(details), session, mailbox, now)

    assert await send_due_reminders(session, mailbox, details.starts_at) == 0
    assert mailbox == ["Agendamento confirmado", "Agendamento cancelado"]
