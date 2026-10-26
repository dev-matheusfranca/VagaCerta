import asyncio
import json
import logging
from functools import partial

import aio_pika
import httpx
from aio_pika.abc import AbstractChannel
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from webhooks import deliveries
from webhooks.config import (
    ALLOW_PRIVATE_TARGETS,
    DATABASE_URL,
    KAFKA_BOOTSTRAP_SERVERS,
    RABBITMQ_URL,
    TOPICS,
)

Sessionmaker = async_sessionmaker[AsyncSession]


async def dispatch(
    consumer: AIOKafkaConsumer, sessionmaker: Sessionmaker, channel: AbstractChannel
) -> None:
    async for record in consumer:
        try:
            event = json.loads(record.value)
        except ValueError:
            event = None
        if isinstance(event, dict) and {"event_id", "type", "occurred_at"} <= event.keys():
            async with sessionmaker() as session:
                for delivery_id in await deliveries.fan_out(session, event):
                    await deliveries.publish(channel, delivery_id)
        await consumer.commit()


async def send(channel: AbstractChannel, sessionmaker: Sessionmaker) -> None:
    # Sem seguir redirecionamentos: um 302 poderia levar a entrega para a rede interna.
    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as http:
        queue = await channel.get_queue(deliveries.QUEUE)
        handle = partial(
            deliveries.handle,
            channel=channel,
            sessionmaker=sessionmaker,
            http=http,
            allow_private=ALLOW_PRIVATE_TARGETS,
            retry_delays=deliveries.RETRY_DELAYS,
        )
        async with queue.iterator() as messages:
            async for message in messages:
                await handle(message)


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL), expire_on_commit=False)
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    await deliveries.declare_queues(channel, deliveries.RETRY_DELAYS)
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="webhooks",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        await asyncio.gather(dispatch(consumer, sessionmaker, channel), send(channel, sessionmaker))
    finally:
        await consumer.stop()
        await connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
