import asyncio
import json
from datetime import UTC, datetime, timedelta
from datetime import time as clock
from pathlib import Path
from uuid import uuid4

import pytest
from pact import Verifier
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_bookings_api import ISSUER, KEY, token

from booking import events
from booking.catalog_client import Business, Professional, Service, WorkingHours
from booking.main import create_app
from booking.models import Booking, OutboxEvent
from vagacerta_auth import TokenVerifier

PACTS = Path(__file__).parents[3] / "pacts"


class StateCatalog:
    business: Business | None = None

    async def get_business(self, business_id):
        return self.business


def schedule(parameters: dict) -> Business:
    return Business(
        id=parameters["business_id"],
        name="Barbearia Navalha de Ouro",
        address="Av. Brasil, 1200",
        timezone="America/Sao_Paulo",
        professionals=[
            Professional(
                id=parameters["professional_id"],
                name="Rafael Costa",
                working_hours=[
                    WorkingHours(weekday=d, start=clock(9), end=clock(12)) for d in range(7)
                ],
            )
        ],
        services=[
            Service(
                id=parameters["service_id"],
                name="Corte masculino",
                duration_minutes=30,
                price_cents=4500,
            )
        ],
    )


def booking(parameters: dict, **fields) -> Booking:
    starts_at = datetime.fromisoformat(parameters["starts_at"])
    return Booking(
        id=parameters["booking_id"],
        business_id=parameters["business_id"],
        professional_id=parameters["professional_id"],
        service_id=parameters["service_id"],
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        customer_name="Ana Souza",
        customer_email="ana@example.com",
        **fields,
    )


async def reset(database_url: str, *rows: Booking) -> None:
    engine = create_async_engine(database_url)
    async with async_sessionmaker(engine)() as session:
        await session.execute(text("TRUNCATE bookings, outbox"))
        session.add_all(rows)
        await session.commit()
    await engine.dispose()


@pytest.fixture(scope="module")
def catalog():
    return StateCatalog()


@pytest.fixture(scope="module")
def provider_url(database_url, catalog, serve):
    yield serve(
        create_app(database_url, catalog, TokenVerifier(ISSUER, lambda _: KEY.public_key()))
    )
    asyncio.run(reset(database_url))


def message(event: OutboxEvent) -> dict[str, object]:
    return {"contents": json.dumps(event.payload).encode(), "content_type": "application/json"}


def outcome(booking: Booking, status: str) -> dict[str, object]:
    booking.status = status
    return message(events.booking_outcome(booking))


def test_booking_honours_its_consumer_contracts(database_url, catalog, provider_url):
    def state_handler(state, parameters):
        # As interações de mensagem chegam com o estado vazio: não há o que preparar.
        if not state:
            return
        catalog.business = schedule(parameters)
        now = datetime.now(UTC)
        rows = {
            "a confirmed booking exists": [booking(parameters, status="confirmed")],
            "a hold exists": [
                booking(parameters, status="held", hold_expires_at=now + timedelta(minutes=15))
            ],
            "an expired hold exists": [
                booking(parameters, status="held", hold_expires_at=now - timedelta(minutes=1))
            ],
        }.get(state, [])
        asyncio.run(reset(database_url, *rows))

    ids = {
        "business_id": uuid4(),
        "professional_id": uuid4(),
        "service_id": uuid4(),
        "booking_id": uuid4(),
    }
    sample = booking({**ids, "starts_at": "2030-01-08T13:00:00+00:00"}, status="confirmed")
    business = schedule(ids)
    (
        Verifier("booking", host="127.0.0.1")
        .add_transport(url=provider_url)
        .message_handler(
            {
                "a booking.created event": message(
                    events.booking_created(
                        sample, business, business.professionals[0], business.services[0]
                    )
                ),
                "a booking.cancelled event": message(events.booking_cancelled(sample)),
                "a booking.completed event": outcome(sample, "completed"),
                "a booking.no_show event": outcome(sample, "no_show"),
            }
        )
        .add_source(PACTS / "waitlist-booking.json")
        .add_source(PACTS / "notification-booking.json")
        .add_source(PACTS / "analytics-booking.json")
        .add_source(PACTS / "mcp-server-booking.json")
        .add_custom_headers(token("booking-holds"))
        .state_handler(state_handler)
        .verify()
    )
