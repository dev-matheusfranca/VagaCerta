from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from analytics.catalog_client import Schedule
from analytics.events import (
    BookedSlot,
    BookingCancelled,
    BookingCreated,
    BookingOutcome,
    BookingRef,
    OfferEvent,
)
from analytics.main import create_app
from analytics.projections import apply
from vagacerta_auth import AUDIENCE, TokenVerifier

ISSUER = "http://keycloak.test/realms/vagacerta"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
BUSINESS = uuid4()
DAY = date(2030, 1, 9)
NINE_AM = datetime(2030, 1, 9, 12, tzinfo=UTC)
# Quarta-feira, das 9h às 12h: 180 minutos de expediente.
SCHEDULE = Schedule.model_validate(
    {"professionals": [{"working_hours": [{"weekday": 2, "start": "09:00", "end": "12:00"}]}]}
)


class FakeCatalog:
    available = True

    async def schedule(self, business_id):
        return SCHEDULE if self.available else None


def token(*businesses: str) -> dict[str, str]:
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "realm_access": {"roles": ["owner"]},
        "businesses": list(businesses),
    }
    return {"Authorization": f"Bearer {jwt.encode(claims, KEY, algorithm='RS256')}"}


@pytest.fixture(scope="module")
def app():
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield create_app(url, TokenVerifier(ISSUER, lambda _: KEY.public_key()), FakeCatalog())


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://test", headers=token(str(BUSINESS))
    ) as client:
        yield client
    async with app.state.sessionmaker() as session:
        await session.execute(
            text("TRUNCATE daily_stats, hourly_stats, bookings, processed_events")
        )
        await session.commit()


@pytest.fixture
async def session(app, client):
    async with app.state.sessionmaker() as session:
        yield session


def created(booking_id, price_cents=4500, starts_at=NINE_AM):
    slot = BookedSlot(
        booking_id=booking_id,
        business_id=BUSINESS,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        timezone="America/Sao_Paulo",
        price_cents=price_cents,
    )
    return BookingCreated(event_id=uuid4(), type="booking.created", data=slot)


def cancelled(booking_id):
    data = BookingRef(booking_id=booking_id)
    return BookingCancelled(event_id=uuid4(), type="booking.cancelled", data=data)


def outcome(booking_id, type):
    data = BookingRef(booking_id=booking_id)
    return BookingOutcome(event_id=uuid4(), type=type, data=data)


def offer(outcome, price_cents=4500):
    return OfferEvent(
        event_id=uuid4(),
        type=f"waitlist.offer_{outcome}",
        data={
            "business_id": BUSINESS,
            "starts_at": NINE_AM,
            "timezone": "America/Sao_Paulo",
            "price_cents": price_cents,
        },
    )


async def stats_of(client, day=DAY):
    response = await client.get(
        f"/businesses/{BUSINESS}/stats", params={"from": str(day), "to": str(day)}
    )
    return response.json()


async def test_bookings_and_cancellations_add_up_per_day(client, session):
    first, second = uuid4(), uuid4()
    for event in (created(first, 4500), created(second, 7000), cancelled(first)):
        await apply(event, session)

    [day] = await stats_of(client)

    assert (day["bookings"], day["cancellations"], day["revenue_cents"]) == (2, 1, 7000)


async def test_redelivered_event_is_counted_once(client, session):
    event = created(uuid4())

    await apply(event, session)
    await apply(event, session)

    assert (await stats_of(client))[0]["bookings"] == 1


async def test_waitlist_recovery_is_measured(client, session):
    for event in (offer("created"), offer("claimed"), offer("created"), offer("expired")):
        await apply(event, session)

    [day] = await stats_of(client)

    assert (day["offers"], day["offers_claimed"], day["offers_expired"]) == (2, 1, 1)
    assert day["recovered_revenue_cents"] == 4500


async def test_late_appointment_counts_on_the_local_day(client, session):
    ten_pm_local = datetime(2030, 1, 10, 1, tzinfo=UTC)

    await apply(created(uuid4(), starts_at=ten_pm_local), session)

    assert [day["day"] for day in await stats_of(client)] == [str(DAY)]


async def test_only_owners_of_the_business_see_its_stats(client):
    params = {"from": str(DAY), "to": str(DAY)}
    url = f"/businesses/{BUSINESS}/stats"

    anonymous = await client.get(url, params=params, headers={"Authorization": ""})
    stranger = await client.get(url, params=params, headers=token(str(uuid4())))

    assert (anonymous.status_code, stranger.status_code) == (401, 403)


async def test_attendance_no_shows_and_occupancy_are_measured(client, session):
    came, missed = uuid4(), uuid4()
    for event in (
        created(came),
        created(missed),
        outcome(came, "booking.completed"),
        outcome(missed, "booking.no_show"),
    ):
        await apply(event, session)

    [day] = await stats_of(client)

    assert (day["completed"], day["no_shows"]) == (1, 1)
    assert (day["booked_minutes"], day["capacity_minutes"]) == (60, 180)


async def test_stats_cover_every_day_of_the_range(client, session):
    await apply(created(uuid4()), session)

    response = await client.get(
        f"/businesses/{BUSINESS}/stats",
        params={"from": str(DAY - timedelta(days=1)), "to": str(DAY + timedelta(days=1))},
    )

    assert [d["bookings"] for d in response.json()] == [0, 1, 0]
    assert [d["capacity_minutes"] for d in response.json()] == [0, 180, 0]


async def test_without_the_catalog_stats_come_without_capacity(app, client, session):
    await apply(created(uuid4()), session)
    app.state.catalog.available = False
    try:
        [day] = await stats_of(client)
    finally:
        app.state.catalog.available = True

    assert (day["bookings"], day["capacity_minutes"]) == (1, None)


async def test_peak_hours_follow_the_local_time_of_confirmed_bookings(client, session):
    kept, dropped = uuid4(), uuid4()
    for event in (created(kept), created(uuid4()), created(dropped), cancelled(dropped)):
        await apply(event, session)

    response = await client.get(f"/businesses/{BUSINESS}/peak-hours")

    assert response.json() == [{"weekday": 2, "hour": 9, "bookings": 2}]
