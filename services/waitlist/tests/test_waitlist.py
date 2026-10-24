from datetime import UTC, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from waitlist import saga
from waitlist.booking_client import Hold
from waitlist.catalog_client import Business, Professional, Service
from waitlist.events import BookingCancelled, FreedSlot
from waitlist.main import create_app
from waitlist.models import Entry, Offer, OutboxEvent

TZ = ZoneInfo("America/Sao_Paulo")
TOMORROW = datetime.now(TZ).date() + timedelta(days=1)
SLOT = datetime.combine(TOMORROW, time(10), TZ)
PROFESSIONAL = Professional(id=uuid4(), name="Dra. Fernanda Lima")
SERVICE = Service(id=uuid4(), name="Avaliação", price_cents=0)
BUSINESS = Business(
    id=uuid4(),
    name="Clínica Teste",
    address="Rua A, 1",
    timezone=str(TZ),
    professionals=[PROFESSIONAL],
    services=[SERVICE],
)


class FakeCatalog:
    async def get_business(self, business_id):
        return BUSINESS if business_id == BUSINESS.id else None


class FakeBooking:
    def __init__(self):
        self.status = {}
        self.unavailable_for = set()

    async def hold(self, entry, starts_at, minutes):
        if entry.customer_email in self.unavailable_for:
            return None
        hold = Hold(
            id=uuid4(),
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
            hold_expires_at=datetime.now(UTC) + timedelta(minutes=minutes),
        )
        self.status[hold.id] = "held"
        return hold

    async def confirm(self, booking_id):
        if self.status[booking_id] == "held":
            self.status[booking_id] = "confirmed"
        return self.status[booking_id] == "confirmed"

    async def release(self, booking_id):
        if self.status[booking_id] == "confirmed":
            return False
        self.status[booking_id] = "released"
        return True


@pytest.fixture(scope="module")
def app(database_url):
    return create_app(database_url, FakeCatalog(), FakeBooking())


@pytest.fixture
def booking(app):
    app.state.booking = FakeBooking()
    return app.state.booking


@pytest.fixture
async def client(app, booking):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
    async with app.state.sessionmaker() as session:
        await session.execute(text("TRUNCATE entries, offers, outbox, processed_events"))
        await session.commit()


@pytest.fixture
async def session(app, client):
    async with app.state.sessionmaker() as session:
        yield session


async def join(client, email, day=TOMORROW):
    return await client.post(
        "/entries",
        json={
            "business_id": str(BUSINESS.id),
            "professional_id": str(PROFESSIONAL.id),
            "service_id": str(SERVICE.id),
            "day": str(day),
            "customer_name": "Cliente Teste",
            "customer_email": email,
        },
    )


def cancellation(starts_at=SLOT):
    return BookingCancelled(
        event_id=uuid4(),
        type="booking.cancelled",
        data=FreedSlot(booking_id=uuid4(), professional_id=PROFESSIONAL.id, starts_at=starts_at),
    )


async def offers_by_email(session) -> dict[str, str]:
    offers = await session.scalars(select(Offer).execution_options(populate_existing=True))
    return {offer.entry.customer_email: offer.status for offer in offers}


async def published_types(session) -> list[str]:
    events = await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id))
    return [event.payload["type"] for event in events]


async def test_joining_returns_the_position_in_line(client):
    first = await join(client, "ana@example.com")
    second = await join(client, "bia@example.com")

    assert first.status_code == second.status_code == 201
    assert (first.json()["position"], second.json()["position"]) == (1, 2)


async def test_cannot_join_the_same_day_twice(client):
    await join(client, "ana@example.com")

    assert (await join(client, "ana@example.com")).status_code == 409


async def test_cannot_join_a_past_day(client):
    response = await join(client, "ana@example.com", day=TOMORROW - timedelta(days=2))

    assert response.status_code == 422


async def test_freed_slot_is_held_and_offered_to_the_first_in_line(client, session, booking):
    await join(client, "ana@example.com")
    await join(client, "bia@example.com")

    await saga.handle_cancellation(cancellation(), session, booking, minutes=15)

    events = (await session.scalars(select(OutboxEvent))).all()
    assert await offers_by_email(session) == {"ana@example.com": "pending"}
    assert [e.payload["data"]["customer_email"] for e in events] == ["ana@example.com"]
    assert events[0].payload["data"]["professional_name"] == "Dra. Fernanda Lima"


async def test_redelivered_cancellation_creates_a_single_offer(client, session, booking):
    await join(client, "ana@example.com")
    await join(client, "bia@example.com")
    event = cancellation()

    await saga.handle_cancellation(event, session, booking, minutes=15)
    await saga.handle_cancellation(event, session, booking, minutes=15)

    assert len(await offers_by_email(session)) == 1


async def test_person_the_slot_does_not_fit_is_skipped(client, session, booking):
    await join(client, "ana@example.com")
    await join(client, "bia@example.com")
    booking.unavailable_for.add("ana@example.com")

    await saga.handle_cancellation(cancellation(), session, booking, minutes=15)

    assert await offers_by_email(session) == {"bia@example.com": "pending"}


async def test_slot_on_another_day_is_not_offered(client, session, booking):
    await join(client, "ana@example.com")

    await saga.handle_cancellation(
        cancellation(SLOT + timedelta(days=1)), session, booking, minutes=15
    )

    assert await offers_by_email(session) == {}


async def test_claiming_the_offer_confirms_the_booking(client, session, booking):
    await join(client, "ana@example.com")
    offer = await saga.offer_slot(session, booking, PROFESSIONAL.id, SLOT, 15)
    await session.commit()

    claimed = await client.post(f"/offers/{offer.id}/claim")

    assert claimed.json()["status"] == "claimed"
    assert booking.status[offer.booking_id] == "confirmed"
    assert await published_types(session) == ["waitlist.offer_created", "waitlist.offer_claimed"]
    assert (await client.get(f"/offers/{offer.id}")).json()["entry"]["details"]["service_name"] == (
        "Avaliação"
    )


async def test_expired_offer_is_released_and_goes_to_the_next_in_line(client, session, booking):
    await join(client, "ana@example.com")
    await join(client, "bia@example.com")
    first = await saga.offer_slot(session, booking, PROFESSIONAL.id, SLOT, 15)
    await session.commit()

    await saga.expire_offers(session, booking, first.expires_at + timedelta(seconds=1), 15)

    assert booking.status[first.booking_id] == "released"
    assert await published_types(session) == [
        "waitlist.offer_created",
        "waitlist.offer_expired",
        "waitlist.offer_created",
    ]
    assert await offers_by_email(session) == {
        "ana@example.com": "expired",
        "bia@example.com": "pending",
    }
    assert (await client.post(f"/offers/{first.id}/claim")).status_code == 409
    entry = await session.scalar(select(Entry).where(Entry.customer_email == "ana@example.com"))
    assert entry.status == "waiting"


async def test_offer_confirmed_before_expiring_is_kept(client, session, booking):
    await join(client, "ana@example.com")
    offer = await saga.offer_slot(session, booking, PROFESSIONAL.id, SLOT, 15)
    await session.commit()
    await booking.confirm(offer.booking_id)

    await saga.expire_offers(session, booking, offer.expires_at + timedelta(seconds=1), 15)

    assert await offers_by_email(session) == {"ana@example.com": "claimed"}
