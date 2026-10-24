import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pact import Verifier

from waitlist.events import offer_event
from waitlist.models import Entry, Offer

PACTS = Path(__file__).parents[3] / "pacts"


def test_waitlist_honours_its_consumer_contracts():
    entry = Entry(
        business_id=uuid4(),
        professional_id=uuid4(),
        service_id=uuid4(),
        customer_name="Ana Souza",
        customer_email="ana@example.com",
        details={
            "business_name": "Clínica Sorriso Pleno",
            "business_address": "Av. Tiradentes, 890",
            "timezone": "America/Sao_Paulo",
            "professional_name": "Dra. Fernanda Lima",
            "service_name": "Avaliação",
            "price_cents": 12000,
        },
    )
    offer = Offer(
        id=uuid4(),
        entry=entry,
        booking_id=uuid4(),
        starts_at=datetime(2030, 1, 8, 13, tzinfo=UTC),
        ends_at=datetime(2030, 1, 8, 13, 30, tzinfo=UTC),
        expires_at=datetime(2030, 1, 7, 13, 15, tzinfo=UTC),
    )
    messages = {
        f"a {type} event": {
            "contents": json.dumps(offer_event(offer, type).payload).encode(),
            "content_type": "application/json",
        }
        for type in ("waitlist.offer_created", "waitlist.offer_claimed", "waitlist.offer_expired")
    }
    (
        Verifier("waitlist", host="127.0.0.1")
        .message_handler(messages)
        .add_source(PACTS / "notification-waitlist.json")
        .add_source(PACTS / "analytics-waitlist.json")
        .verify()
    )
