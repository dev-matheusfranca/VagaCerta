import json

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.kafka import KafkaContainer

from booking.models import OutboxEvent
from booking.outbox_relay import publish_pending


@pytest.fixture(scope="module")
def kafka():
    with KafkaContainer().with_kraft() as kafka:
        yield kafka.get_bootstrap_server()


async def test_publishes_pending_events_once_and_in_order(database_url, kafka):
    sessionmaker = async_sessionmaker(create_async_engine(database_url))
    async with sessionmaker() as session:
        await session.execute(text("TRUNCATE outbox"))
        session.add_all(
            OutboxEvent(topic="booking.events", key="booking-1", payload={"seq": seq})
            for seq in range(3)
        )
        await session.commit()

    producer = AIOKafkaProducer(bootstrap_servers=kafka)
    await producer.start()
    try:
        async with sessionmaker() as session:
            first_run = await publish_pending(session, producer)
        async with sessionmaker() as session:
            second_run = await publish_pending(session, producer)
            pending = await session.scalars(
                select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
            )
            assert pending.all() == []
    finally:
        await producer.stop()

    consumer = AIOKafkaConsumer(
        "booking.events", bootstrap_servers=kafka, auto_offset_reset="earliest"
    )
    await consumer.start()
    try:
        records = [await consumer.getone() for _ in range(3)]
    finally:
        await consumer.stop()

    assert (first_run, second_run) == (3, 0)
    assert [json.loads(r.value)["seq"] for r in records] == [0, 1, 2]
    assert {r.key for r in records} == {b"booking-1"}
