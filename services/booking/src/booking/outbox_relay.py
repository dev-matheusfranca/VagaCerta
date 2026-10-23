import asyncio
import json
import os
from datetime import UTC, datetime

from aiokafka import AIOKafkaProducer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from booking.main import DATABASE_URL
from booking.models import OutboxEvent

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")


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
        await producer.send_and_wait(
            event.topic, json.dumps(event.payload).encode(), key=event.key.encode()
        )
        event.published_at = datetime.now(UTC)
        published += 1
    await session.commit()
    return published


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL))
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, enable_idempotence=True)
    await producer.start()
    try:
        while True:
            async with sessionmaker() as session:
                if not await publish_pending(session, producer):
                    await asyncio.sleep(0.5)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
