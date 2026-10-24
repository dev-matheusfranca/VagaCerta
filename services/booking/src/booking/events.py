from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from opentelemetry import propagate

from booking.catalog_client import Business, Professional, Service
from booking.models import Booking, OutboxEvent

TOPIC = "booking.events"


def _event(booking: Booking, type: str, data: dict[str, Any]) -> OutboxEvent:
    # Guarda o trace da requisição para o relay continuá-lo ao publicar no Kafka.
    trace_context: dict[str, str] = {}
    propagate.inject(trace_context)
    return OutboxEvent(
        topic=TOPIC,
        key=str(booking.id),
        payload={
            "event_id": str(uuid4()),
            "type": type,
            "occurred_at": datetime.now(UTC).isoformat(),
            "data": {"booking_id": str(booking.id), **data},
        },
        trace_context=trace_context,
    )


def booking_created(
    booking: Booking, business: Business, professional: Professional, service: Service
) -> OutboxEvent:
    return _event(
        booking,
        "booking.created",
        {
            "starts_at": booking.starts_at.isoformat(),
            "ends_at": booking.ends_at.isoformat(),
            "customer_name": booking.customer_name,
            "customer_email": booking.customer_email,
            "business_name": business.name,
            "business_address": business.address,
            "timezone": business.timezone,
            "professional_name": professional.name,
            "service_name": service.name,
            "price_cents": service.price_cents,
        },
    )


def booking_cancelled(booking: Booking) -> OutboxEvent:
    return _event(
        booking,
        "booking.cancelled",
        {
            "business_id": str(booking.business_id),
            "professional_id": str(booking.professional_id),
            "starts_at": booking.starts_at.isoformat(),
            "ends_at": booking.ends_at.isoformat(),
        },
    )
