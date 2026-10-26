import json
from pathlib import Path
from uuid import UUID

import pytest
from pact import Pact, match

PACTS = Path(__file__).parents[3] / "pacts"
DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_files():
    for name in ("webhooks-booking.json", "webhooks-waitlist.json"):
        (PACTS / name).unlink(missing_ok=True)


def routable(body: str | bytes | None, metadata: dict) -> None:
    """O que os webhooks precisam para achar as assinaturas e repassar o evento."""
    event = json.loads(body or "")
    assert {"event_id", "type", "occurred_at"} <= event.keys()
    UUID(event["data"]["business_id"])


def expect(provider: str, *types: str) -> None:
    pact = Pact("webhooks", provider).with_specification("V4")
    for type in types:
        pact.upon_receiving(f"a {type} event", "Async").with_body(
            {
                "event_id": match.uuid("0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9"),
                "type": type,
                "occurred_at": match.regex("2030-01-07T13:00:00+00:00", regex=DATETIME),
                "data": {"business_id": match.uuid("711fa378-fb4e-429e-bd5e-6a3f856ab875")},
            },
            "application/json",
        )
    pact.verify(routable, "Async")
    pact.write_file(PACTS)


def test_routes_every_booking_event():
    expect(
        "booking", "booking.created", "booking.cancelled", "booking.completed", "booking.no_show"
    )


def test_routes_every_waitlist_event():
    expect("waitlist", "waitlist.offer_created", "waitlist.offer_claimed", "waitlist.offer_expired")
