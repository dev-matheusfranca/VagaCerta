import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from vagacerta_auth import AUDIENCE, TokenVerifier
from webhooks import deliveries
from webhooks.main import create_app
from webhooks.models import Delivery, Subscription

ISSUER = "http://keycloak.test/realms/vagacerta"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
BUSINESS = uuid4()
HOOK = "https://93.184.216.34/vagacerta"


def owner(business=BUSINESS) -> dict[str, str]:
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "realm_access": {"roles": ["owner"]},
        "businesses": [str(business)],
    }
    return {"Authorization": f"Bearer {jwt.encode(claims, KEY, algorithm='RS256')}"}


def event(type="booking.created", occurred_at=None) -> dict:
    return {
        "event_id": str(uuid4()),
        "type": type,
        "occurred_at": (occurred_at or datetime.now(UTC)).isoformat(),
        "data": {"business_id": str(BUSINESS), "booking_id": str(uuid4())},
    }


@pytest.fixture(scope="module")
def app(database_url):
    return create_app(database_url, TokenVerifier(ISSUER, lambda _: KEY.public_key()), False)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
    async with app.state.sessionmaker() as session:
        await session.execute(text("TRUNCATE subscriptions CASCADE"))
        await session.commit()


@pytest.fixture
async def session(app, client):
    async with app.state.sessionmaker() as session:
        yield session


async def subscribe(client, events=("booking.created",)) -> dict:
    response = await client.post(
        f"/businesses/{BUSINESS}/webhooks",
        json={"url": HOOK, "events": list(events)},
        headers=owner(),
    )
    assert response.status_code == 201
    return response.json()


async def test_the_secret_is_shown_once_and_internal_urls_are_refused(client):
    created = await subscribe(client)
    internal = await client.post(
        f"/businesses/{BUSINESS}/webhooks",
        json={"url": "http://169.254.169.254/latest", "events": ["booking.created"]},
        headers=owner(),
    )
    listed = await client.get(f"/businesses/{BUSINESS}/webhooks", headers=owner())
    stranger = await client.get(f"/businesses/{BUSINESS}/webhooks", headers=owner(uuid4()))

    assert len(created["secret"]) == 48
    assert internal.status_code == 422
    assert "secret" not in listed.json()[0]
    assert stranger.status_code == 403


async def test_each_interested_subscription_gets_one_delivery(client, session):
    await subscribe(client, ("booking.created",))
    await subscribe(client, ("booking.cancelled",))
    created = event("booking.created")

    first = await deliveries.fan_out(session, created)
    again = await deliveries.fan_out(session, created)
    before = await deliveries.fan_out(
        session, event(occurred_at=datetime.now(UTC) - timedelta(days=1))
    )

    assert len(first) == 1
    assert again == first
    assert before == []


async def test_the_delivery_is_signed_with_the_subscription_secret(client, session):
    secret = (await subscribe(client))["secret"]
    [delivery_id] = await deliveries.fan_out(session, event())
    received = []

    def destination(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(204)

    http = httpx.AsyncClient(transport=httpx.MockTransport(destination))
    status = await deliveries.attempt(session, delivery_id, http, allow_private=False, last=False)

    [request] = received
    expected = hmac.new(secret.encode(), request.content, hashlib.sha256).hexdigest()
    assert status == "delivered"
    assert request.headers["X-VagaCerta-Signature"] == f"sha256={expected}"
    assert json.loads(request.content)["type"] == "booking.created"


class FakeChannel:
    def __init__(self):
        self.published: list[tuple[str, int]] = []

    @property
    def default_exchange(self):
        return self

    async def publish(self, message, routing_key):
        self.published.append((routing_key, message.headers["x-failed-attempts"]))


class FakeMessage:
    def __init__(self, delivery_id, failures):
        self.body = str(delivery_id).encode()
        self.headers = {"x-failed-attempts": failures}
        self.acked = False

    async def ack(self):
        self.acked = True


@pytest.mark.parametrize(
    ("failures", "status_code", "queue", "final"),
    [
        (0, 500, "webhooks.delivery.retry.1", "pending"),
        (3, 500, "webhooks.delivery.dead", "failed"),
        (3, 200, None, "delivered"),
    ],
)
async def test_failures_are_retried_and_then_dead_lettered(
    app, client, session, failures, status_code, queue, final
):
    await subscribe(client)
    [delivery_id] = await deliveries.fan_out(session, event())
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(status_code)))
    channel, message = FakeChannel(), FakeMessage(delivery_id, failures)

    await deliveries.handle(message, channel, app.state.sessionmaker, http, False, (5, 30, 120))

    async with app.state.sessionmaker() as fresh:
        delivery = await fresh.get_one(Delivery, delivery_id)
    assert [q for q, _ in channel.published] == ([queue] if queue else [])
    assert (delivery.status, delivery.last_status_code, message.acked) == (final, status_code, True)


async def test_unsubscribing_removes_the_deliveries(client, session):
    created = await subscribe(client)
    await deliveries.fan_out(session, event())

    response = await client.delete(
        f"/businesses/{BUSINESS}/webhooks/{created['id']}", headers=owner()
    )

    assert response.status_code == 204
    assert await session.get(Subscription, created["id"]) is None
