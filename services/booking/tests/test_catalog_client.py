from uuid import uuid4

import httpx

from booking.catalog_client import CatalogClient


async def test_business_is_cached_between_calls():
    business_id = uuid4()
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "id": str(business_id),
                "name": "Barbearia",
                "address": "Rua A, 1",
                "timezone": "America/Sao_Paulo",
                "professionals": [],
                "services": [],
            },
        )

    http = httpx.AsyncClient(base_url="http://catalog", transport=httpx.MockTransport(handle))
    catalog = CatalogClient(http)

    first = await catalog.get_business(business_id)
    second = await catalog.get_business(business_id)

    assert first == second
    assert requests == [f"/businesses/{business_id}"]
