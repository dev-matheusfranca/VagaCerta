import asyncio
import logging
from functools import partial

import aio_pika
import aiosmtplib
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from notification import mailer
from notification.config import (
    DATABASE_URL,
    KAFKA_BOOTSTRAP_SERVERS,
    RABBITMQ_URL,
    SMTP_HOST,
    SMTP_PORT,
)
from notification.consumer import consume
from notification.events import TOPICS
from notification.scheduler import run_scheduler


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL), expire_on_commit=False)
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    await mailer.declare_queues(channel, mailer.RETRY_DELAYS)
    publish = partial(mailer.publish, channel)

    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="notification",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        await asyncio.gather(
            consume(consumer, sessionmaker, publish),
            run_scheduler(sessionmaker, publish),
            mailer.run_worker(
                channel,
                partial(aiosmtplib.send, hostname=SMTP_HOST, port=SMTP_PORT),
                mailer.RETRY_DELAYS,
            ),
        )
    finally:
        await consumer.stop()
        await connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
