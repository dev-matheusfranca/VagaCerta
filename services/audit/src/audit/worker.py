import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer
from opentelemetry import propagate, trace
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from audit.config import DATABASE_URL, KAFKA_BOOTSTRAP_SERVERS, TOPICS
from audit.recorder import record

tracer = trace.get_tracer("audit")
logger = logging.getLogger(__name__)
EVENT_FIELDS = {"event_id", "type", "occurred_at"}


async def audit(consumer: AIOKafkaConsumer, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    async for message in consumer:
        try:
            payload = json.loads(message.value)
        except ValueError:
            payload = None
        if not isinstance(payload, dict) or not EVENT_FIELDS <= payload.keys():
            logger.warning("Mensagem fora do formato de evento em %s", message.topic)
        else:
            carrier = {key: value.decode() for key, value in message.headers}
            with tracer.start_as_current_span(
                f"audit {payload['type']}",
                context=propagate.extract(carrier),
                kind=trace.SpanKind.CONSUMER,
            ):
                async with sessionmaker() as session:
                    await record(session, message.topic, payload)
        await consumer.commit()


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL), expire_on_commit=False)
    # Lê tudo desde o início: a trilha cobre a história inteira que ainda está no Kafka.
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="audit",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        await audit(consumer, sessionmaker)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
