from datetime import datetime
from uuid import UUID

import httpx
from pydantic import AwareDatetime, BaseModel

from waitlist.models import Entry


class Hold(BaseModel):
    id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    hold_expires_at: AwareDatetime


class BookingClient:
    def __init__(self, base_url: str) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=5)

    async def hold(self, entry: Entry, starts_at: datetime, minutes: int) -> Hold | None:
        """Reserva o horário para a pessoa da fila; None se ele não serve para ela."""
        response = await self._http.post(
            "/holds",
            json={
                "business_id": str(entry.business_id),
                "professional_id": str(entry.professional_id),
                "service_id": str(entry.service_id),
                "starts_at": starts_at.isoformat(),
                "customer_name": entry.customer_name,
                "customer_email": entry.customer_email,
                "hold_minutes": minutes,
            },
        )
        if response.status_code in (409, 422):
            return None
        response.raise_for_status()
        return Hold.model_validate_json(response.content)

    async def confirm(self, booking_id: UUID) -> bool:
        response = await self._http.post(f"/bookings/{booking_id}/confirm")
        if response.status_code == 409:
            return False
        response.raise_for_status()
        return True

    async def release(self, booking_id: UUID) -> bool:
        """Libera a reserva; False se ela já tinha sido confirmada."""
        response = await self._http.post(f"/bookings/{booking_id}/release")
        if response.status_code == 409:
            return False
        response.raise_for_status()
        return True
