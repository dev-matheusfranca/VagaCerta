from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from notification.events import BookingDetails

STARTS_AT = datetime(2030, 1, 9, 12, tzinfo=UTC)


@pytest.fixture
def details():
    return BookingDetails(
        booking_id=uuid4(),
        starts_at=STARTS_AT,
        ends_at=STARTS_AT + timedelta(minutes=30),
        customer_name="Maria Silva",
        customer_email="maria@example.com",
        business_name="Barbearia Teste",
        business_address="Rua A, 1",
        timezone="America/Sao_Paulo",
        professional_name="Rafael Costa",
        service_name="Corte",
        price_cents=4500,
    )
