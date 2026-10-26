import asyncio
from datetime import time as clock
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from pact import Verifier
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from catalog.main import create_app
from catalog.models import Business, Professional, Service, WorkingHours
from vagacerta_auth import TokenVerifier

PACTS = Path(__file__).parents[3] / "pacts"


@pytest.fixture(scope="module")
def database_url():
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield url


@pytest.fixture(scope="module")
def provider_url(database_url, serve):
    return serve(
        create_app(database_url, TokenVerifier("http://keycloak.test", lambda _: "unused"))
    )


async def prepare(database_url: str, state: str, parameters: dict[str, str]) -> None:
    engine = create_async_engine(database_url)
    async with async_sessionmaker(engine)() as session:
        await session.execute(text("TRUNCATE businesses CASCADE"))
        if state == "a business with a professional and a service exists":
            business = UUID(parameters["business_id"])
            session.add(
                Business(
                    id=business,
                    name="Barbearia Navalha de Ouro",
                    category="barbearia",
                    description="Cortes e barba",
                    address="Av. Brasil, 1200",
                    timezone="America/Sao_Paulo",
                    professionals=[
                        Professional(
                            id=UUID(parameters["professional_id"]),
                            name="Rafael Costa",
                            specialty="Barbeiro",
                            working_hours=[WorkingHours(weekday=1, start=clock(9), end=clock(12))],
                        )
                    ],
                    services=[
                        Service(
                            id=UUID(parameters["service_id"]),
                            name="Corte masculino",
                            duration_minutes=30,
                            price_cents=4500,
                        )
                    ],
                )
            )
        await session.commit()
    await engine.dispose()


def test_catalog_honours_its_consumer_contracts(database_url, provider_url):
    def state_handler(state, action, parameters):
        asyncio.run(prepare(database_url, state, parameters or {}))

    (
        Verifier("catalog", host="127.0.0.1")
        .add_transport(url=provider_url)
        .add_source(PACTS / "booking-catalog.json")
        .add_source(PACTS / "waitlist-catalog.json")
        .add_source(PACTS / "mcp-server-catalog.json")
        .add_source(PACTS / "analytics-catalog.json")
        .state_handler(state_handler)
        .verify()
    )
