import asyncio
from datetime import datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from booking.catalog_client import Business, Professional, Service, WorkingHours
from booking.main import create_app
from booking.models import OutboxEvent

TZ = ZoneInfo("America/Sao_Paulo")
TOMORROW = datetime.now(TZ).date() + timedelta(days=1)
PROFESSIONAL = Professional(
    id=uuid4(),
    name="Rafael Costa",
    working_hours=[WorkingHours(weekday=d, start=time(9), end=time(12)) for d in range(7)],
)
SERVICE = Service(id=uuid4(), name="Corte", duration_minutes=60, price_cents=4500)
BUSINESS = Business(
    id=uuid4(),
    name="Barbearia Teste",
    address="Rua A, 1",
    timezone=str(TZ),
    professionals=[PROFESSIONAL],
    services=[SERVICE],
)
SCHEDULE = {
    "business_id": str(BUSINESS.id),
    "professional_id": str(PROFESSIONAL.id),
    "service_id": str(SERVICE.id),
}


class FakeCatalog:
    async def get_business(self, business_id):
        return BUSINESS if business_id == BUSINESS.id else None


def booking(hour: int, minute: int = 0, **overrides):
    starts_at = datetime.combine(TOMORROW, time(hour, minute), TZ)
    return {
        **SCHEDULE,
        "starts_at": starts_at.isoformat(),
        "customer_name": "Maria Silva",
        "customer_email": "maria@example.com",
        **overrides,
    }


async def free_hours(client) -> list[str]:
    response = await client.get("/availability", params={**SCHEDULE, "date": str(TOMORROW)})
    return [
        datetime.fromisoformat(s).astimezone(TZ).strftime("%H:%M") for s in response.json()["slots"]
    ]


@pytest.fixture(scope="module")
def app(database_url):
    return create_app(database_url, FakeCatalog())


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
    async with app.state.sessionmaker() as session:
        await session.execute(text("TRUNCATE bookings, outbox"))
        await session.commit()


async def test_offers_every_slot_of_an_empty_day(client):
    assert await free_hours(client) == ["09:00", "09:30", "10:00", "10:30", "11:00"]


async def test_booked_time_leaves_availability(client):
    response = await client.post("/bookings", json=booking(10))

    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"
    assert await free_hours(client) == ["09:00", "11:00"]


async def test_overlapping_booking_is_rejected(client):
    await client.post("/bookings", json=booking(9))

    response = await client.post("/bookings", json=booking(9, 30))

    assert response.status_code == 409


async def test_only_one_of_many_simultaneous_requests_gets_the_slot(client):
    responses = await asyncio.gather(
        *(
            client.post("/bookings", json=booking(10, customer_name=f"Cliente {i}"))
            for i in range(10)
        )
    )

    assert sorted(r.status_code for r in responses) == [201] + [409] * 9


async def test_rejects_time_outside_working_hours(client):
    response = await client.post("/bookings", json=booking(13))

    assert response.status_code == 422


async def test_rejects_unknown_professional(client):
    response = await client.post("/bookings", json=booking(9, professional_id=str(uuid4())))

    assert response.status_code == 404


async def test_cancelled_time_can_be_booked_again(client):
    created = (await client.post("/bookings", json=booking(9))).json()

    cancelled = await client.post(f"/bookings/{created['id']}/cancel")

    assert cancelled.json()["status"] == "cancelled"
    assert "09:00" in await free_hours(client)
    assert (await client.post("/bookings", json=booking(9))).status_code == 201


async def test_unknown_booking_returns_404(client):
    assert (await client.get(f"/bookings/{uuid4()}")).status_code == 404


async def outbox(app) -> list[dict]:
    async with app.state.sessionmaker() as session:
        return [e.payload for e in await session.scalars(select(OutboxEvent).order_by("id"))]


async def test_booking_and_cancellation_are_recorded_in_the_outbox(app, client):
    created = (await client.post("/bookings", json=booking(9))).json()
    await client.post(f"/bookings/{created['id']}/cancel")
    await client.post(f"/bookings/{created['id']}/cancel")

    events = await outbox(app)

    assert [e["type"] for e in events] == ["booking.created", "booking.cancelled"]
    assert {e["data"]["booking_id"] for e in events} == {created["id"]}
    assert events[0]["data"]["professional_name"] == "Rafael Costa"
    assert events[0]["data"]["customer_email"] == "maria@example.com"


async def test_rejected_booking_publishes_nothing(app, client):
    await client.post("/bookings", json=booking(9))

    await client.post("/bookings", json=booking(9, 30))

    assert len(await outbox(app)) == 1
