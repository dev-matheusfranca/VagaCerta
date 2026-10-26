import asyncio
import json
import logging
import os
from datetime import UTC, datetime

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from opentelemetry import context, propagate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from booking.main import DATABASE_URL
from booking.models import OutboxEvent

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
logger = logging.getLogger(__name__)
Sessionmaker = async_sessionmaker[AsyncSession]


async def publish_pending(session: AsyncSession, producer: AIOKafkaProducer) -> int:
    # SKIP LOCKED permite rodar várias réplicas do relay sem publicarem o mesmo evento em paralelo.
    events = await session.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.id)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    published = 0
    for event in events:
        token = context.attach(propagate.extract(event.trace_context))
        try:
            await producer.send_and_wait(
                event.topic, json.dumps(event.payload).encode(), key=event.key.encode()
            )
        finally:
            context.detach(token)
        event.published_at = datetime.now(UTC)
        published += 1
    await session.commit()
    return published


async def relay(sessionmaker: Sessionmaker, producer: AIOKafkaProducer) -> None:
    while True:
        async with sessionmaker() as session:
            try:
                published = await publish_pending(session, producer)
            except KafkaError:
                # Sem o Kafka, os eventos continuam no outbox e saem, em ordem, quando ele voltar.
                logger.warning("Kafka indisponível, tentando de novo", exc_info=True)
                published = 0
        if not published:
            await asyncio.sleep(0.5)


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL))
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, enable_idempotence=True)
    await producer.start()
    try:
        await relay(sessionmaker, producer)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
