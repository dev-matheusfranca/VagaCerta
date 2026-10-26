from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pact import Pact, match

from analytics.catalog_client import CatalogClient
from analytics.events import event_adapter

PACTS = Path(__file__).parents[3] / "pacts"
DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
SLOT = {
    "business_id": match.uuid("711fa378-fb4e-429e-bd5e-6a3f856ab875"),
    "starts_at": match.regex("2030-01-08T13:00:00+00:00", regex=DATETIME),
    "timezone": match.str("America/Sao_Paulo"),
    "price_cents": match.int(4500),
}
BOOKING_ID = match.uuid("5d6e7f80-9a1b-4c2d-8e3f-4a5b6c7d8e9f")
BUSINESS = {
    "business_id": "711fa378-fb4e-429e-bd5e-6a3f856ab875",
    "professional_id": "3a4b5c6d-7e8f-4901-a2b3-c4d5e6f7a8b9",
    "service_id": "9c8b7a6d-5e4f-4321-8fed-cba987654321",
}


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_files():
    for name in ("analytics-booking.json", "analytics-waitlist.json", "analytics-catalog.json"):
        (PACTS / name).unlink(missing_ok=True)


def expect(provider: str, events: dict[str, dict]) -> None:
    pact = Pact("analytics", provider).with_specification("V4")
    for type, data in events.items():
        pact.upon_receiving(f"a {type} event", "Async").with_body(
            {
                "event_id": match.uuid("0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9"),
                "type": type,
                "data": data,
            },
            "application/json",
        )
    pact.verify(lambda body, _: event_adapter.validate_json(body), "Async")
    pact.write_file(PACTS)


def test_reads_booking_events():
    expect(
        "booking",
        {
            "booking.created": {
                **SLOT,
                "booking_id": BOOKING_ID,
                "ends_at": match.regex("2030-01-08T13:30:00+00:00", regex=DATETIME),
            },
            "booking.cancelled": {"booking_id": BOOKING_ID},
            "booking.completed": {"booking_id": BOOKING_ID},
            "booking.no_show": {"booking_id": BOOKING_ID},
        },
    )


def test_reads_waitlist_offers():
    expect(
        "waitlist",
        {
            "waitlist.offer_created": SLOT,
            "waitlist.offer_claimed": SLOT,
            "waitlist.offer_expired": SLOT,
        },
    )


async def test_reads_the_working_hours_of_a_business():
    pact = Pact("analytics", "catalog").with_specification("V4")
    (
        pact.upon_receiving("a request for the working hours of a business")
        .given("a business with a professional and a service exists", BUSINESS)
        .with_request("GET", f"/businesses/{BUSINESS['business_id']}")
        .will_respond_with(200)
        .with_body(
            {
                "professionals": match.each_like(
                    {
                        "working_hours": match.each_like(
                            {
                                "weekday": match.int(1),
                                "start": match.regex("09:00:00", regex=r"^\d{2}:\d{2}:\d{2}$"),
                                "end": match.regex("12:00:00", regex=r"^\d{2}:\d{2}:\d{2}$"),
                            }
                        )
                    }
                )
            },
            content_type="application/json",
        )
    )

    with pact.serve() as server:
        catalog = CatalogClient(httpx.AsyncClient(base_url=str(server.url)))
        schedule = await catalog.schedule(UUID(BUSINESS["business_id"]))
    pact.write_file(PACTS)

    assert schedule is not None
    assert schedule.professionals[0].working_hours[0].weekday == 1
