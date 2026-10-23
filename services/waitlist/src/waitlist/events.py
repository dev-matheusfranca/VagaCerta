from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel

from waitlist.models import Offer, OutboxEvent

BOOKING_TOPIC = "booking.events"
WAITLIST_TOPIC = "waitlist.events"


class FreedSlot(BaseModel):
    booking_id: UUID
    professional_id: UUID
    starts_at: AwareDatetime


class BookingCancelled(BaseModel):
    event_id: UUID
    type: Literal["booking.cancelled"]
    data: FreedSlot


def offer_created(offer: Offer) -> OutboxEvent:
    return OutboxEvent(
        topic=WAITLIST_TOPIC,
        key=str(offer.id),
        payload={
            "event_id": str(uuid4()),
            "type": "waitlist.offer_created",
            "occurred_at": datetime.now(UTC).isoformat(),
            "data": {
                "offer_id": str(offer.id),
                "booking_id": str(offer.booking_id),
                "starts_at": offer.starts_at.isoformat(),
                "ends_at": offer.ends_at.isoformat(),
                "expires_at": offer.expires_at.isoformat(),
                "customer_name": offer.entry.customer_name,
                "customer_email": offer.entry.customer_email,
                **offer.entry.details,
            },
        },
    )
