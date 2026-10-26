from uuid import uuid4

import httpx
import pytest

from booking.catalog_client import CatalogClient


def business(business_id) -> dict:
    return {
        "id": str(business_id),
        "name": "Barbearia",
        "address": "Rua A, 1",
        "timezone": "America/Sao_Paulo",
        "professionals": [],
        "services": [],
    }


async def test_business_is_cached_between_calls():
    business_id = uuid4()
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(200, json=business(business_id))

    http = httpx.AsyncClient(base_url="http://catalog", transport=httpx.MockTransport(handle))
    catalog = CatalogClient(http)

    first = await catalog.get_business(business_id)
    second = await catalog.get_business(business_id)

    assert first == second
    assert requests == [f"/businesses/{business_id}"]


async def test_an_expired_entry_is_used_while_the_catalog_is_down():
    business_id = uuid4()
    catalog_up = True

    def handle(request: httpx.Request) -> httpx.Response:
        if not catalog_up:
            raise httpx.ConnectError("catálogo fora do ar")
        return httpx.Response(200, json=business(business_id))

    catalog = CatalogClient(
        httpx.AsyncClient(base_url="http://catalog", transport=httpx.MockTransport(handle))
    )
    catalog.CACHE_SECONDS = 0
    cached = await catalog.get_business(business_id)
    catalog_up = False

    assert await catalog.get_business(business_id) == cached
    with pytest.raises(httpx.ConnectError):
        await catalog.get_business(uuid4())
