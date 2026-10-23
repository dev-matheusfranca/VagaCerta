import email
import logging
from collections.abc import Awaitable, Callable
from email import policy
from email.message import EmailMessage

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage
from aiosmtplib import SMTPException

logger = logging.getLogger(__name__)

EMAIL_QUEUE = "notification.email"
DEAD_LETTER_QUEUE = "notification.email.dead"
RETRY_DELAYS = (5.0, 30.0, 120.0)

Send = Callable[[EmailMessage], Awaitable[object]]


def retry_queue(failures: int) -> str:
    return f"{EMAIL_QUEUE}.retry.{failures}"


async def declare_queues(channel: AbstractChannel, retry_delays: tuple[float, ...]) -> None:
    await channel.declare_queue(EMAIL_QUEUE, durable=True)
    await channel.declare_queue(DEAD_LETTER_QUEUE, durable=True)
    # Uma fila por tentativa, cada uma com TTL fixo: ao expirar, a mensagem volta para a fila
    # principal. Backoff crescente sem plugin e sem o bloqueio de TTLs diferentes na mesma fila.
    for failures, delay in enumerate(retry_delays, start=1):
        await channel.declare_queue(
            retry_queue(failures),
            durable=True,
            arguments={
                "x-message-ttl": int(delay * 1000),
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": EMAIL_QUEUE,
            },
        )


async def _publish(channel: AbstractChannel, body: bytes, queue: str, failures: int) -> None:
    await channel.default_exchange.publish(
        Message(
            body, headers={"x-failed-attempts": failures}, delivery_mode=DeliveryMode.PERSISTENT
        ),
        routing_key=queue,
    )


async def publish(channel: AbstractChannel, message: EmailMessage) -> None:
    await _publish(channel, message.as_bytes(), EMAIL_QUEUE, 0)


async def deliver(
    message: AbstractIncomingMessage,
    channel: AbstractChannel,
    send: Send,
    retry_delays: tuple[float, ...],
) -> None:
    try:
        await send(email.message_from_bytes(message.body, policy=policy.default))
    except (SMTPException, OSError) as error:
        failures = int(message.headers.get("x-failed-attempts", 0)) + 1  # type: ignore[arg-type]
        queue = retry_queue(failures) if failures <= len(retry_delays) else DEAD_LETTER_QUEUE
        logger.warning(
            "E-mail delivery failed (%s), attempt %s, moving to %s", error, failures, queue
        )
        await _publish(channel, message.body, queue, failures)
    await message.ack()


async def run_worker(channel: AbstractChannel, send: Send, retry_delays: tuple[float, ...]) -> None:
    queue = await channel.get_queue(EMAIL_QUEUE)
    async with queue.iterator() as messages:
        async for message in messages:
            await deliver(message, channel, send, retry_delays)
