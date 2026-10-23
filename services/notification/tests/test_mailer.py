import asyncio
from contextlib import asynccontextmanager, suppress
from email.message import EmailMessage

import aio_pika
import pytest
from testcontainers.community.rabbitmq import RabbitMqContainer

from notification import mailer

RETRY_DELAYS = (0.2, 0.2)


@pytest.fixture(scope="module")
def rabbitmq_url():
    with RabbitMqContainer("rabbitmq:4.2-management-alpine") as rabbitmq:
        params = rabbitmq.get_connection_params()
        yield f"amqp://guest:guest@{params.host}:{params.port}/"


@pytest.fixture
async def channel(rabbitmq_url):
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()
    await mailer.declare_queues(channel, RETRY_DELAYS)
    yield channel
    for queue in (mailer.EMAIL_QUEUE, mailer.DEAD_LETTER_QUEUE, *map(mailer.retry_queue, (1, 2))):
        await channel.queue_delete(queue)
    await connection.close()


@asynccontextmanager
async def worker(channel, send):
    task = asyncio.create_task(mailer.run_worker(channel, send, RETRY_DELAYS))
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


async def eventually(condition):
    async with asyncio.timeout(10):
        while not condition():
            await asyncio.sleep(0.05)


def email() -> EmailMessage:
    message = EmailMessage()
    message["To"] = "maria@example.com"
    message["Subject"] = "Agendamento confirmado"
    message.set_content("Tudo certo!")
    return message


async def test_queued_email_is_sent(channel):
    sent = []

    async def send(message):
        sent.append(message["Subject"])

    await mailer.publish(channel, email())
    async with worker(channel, send):
        await eventually(lambda: sent)

    assert sent == ["Agendamento confirmado"]


async def test_failing_email_is_retried_with_backoff_then_dead_lettered(channel):
    attempts = 0

    async def send(message):
        nonlocal attempts
        attempts += 1
        raise OSError("SMTP indisponível")

    dead_letters = await channel.get_queue(mailer.DEAD_LETTER_QUEUE)
    await mailer.publish(channel, email())
    async with worker(channel, send), asyncio.timeout(10):
        while (dead := await dead_letters.get(fail=False)) is None:
            await asyncio.sleep(0.05)

    assert attempts == len(RETRY_DELAYS) + 1
    assert dead.headers["x-failed-attempts"] == 3


async def test_transient_failure_recovers_on_retry(channel):
    attempts = []

    async def send(message):
        attempts.append(message["Subject"])
        if len(attempts) == 1:
            raise OSError("SMTP indisponível")

    await mailer.publish(channel, email())
    async with worker(channel, send):
        await eventually(lambda: len(attempts) == 2)

    dead_letters = await channel.get_queue(mailer.DEAD_LETTER_QUEUE)
    assert await dead_letters.get(fail=False) is None
