from datetime import date, datetime, time
from time import monotonic
from uuid import UUID

import httpx
from pydantic import BaseModel


class WorkingHours(BaseModel):
    weekday: int
    start: time
    end: time


class Professional(BaseModel):
    working_hours: list[WorkingHours]


class Schedule(BaseModel):
    professionals: list[Professional]

    def capacity_minutes(self, day: date) -> int:
        """Minutos de expediente somando todos os profissionais naquele dia."""
        return sum(
            int((datetime.combine(day, h.end) - datetime.combine(day, h.start)).total_seconds())
            // 60
            for p in self.professionals
            for h in p.working_hours
            if h.weekday == day.weekday()
        )


class CatalogClient:
    CACHE_SECONDS = 60

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http
        self._cache: dict[UUID, tuple[float, Schedule]] = {}

    async def schedule(self, business_id: UUID) -> Schedule | None:
        """Expediente do estabelecimento; None se o Catalog não responder e não houver cache."""
        expires_at, cached = self._cache.get(business_id, (0.0, None))
        if cached is not None and monotonic() < expires_at:
            return cached
        try:
            response = await self._http.get(f"/businesses/{business_id}")
            response.raise_for_status()
        except httpx.HTTPError:
            return cached
        schedule = Schedule.model_validate_json(response.content)
        self._cache[business_id] = (monotonic() + self.CACHE_SECONDS, schedule)
        return schedule
