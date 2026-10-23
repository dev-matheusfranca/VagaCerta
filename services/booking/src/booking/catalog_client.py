from datetime import date, time
from time import monotonic
from uuid import UUID

import httpx
from pydantic import BaseModel


class WorkingHours(BaseModel):
    weekday: int
    start: time
    end: time


class Professional(BaseModel):
    id: UUID
    name: str
    working_hours: list[WorkingHours]

    def periods_on(self, day: date) -> list[tuple[time, time]]:
        return [(h.start, h.end) for h in self.working_hours if h.weekday == day.weekday()]


class Service(BaseModel):
    id: UUID
    name: str
    duration_minutes: int
    price_cents: int


class Business(BaseModel):
    id: UUID
    name: str
    address: str
    timezone: str
    professionals: list[Professional]
    services: list[Service]


class CatalogClient:
    # O catálogo quase não muda e é lido em toda consulta de disponibilidade: um cache curto
    # tira a chamada HTTP do caminho quente. Mudanças de expediente valem em até CACHE_SECONDS.
    CACHE_SECONDS = 30

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http
        self._cache: dict[UUID, tuple[float, Business | None]] = {}

    async def get_business(self, business_id: UUID) -> Business | None:
        expires_at, business = self._cache.get(business_id, (0.0, None))
        if monotonic() < expires_at:
            return business
        response = await self._http.get(f"/businesses/{business_id}")
        if response.status_code == 404:
            business = None
        else:
            response.raise_for_status()
            business = Business.model_validate_json(response.content)
        self._cache[business_id] = (monotonic() + self.CACHE_SECONDS, business)
        return business
