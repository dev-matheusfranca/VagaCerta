import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pact import Verifier
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from waitlist.catalog_client import Business, Professional, Service
from waitlist.events import offer_event
from waitlist.main import create_app
from waitlist.models import Entry, Offer

PACTS = Path(__file__).parents[3] / "pacts"


class StateCatalog:
    business: Business | None = None

    async def get_business(self, business_id):
        return self.business


async def reset(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with async_sessionmaker(engine)() as session:
        await session.execute(text("TRUNCATE entries, offers, outbox, processed_events"))
        await session.commit()
    await engine.dispose()


@pytest.fixture(scope="module")
def catalog():
    return StateCatalog()


@pytest.fixture(scope="module")
def provider_url(database_url, catalog, serve):
    yield serve(create_app(database_url, catalog, None))
    asyncio.run(reset(database_url))


def test_waitlist_honours_its_consumer_contracts(database_url, catalog, provider_url):
    def state_handler(state, parameters):
        # As interações de mensagem chegam com o estado vazio: não há o que preparar.
        if not state:
            return
        catalog.business = Business(
            id=parameters["business_id"],
            name="Barbearia Navalha de Ouro",
            address="Av. Brasil, 1200",
            timezone="America/Sao_Paulo",
            professionals=[Professional(id=parameters["professional_id"], name="Rafael Costa")],
            services=[
                Service(id=parameters["service_id"], name="Corte masculino", price_cents=4500)
            ],
        )
        asyncio.run(reset(database_url))

    entry = Entry(
        business_id=uuid4(),
        professional_id=uuid4(),
        service_id=uuid4(),
        customer_name="Ana Souza",
        customer_email="ana@example.com",
        details={
            "business_name": "Clínica Sorriso Pleno",
            "business_address": "Av. Tiradentes, 890",
            "timezone": "America/Sao_Paulo",
            "professional_name": "Dra. Fernanda Lima",
            "service_name": "Avaliação",
            "price_cents": 12000,
        },
    )
    offer = Offer(
        id=uuid4(),
        entry=entry,
        booking_id=uuid4(),
        starts_at=datetime(2030, 1, 8, 13, tzinfo=UTC),
        ends_at=datetime(2030, 1, 8, 13, 30, tzinfo=UTC),
        expires_at=datetime(2030, 1, 7, 13, 15, tzinfo=UTC),
    )
    messages = {
        f"a {type} event": {
            "contents": json.dumps(offer_event(offer, type).payload).encode(),
            "content_type": "application/json",
        }
        for type in ("waitlist.offer_created", "waitlist.offer_claimed", "waitlist.offer_expired")
    }
    (
        Verifier("waitlist", host="127.0.0.1")
        .add_transport(url=provider_url)
        .message_handler(messages)
        .add_source(PACTS / "notification-waitlist.json")
        .add_source(PACTS / "analytics-waitlist.json")
        .add_source(PACTS / "mcp-server-waitlist.json")
        .add_source(PACTS / "audit-waitlist.json")
        .state_handler(state_handler)
        .verify()
    )
