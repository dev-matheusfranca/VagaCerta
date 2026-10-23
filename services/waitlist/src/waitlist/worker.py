import asyncio
import json
import logging
from datetime import UTC, datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from waitlist import saga
from waitlist.booking_client import BookingClient
from waitlist.config import BOOKING_URL, DATABASE_URL, KAFKA_BOOTSTRAP_SERVERS, OFFER_MINUTES
from waitlist.events import BOOKING_TOPIC, BookingCancelled
from waitlist.models import OutboxEvent

Sessionmaker = async_sessionmaker[AsyncSession]


async def consume_cancellations(
    consumer: AIOKafkaConsumer, sessionmaker: Sessionmaker, booking: BookingClient
) -> None:
    async for record in consumer:
        try:
            event = BookingCancelled.model_validate_json(record.value)
        except ValidationError:
            pass  # outros tipos de evento, ou cancelamentos antigos que ainda não traziam o horário
        else:
            async with sessionmaker() as session:
                await saga.handle_cancellation(event, session, booking, OFFER_MINUTES)
        await consumer.commit()


async def expire_offers(sessionmaker: Sessionmaker, booking: BookingClient) -> None:
    while True:
        async with sessionmaker() as session:
            await saga.expire_offers(session, booking, datetime.now(UTC), OFFER_MINUTES)
        await asyncio.sleep(5)


async def publish_pending(session: AsyncSession, producer: AIOKafkaProducer) -> int:
    events = await session.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.id)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    published = 0
    for event in events:
        await producer.send_and_wait(
            event.topic, json.dumps(event.payload).encode(), key=event.key.encode()
        )
        event.published_at = datetime.now(UTC)
        published += 1
    await session.commit()
    return published


async def relay_outbox(sessionmaker: Sessionmaker, producer: AIOKafkaProducer) -> None:
    while True:
        async with sessionmaker() as session:
            if not await publish_pending(session, producer):
                await asyncio.sleep(0.5)


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL), expire_on_commit=False)
    booking = BookingClient(BOOKING_URL)
    consumer = AIOKafkaConsumer(
        BOOKING_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="waitlist",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, enable_idempotence=True)
    await consumer.start()
    await producer.start()
    try:
        await asyncio.gather(
            consume_cancellations(consumer, sessionmaker, booking),
            expire_offers(sessionmaker, booking),
            relay_outbox(sessionmaker, producer),
        )
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
