from pathlib import Path

import pytest
from pact import Pact, match

from notification.events import event_adapter

PACTS = Path(__file__).parents[3] / "pacts"
DATETIME = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
BOOKING = {
    "booking_id": match.uuid("5d6e7f80-9a1b-4c2d-8e3f-4a5b6c7d8e9f"),
    "starts_at": match.regex("2030-01-08T13:00:00+00:00", regex=DATETIME),
    "ends_at": match.regex("2030-01-08T13:30:00+00:00", regex=DATETIME),
    "customer_name": match.str("Ana Souza"),
    "customer_email": match.str("ana@example.com"),
    "business_name": match.str("Barbearia Navalha de Ouro"),
    "business_address": match.str("Av. Brasil, 1200"),
    "timezone": match.str("America/Sao_Paulo"),
    "professional_name": match.str("Rafael Costa"),
    "service_name": match.str("Corte masculino"),
    "price_cents": match.int(4500),
}


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_files():
    for name in ("notification-booking.json", "notification-waitlist.json"):
        (PACTS / name).unlink(missing_ok=True)


def expect(provider: str, events: dict[str, dict]) -> None:
    pact = Pact("notification", provider).with_specification("V4")
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
            "booking.created": BOOKING,
            "booking.cancelled": {"booking_id": BOOKING["booking_id"]},
        },
    )


def test_reads_waitlist_offers():
    offer = {
        **BOOKING,
        "offer_id": match.uuid("6e7f8091-a2b3-4c4d-9e5f-60718293a4b5"),
        "expires_at": match.regex("2030-01-07T13:15:00+00:00", regex=DATETIME),
    }
    expect("waitlist", {"waitlist.offer_created": offer})
