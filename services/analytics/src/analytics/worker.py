import asyncio
import logging

from aiokafka import AIOKafkaConsumer
from opentelemetry import propagate, trace
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from analytics.config import DATABASE_URL, KAFKA_BOOTSTRAP_SERVERS
from analytics.events import TOPICS, event_adapter
from analytics.projections import apply

tracer = trace.get_tracer("analytics")


async def project(
    consumer: AIOKafkaConsumer, sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    async for record in consumer:
        try:
            event = event_adapter.validate_json(record.value)
        except ValidationError:
            pass  # eventos que não alimentam as projeções, ou versões antigas sem os campos usados
        else:
            carrier = {key: value.decode() for key, value in record.headers}
            with tracer.start_as_current_span(
                f"project {event.type}",
                context=propagate.extract(carrier),
                kind=trace.SpanKind.CONSUMER,
            ):
                async with sessionmaker() as session:
                    await apply(event, session)
        await consumer.commit()


async def main() -> None:
    sessionmaker = async_sessionmaker(create_async_engine(DATABASE_URL), expire_on_commit=False)
    # Grupo próprio, lendo desde o início: a projeção pode ser reconstruída do histórico do Kafka.
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="analytics",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        await project(consumer, sessionmaker)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
