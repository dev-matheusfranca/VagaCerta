from pathlib import Path

import httpx
import pytest
from mcp import Client
from pact import Pact, match

from mcp_server.server import create_server

PACTS = Path(__file__).parents[3] / "pacts"
SLOT = {
    "business_id": "6384a99a-146a-4b11-8e9b-db99b79e8fd2",
    "professional_id": "8f4c2a1e-5b6d-4e7f-9a0b-1c2d3e4f5a6b",
    "service_id": "2b3c4d5e-6f70-4812-93a4-b5c6d7e8f901",
    "booking_id": "5d6e7f80-9a1b-4c2d-8e3f-4a5b6c7d8e9f",
    "starts_at": "2030-01-08T13:00:00+00:00",
}
DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
BUSINESS_STATE = "a business with a professional and a service exists"
CHOICE = {key: SLOT[key] for key in ("business_id", "professional_id", "service_id")}
CUSTOMER = {"customer_name": "Ana Souza", "customer_email": "ana@example.com"}


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_files():
    for provider in ("catalog", "booking", "waitlist"):
        (PACTS / f"mcp-server-{provider}.json").unlink(missing_ok=True)


def pact_with(provider: str):
    pact = Pact("mcp-server", provider).with_specification("V4")
    yield pact
    pact.write_file(PACTS)


@pytest.fixture
def catalog_pact():
    yield from pact_with("catalog")


@pytest.fixture
def booking_pact():
    yield from pact_with("booking")


@pytest.fixture
def waitlist_pact():
    yield from pact_with("waitlist")


def tools(catalog="http://unused", booking="http://unused", waitlist="http://unused") -> Client:
    server = create_server(
        httpx.AsyncClient(base_url=catalog),
        httpx.AsyncClient(base_url=booking),
        httpx.AsyncClient(base_url=waitlist),
        "http://web",
    )
    return Client(server)


async def test_lists_and_describes_businesses(catalog_pact):
    (
        catalog_pact.upon_receiving("a request for the list of businesses")
        .given(BUSINESS_STATE, SLOT)
        .with_request("GET", "/businesses")
        .will_respond_with(200)
        .with_body(
            match.each_like(
                {
                    "id": match.uuid(SLOT["business_id"]),
                    "name": match.str("Barbearia Navalha de Ouro"),
                    "category": match.str("barbearia"),
                    "address": match.str("Av. Brasil, 1200"),
                }
            ),
            content_type="application/json",
        )
    )
    (
        catalog_pact.upon_receiving("a request for a business with its professionals and services")
        .given(BUSINESS_STATE, SLOT)
        .with_request("GET", f"/businesses/{SLOT['business_id']}")
        .will_respond_with(200)
        .with_body(
            {
                "id": match.uuid(SLOT["business_id"]),
                "name": match.str("Barbearia Navalha de Ouro"),
                "address": match.str("Av. Brasil, 1200"),
                "professionals": match.each_like(
                    {
                        "id": match.uuid(SLOT["professional_id"]),
                        "name": match.str("Rafael Costa"),
                        "specialty": match.str("Barbeiro"),
                    }
                ),
                "services": match.each_like(
                    {
                        "id": match.uuid(SLOT["service_id"]),
                        "name": match.str("Corte masculino"),
                        "duration_minutes": match.int(30),
                        "price_cents": match.int(4500),
                    }
                ),
            },
            content_type="application/json",
        )
    )

    with catalog_pact.serve() as catalog:
        async with tools(catalog=str(catalog.url)) as client:
            listed = await client.call_tool("list_businesses", {})
            described = await client.call_tool("get_business", {"business_id": SLOT["business_id"]})

    assert listed.structured_content["result"][0]["category"] == "barbearia"
    assert described.structured_content["services"][0]["price"] == "R$ 45,00"


async def test_finds_a_slot_and_books_it(catalog_pact, booking_pact):
    (
        catalog_pact.upon_receiving("a request for the timezone of a business")
        .given(BUSINESS_STATE, SLOT)
        .with_request("GET", f"/businesses/{SLOT['business_id']}")
        .will_respond_with(200)
        .with_body({"timezone": match.str("America/Sao_Paulo")}, content_type="application/json")
    )
    (
        booking_pact.upon_receiving("a request for the free slots of a day")
        .given("the slot is free", SLOT)
        .with_request("GET", "/availability")
        .with_query_parameters({**CHOICE, "date": "2030-01-08"})
        .will_respond_with(200)
        .with_body(
            {"slots": match.each_like(match.regex(SLOT["starts_at"], regex=DATETIME))},
            content_type="application/json",
        )
    )
    (
        booking_pact.upon_receiving("a request to book a free slot")
        .given("the slot is free", SLOT)
        .with_request("POST", "/bookings")
        .with_body(
            {**CHOICE, "starts_at": "2030-01-08T10:00:00-03:00", **CUSTOMER},
            content_type="application/json",
        )
        .will_respond_with(201)
        .with_body(
            {"id": match.uuid(SLOT["booking_id"]), "status": match.str("confirmed")},
            content_type="application/json",
        )
    )

    with catalog_pact.serve() as catalog, booking_pact.serve() as booking:
        async with tools(catalog=str(catalog.url), booking=str(booking.url)) as client:
            found = await client.call_tool("find_slots", {**CHOICE, "day": "2030-01-08"})
            slot = found.structured_content["slots"][0]
            booked = await client.call_tool(
                "book_appointment", {**CHOICE, "starts_at": slot["starts_at"], **CUSTOMER}
            )

    assert slot["time"] == "10:00"
    assert booked.structured_content["link"] == f"http://web/agendamentos/{SLOT['booking_id']}"


async def test_cancels_a_booking(booking_pact):
    (
        booking_pact.upon_receiving("a request to cancel a confirmed booking")
        .given("a confirmed booking exists", SLOT)
        .with_request("POST", f"/bookings/{SLOT['booking_id']}/cancel")
        .will_respond_with(200)
        .with_body(
            {"id": match.uuid(SLOT["booking_id"]), "status": match.str("cancelled")},
            content_type="application/json",
        )
    )

    with booking_pact.serve() as booking:
        async with tools(booking=str(booking.url)) as client:
            cancelled = await client.call_tool("cancel_booking", {"booking_id": SLOT["booking_id"]})

    assert cancelled.structured_content["status"] == "cancelled"


async def test_joins_the_waitlist(waitlist_pact):
    (
        waitlist_pact.upon_receiving("a request to join the waitlist of a day")
        .given(BUSINESS_STATE, SLOT)
        .with_request("POST", "/entries")
        .with_body({**CHOICE, "day": "2030-01-08", **CUSTOMER}, content_type="application/json")
        .will_respond_with(201)
        .with_body(
            {"id": match.uuid("1a2b3c4d-5e6f-4a1b-8c2d-3e4f5a6b7c8d"), "position": match.int(1)},
            content_type="application/json",
        )
    )

    with waitlist_pact.serve() as waitlist:
        async with tools(waitlist=str(waitlist.url)) as client:
            joined = await client.call_tool(
                "join_waitlist", {**CHOICE, "day": "2030-01-08", **CUSTOMER}
            )

    assert joined.structured_content["position"] == 1
