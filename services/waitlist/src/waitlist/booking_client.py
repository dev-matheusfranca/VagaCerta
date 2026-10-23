import time
from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID

import httpx
from pydantic import AwareDatetime, BaseModel

from waitlist.config import BOOKING_URL, CLIENT_ID, CLIENT_SECRET, KEYCLOAK_TOKEN_URL
from waitlist.models import Entry


class Hold(BaseModel):
    id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    hold_expires_at: AwareDatetime


class ClientCredentials(httpx.Auth):
    """Token de serviço do Keycloak (client credentials), reaproveitado até perto de expirar."""

    def __init__(self, token_url: str, client_id: str, client_secret: str) -> None:
        self._token_url = token_url
        self._form = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        self._token = ""
        self._expires_at = 0.0

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        if time.monotonic() >= self._expires_at:
            response = yield httpx.Request("POST", self._token_url, data=self._form)
            await response.aread()
            response.raise_for_status()
            token = response.json()
            self._token = token["access_token"]
            self._expires_at = time.monotonic() + token["expires_in"] - 30
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


class BookingClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

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


def booking_client() -> BookingClient:
    auth = ClientCredentials(KEYCLOAK_TOKEN_URL, CLIENT_ID, CLIENT_SECRET)
    return BookingClient(httpx.AsyncClient(base_url=BOOKING_URL, timeout=5, auth=auth))
