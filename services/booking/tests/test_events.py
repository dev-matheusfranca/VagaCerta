from datetime import UTC, datetime, timedelta
from uuid import uuid4

from opentelemetry.sdk.trace import TracerProvider

from booking import events
from booking.models import Booking


def test_outbox_event_carries_the_trace_of_the_request():
    starts_at = datetime.now(UTC) + timedelta(days=1)
    booking = Booking(
        id=uuid4(),
        business_id=uuid4(),
        professional_id=uuid4(),
        service_id=uuid4(),
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        customer_name="Maria Silva",
        customer_email="maria@example.com",
    )

    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("POST /bookings/{id}/cancel") as span:
        event = events.booking_cancelled(booking)

    trace_id = format(span.get_span_context().trace_id, "032x")
    assert trace_id in event.trace_context["traceparent"]
