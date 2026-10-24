import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.message import EmailMessage

from aiokafka import AIOKafkaConsumer
from opentelemetry import propagate, trace
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from notification import emails
from notification.domain import remind_at
from notification.events import BookingCreated, BookingDetails, Event, OfferCreated, event_adapter
from notification.models import Booking, ProcessedEvent

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("notification")

Publish = Callable[[EmailMessage], Awaitable[None]]


async def handle_event(
    event: Event, session: AsyncSession, publish: Publish, now: datetime
) -> None:
    # O Kafka entrega pelo menos uma vez: o id do evento garante que cada um é tratado uma vez só.
    if await session.get(ProcessedEvent, event.event_id):
        return
    session.add(ProcessedEvent(id=event.event_id))
    if isinstance(event, BookingCreated):
        session.add(
            Booking(
                id=event.data.booking_id,
                details=event.data.model_dump(mode="json"),
                remind_at=remind_at(event.data.starts_at, now),
            )
        )
        await publish(emails.confirmation(event.data))
    elif isinstance(event, OfferCreated):
        await publish(emails.offer(event.data))
    elif booking := await session.get(Booking, event.data.booking_id):
        booking.cancelled_at = now
        await publish(emails.cancellation(BookingDetails.model_validate(booking.details)))
    await session.commit()


async def consume(
    consumer: AIOKafkaConsumer, sessionmaker: async_sessionmaker[AsyncSession], publish: Publish
) -> None:
    async for record in consumer:
        try:
            event = event_adapter.validate_json(record.value)
        except ValidationError:
            logger.debug("Skipping event this service does not handle at offset %s", record.offset)
        else:
            carrier = {key: value.decode() for key, value in record.headers}
            with tracer.start_as_current_span(
                f"process {event.type}",
                context=propagate.extract(carrier),
                kind=trace.SpanKind.CONSUMER,
            ):
                async with sessionmaker() as session:
                    await handle_event(event, session, publish, datetime.now(UTC))
        await consumer.commit()
