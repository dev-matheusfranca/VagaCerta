from pathlib import Path

import pytest
from pact import Pact, match

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


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_files():
    for name in ("analytics-booking.json", "analytics-waitlist.json"):
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
            "booking.created": {**SLOT, "booking_id": BOOKING_ID},
            "booking.cancelled": {"booking_id": BOOKING_ID},
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
