import asyncio
import json

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.kafka import KafkaContainer

from booking.models import OutboxEvent
from booking.outbox_relay import publish_pending, relay


@pytest.fixture(scope="module")
def kafka_container():
    with KafkaContainer().with_kraft() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def kafka(kafka_container):
    return kafka_container.get_bootstrap_server()


async def add_events(sessionmaker, *seqs: int) -> None:
    async with sessionmaker() as session:
        await session.execute(text("TRUNCATE outbox"))
        session.add_all(
            OutboxEvent(topic="booking.events", key="booking-1", payload={"seq": seq})
            for seq in seqs
        )
        await session.commit()


async def pending(sessionmaker) -> int:
    async with sessionmaker() as session:
        events = await session.scalars(
            select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
        )
        return len(events.all())


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


async def test_events_wait_in_the_outbox_while_kafka_is_down(database_url, kafka_container, kafka):
    sessionmaker = async_sessionmaker(create_async_engine(database_url))
    await add_events(sessionmaker, 10, 11)
    producer = AIOKafkaProducer(bootstrap_servers=kafka, request_timeout_ms=1000)
    await producer.start()
    kafka_container.get_wrapped_container().pause()
    running = asyncio.create_task(relay(sessionmaker, producer))
    try:
        await asyncio.sleep(4)
        assert not running.done()
        assert await pending(sessionmaker) == 2

        kafka_container.get_wrapped_container().unpause()
        for _ in range(60):
            if await pending(sessionmaker) == 0:
                break
            await asyncio.sleep(0.5)
        assert await pending(sessionmaker) == 0
    finally:
        running.cancel()
        await producer.stop()

    consumer = AIOKafkaConsumer(
        "booking.events", bootstrap_servers=kafka, auto_offset_reset="earliest"
    )
    await consumer.start()
    seqs: list[int] = []
    try:
        while 11 not in seqs:
            record = await asyncio.wait_for(consumer.getone(), 10)
            seqs.append(json.loads(record.value)["seq"])
    finally:
        await consumer.stop()

    # Um envio interrompido pode repetir um evento: os consumidores, idempotentes, descartam.
    assert [seq for seq in dict.fromkeys(seqs) if seq >= 10] == [10, 11]
