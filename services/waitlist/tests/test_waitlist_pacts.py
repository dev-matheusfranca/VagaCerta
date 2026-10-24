from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pact import Pact, match

from waitlist.booking_client import BookingClient
from waitlist.catalog_client import CatalogClient
from waitlist.events import BookingCancelled
from waitlist.models import Entry

PACTS = Path(__file__).parents[3] / "pacts"
SLOT = {
    "business_id": "711fa378-fb4e-429e-bd5e-6a3f856ab875",
    "professional_id": "3a4b5c6d-7e8f-4901-a2b3-c4d5e6f7a8b9",
    "service_id": "9c8b7a6d-5e4f-4321-8fed-cba987654321",
    "booking_id": "5d6e7f80-9a1b-4c2d-8e3f-4a5b6c7d8e9f",
    "starts_at": "2030-01-08T13:00:00+00:00",
}
DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"


def instant(value: str):
    return match.regex(value, regex=DATETIME)


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_files():
    for name in ("waitlist-catalog.json", "waitlist-booking.json"):
        (PACTS / name).unlink(missing_ok=True)


@pytest.fixture
def catalog_pact():
    pact = Pact("waitlist", "catalog").with_specification("V4")
    yield pact
    pact.write_file(PACTS)


@pytest.fixture
def booking_pact():
    pact = Pact("waitlist", "booking").with_specification("V4")
    yield pact
    pact.write_file(PACTS)


def booking_client(server) -> BookingClient:
    headers = {"Authorization": "Bearer service-token"}
    return BookingClient(httpx.AsyncClient(base_url=str(server.url), headers=headers))


def service_request(pact, description: str, state: str, path: str):
    return (
        pact.upon_receiving(description)
        .given(state, SLOT)
        .with_request("POST", path)
        .with_header("Authorization", match.regex("Bearer service-token", regex=r"^Bearer \S+$"))
    )


def hold_request(pact, description: str, state: str):
    return service_request(pact, description, state, "/holds").with_body(
        {
            "business_id": match.uuid(SLOT["business_id"]),
            "professional_id": match.uuid(SLOT["professional_id"]),
            "service_id": match.uuid(SLOT["service_id"]),
            "starts_at": instant(SLOT["starts_at"]),
            "customer_name": match.str("Ana Souza"),
            "customer_email": match.str("ana@example.com"),
            "hold_minutes": match.int(15),
        },
        content_type="application/json",
    )


async def hold(server):
    entry = Entry(
        business_id=UUID(SLOT["business_id"]),
        professional_id=UUID(SLOT["professional_id"]),
        service_id=UUID(SLOT["service_id"]),
        customer_name="Ana Souza",
        customer_email="ana@example.com",
    )
    return await booking_client(server).hold(entry, datetime(2030, 1, 8, 13, tzinfo=UTC), 15)


async def test_reads_names_and_prices_of_a_business(catalog_pact):
    (
        catalog_pact.upon_receiving("a request for a business with its names and prices")
        .given("a business with a professional and a service exists", SLOT)
        .with_request("GET", f"/businesses/{SLOT['business_id']}")
        .will_respond_with(200)
        .with_body(
            {
                "id": match.uuid(SLOT["business_id"]),
                "name": match.str("Clínica Sorriso Pleno"),
                "address": match.str("Av. Tiradentes, 890"),
                "timezone": match.str("America/Sao_Paulo"),
                "professionals": match.each_like(
                    {"id": match.uuid(SLOT["professional_id"]), "name": match.str("Dra. Ana")}
                ),
                "services": match.each_like(
                    {
                        "id": match.uuid(SLOT["service_id"]),
                        "name": match.str("Avaliação"),
                        "price_cents": match.int(0),
                    }
                ),
            },
            content_type="application/json",
        )
    )

    with catalog_pact.serve() as server:
        business = await CatalogClient(str(server.url)).get_business(UUID(SLOT["business_id"]))

    assert business is not None
    assert business.services[0].name == "Avaliação"


async def test_holds_a_free_slot(booking_pact):
    (
        hold_request(booking_pact, "a request to hold a free slot", "the slot is free")
        .will_respond_with(201)
        .with_body(
            {
                "id": match.uuid(SLOT["booking_id"]),
                "starts_at": instant(SLOT["starts_at"]),
                "ends_at": instant("2030-01-08T13:30:00+00:00"),
                "hold_expires_at": instant("2030-01-08T12:15:00+00:00"),
            },
            content_type="application/json",
        )
    )

    with booking_pact.serve() as server:
        held = await hold(server)

    assert held is not None
    assert held.id == UUID(SLOT["booking_id"])


async def test_taken_slot_is_not_held(booking_pact):
    hold_request(
        booking_pact, "a request to hold a taken slot", "a confirmed booking exists"
    ).will_respond_with(409)

    with booking_pact.serve() as server:
        assert await hold(server) is None


@pytest.mark.parametrize(
    ("action", "state", "status", "settled"),
    [
        ("confirm", "a hold exists", 200, True),
        ("confirm", "an expired hold exists", 409, False),
        ("release", "a hold exists", 200, True),
        ("release", "a confirmed booking exists", 409, False),
    ],
)
async def test_settles_a_hold(booking_pact, action, state, status, settled):
    path = f"/bookings/{SLOT['booking_id']}/{action}"
    service_request(
        booking_pact, f"a request to {action} when {state}", state, path
    ).will_respond_with(status)

    with booking_pact.serve() as server:
        client = booking_client(server)
        assert await getattr(client, action)(UUID(SLOT["booking_id"])) is settled


def test_reads_the_freed_slot_of_a_cancellation(booking_pact):
    booking_pact.upon_receiving("a booking.cancelled event", "Async").with_body(
        {
            "event_id": match.uuid("0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9"),
            "type": "booking.cancelled",
            "data": {
                "booking_id": match.uuid(SLOT["booking_id"]),
                "professional_id": match.uuid(SLOT["professional_id"]),
                "starts_at": instant(SLOT["starts_at"]),
            },
        },
        "application/json",
    )

    booking_pact.verify(lambda body, _: BookingCancelled.model_validate_json(body), "Async")
