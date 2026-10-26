from uuid import UUID

import httpx
from pydantic import BaseModel

from vagacerta_http import ResilientTransport


class Professional(BaseModel):
    id: UUID
    name: str


class Service(BaseModel):
    id: UUID
    name: str
    price_cents: int


class Business(BaseModel):
    id: UUID
    name: str
    address: str
    timezone: str
    professionals: list[Professional]
    services: list[Service]


class CatalogClient:
    def __init__(self, base_url: str) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=2, transport=ResilientTransport())

    async def get_business(self, business_id: UUID) -> Business | None:
        response = await self._http.get(f"/businesses/{business_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return Business.model_validate_json(response.content)
