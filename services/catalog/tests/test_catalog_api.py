from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from testcontainers.community.postgres import PostgresContainer

from catalog.main import create_app

BUSINESS = {
    "name": "Barbearia Teste",
    "category": "barbearia",
    "description": "Cortes e barba",
    "address": "Rua A, 1",
}
PROFESSIONAL = {
    "name": "Rafael",
    "specialty": "Barbeiro",
    "working_hours": [
        {"weekday": 1, "start": "09:00", "end": "12:00"},
        {"weekday": 1, "start": "13:00", "end": "18:00"},
    ],
}


@pytest.fixture(scope="module")
def app():
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        yield create_app(url)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
    async with app.state.sessionmaker() as session:
        await session.execute(text("TRUNCATE businesses CASCADE"))
        await session.commit()


async def test_business_detail_includes_professionals_and_services(client):
    business = (await client.post("/businesses", json=BUSINESS)).json()

    professional = await client.post(
        f"/businesses/{business['id']}/professionals", json=PROFESSIONAL
    )
    service = await client.post(
        f"/businesses/{business['id']}/services",
        json={"name": "Corte", "duration_minutes": 30, "price_cents": 4500},
    )
    detail = (await client.get(f"/businesses/{business['id']}")).json()

    assert professional.status_code == service.status_code == 201
    assert business["timezone"] == "America/Sao_Paulo"
    assert detail["professionals"] == [professional.json()]
    assert detail["professionals"][0]["working_hours"][0] == {
        "weekday": 1,
        "start": "09:00:00",
        "end": "12:00:00",
    }
    assert detail["services"] == [service.json()]


async def test_lists_businesses_by_name(client):
    for name in ("Studio Zeta", "Clínica Alfa"):
        await client.post("/businesses", json={**BUSINESS, "name": name})

    response = await client.get("/businesses")

    assert [business["name"] for business in response.json()] == ["Clínica Alfa", "Studio Zeta"]


async def test_unknown_business_returns_404(client):
    unknown = uuid4()

    assert (await client.get(f"/businesses/{unknown}")).status_code == 404
    assert (
        await client.post(f"/businesses/{unknown}/professionals", json=PROFESSIONAL)
    ).status_code == 404


async def test_rejects_working_hours_that_end_before_they_start(client):
    business = (await client.post("/businesses", json=BUSINESS)).json()
    invalid = {**PROFESSIONAL, "working_hours": [{"weekday": 1, "start": "18:00", "end": "09:00"}]}

    response = await client.post(f"/businesses/{business['id']}/professionals", json=invalid)

    assert response.status_code == 422


async def test_rejects_unknown_timezone(client):
    response = await client.post("/businesses", json={**BUSINESS, "timezone": "Mars/Olympus"})

    assert response.status_code == 422
