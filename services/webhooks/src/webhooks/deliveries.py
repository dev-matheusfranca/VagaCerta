import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage
from opentelemetry import propagate, trace
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from webhooks.models import Delivery, Subscription
from webhooks.targets import ForbiddenTarget, check_target

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("webhooks")

QUEUE = "webhooks.delivery"
DEAD_LETTER_QUEUE = "webhooks.delivery.dead"
RETRY_DELAYS = (5.0, 30.0, 120.0)


def signature(secret: str, body: bytes) -> str:
    """HMAC-SHA256 do corpo; o destino recalcula com o segredo para validar a origem."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def retry_queue(failures: int) -> str:
    return f"{QUEUE}.retry.{failures}"


async def declare_queues(channel: AbstractChannel, retry_delays: tuple[float, ...]) -> None:
    await channel.declare_queue(QUEUE, durable=True)
    await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
    # Mesmo esquema de retry do mailer do Notification.
    for failures, delay in enumerate(retry_delays, start=1):
        await channel.declare_queue(
            retry_queue(failures),
            durable=True,
            arguments={
                "x-message-ttl": int(delay * 1000),
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": QUEUE,
            },
        )


async def publish(
    channel: AbstractChannel, delivery_id: UUID, queue: str = QUEUE, failures: int = 0
) -> None:
    await channel.default_exchange.publish(
        Message(
            str(delivery_id).encode(),
            headers={"x-failed-attempts": failures},
            delivery_mode=DeliveryMode.PERSISTENT,
        ),
        routing_key=queue,
    )


async def fan_out(session: AsyncSession, event: dict[str, Any]) -> list[UUID]:
    """Cria uma entrega por assinatura interessada e devolve as pendentes.

    Eventos anteriores ao cadastro ficam de fora; senão, reprocessar o Kafka mandaria o histórico
    inteiro para uma integração nova.
    """
    business_id = event.get("data", {}).get("business_id")
    if not business_id:
        return []
    subscriptions = await session.scalars(
        select(Subscription.id).where(
            Subscription.business_id == business_id,
            Subscription.events.contains([event["type"]]),
            Subscription.created_at <= datetime.fromisoformat(event["occurred_at"]),
        )
    )
    for subscription_id in subscriptions.all():
        await session.execute(
            insert(Delivery)
            .values(
                subscription_id=subscription_id,
                event_id=event["event_id"],
                event_type=event["type"],
                payload=event,
            )
            .on_conflict_do_nothing()
        )
    await session.commit()
    pending = await session.scalars(
        select(Delivery.id).where(
            Delivery.event_id == event["event_id"], Delivery.status == "pending"
        )
    )
    return list(pending.all())


async def attempt(
    session: AsyncSession,
    delivery_id: UUID,
    http: httpx.AsyncClient,
    allow_private: bool,
    last: bool,
) -> str | None:
    """Tenta entregar uma vez e devolve o status resultante; None se não havia o que entregar."""
    delivery = await session.get(Delivery, delivery_id)
    if delivery is None or delivery.status != "pending":
        return None
    subscription = await session.get_one(Subscription, delivery.subscription_id)
    body = json.dumps(delivery.payload).encode()
    delivery.attempts += 1
    try:
        await check_target(subscription.url, allow_private)
        response = await http.post(
            subscription.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-VagaCerta-Event": delivery.event_type,
                "X-VagaCerta-Delivery": str(delivery.id),
                "X-VagaCerta-Signature": signature(subscription.secret, body),
            },
        )
        delivery.last_status_code, delivery.last_error = response.status_code, None
        delivered = response.is_success
    except (ForbiddenTarget, httpx.HTTPError) as error:
        delivery.last_status_code, delivery.last_error = (
            None,
            str(error)[:300] or type(error).__name__,
        )
        delivered = False
    if delivered:
        delivery.status = "delivered"
    elif last:
        delivery.status = "failed"
    await session.commit()
    return delivery.status


async def handle(
    message: AbstractIncomingMessage,
    channel: AbstractChannel,
    sessionmaker: async_sessionmaker[AsyncSession],
    http: httpx.AsyncClient,
    allow_private: bool,
    retry_delays: tuple[float, ...],
) -> None:
    failures = int(message.headers.get("x-failed-attempts", 0))  # type: ignore[arg-type]
    last = failures >= len(retry_delays)
    delivery_id = UUID(message.body.decode())
    with tracer.start_as_current_span(
        "deliver webhook", context=propagate.extract(message.headers), kind=trace.SpanKind.CONSUMER
    ):
        async with sessionmaker() as session:
            status = await attempt(session, delivery_id, http, allow_private, last)
    if status == "pending":
        await publish(channel, delivery_id, retry_queue(failures + 1), failures + 1)
    elif status == "failed":
        await publish(channel, delivery_id, DEAD_LETTER_QUEUE, failures)
    await message.ack()
