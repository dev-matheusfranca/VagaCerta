import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from booking.catalog_client import CatalogClient
from booking.main import create_app
from vagacerta_auth import TokenVerifier
from vagacerta_http import ResilientTransport

TZ = ZoneInfo("America/Sao_Paulo")
BUSINESS, PROFESSIONAL, SERVICE = uuid4(), uuid4(), uuid4()
SCHEDULE = {
    "business_id": str(BUSINESS),
    "professional_id": str(PROFESSIONAL),
    "service_id": str(SERVICE),
    "date": str(datetime.now(TZ).date() + timedelta(days=1)),
}


def wait_until_up(url: str) -> None:
    for _ in range(60):
        try:
            if httpx.get(url).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError(url)


@pytest.fixture(scope="module")
def toxiproxy():
    """Catálogo simulado pelo WireMock, que o Booking alcança pela rede através do Toxiproxy."""
    with (
        Network() as network,
        DockerContainer("wiremock/wiremock:3.13.2")
        .with_network(network)
        .with_network_aliases("catalog")
        .with_exposed_ports(8080) as wiremock,
        DockerContainer("ghcr.io/shopify/toxiproxy:2.13.0")
        .with_network(network)
        .with_exposed_ports(8474, 8666) as proxy,
    ):
        host = proxy.get_container_host_ip()
        wiremock_url = f"http://{host}:{wiremock.get_exposed_port(8080)}"
        api = f"http://{host}:{proxy.get_exposed_port(8474)}"
        wait_until_up(f"{wiremock_url}/__admin/health")
        wait_until_up(f"{api}/version")
        stub = {
            "request": {"method": "GET", "urlPath": f"/businesses/{BUSINESS}"},
            "response": {
                "status": 200,
                "jsonBody": {
                    "id": str(BUSINESS),
                    "name": "Barbearia Teste",
                    "address": "Rua A, 1",
                    "timezone": str(TZ),
                    "professionals": [
                        {
                            "id": str(PROFESSIONAL),
                            "name": "Rafael Costa",
                            "working_hours": [
                                {"weekday": d, "start": "09:00:00", "end": "12:00:00"}
                                for d in range(7)
                            ],
                        }
                    ],
                    "services": [
                        {
                            "id": str(SERVICE),
                            "name": "Corte",
                            "duration_minutes": 30,
                            "price_cents": 4500,
                        }
                    ],
                },
            },
        }
        httpx.post(f"{wiremock_url}/__admin/mappings", json=stub).raise_for_status()
        catalog = {"name": "catalog", "listen": "0.0.0.0:8666", "upstream": "catalog:8080"}
        httpx.post(f"{api}/proxies", json=catalog).raise_for_status()
        yield api, f"http://{host}:{proxy.get_exposed_port(8666)}"


@pytest.fixture
async def toxi(toxiproxy):
    api, _ = toxiproxy
    async with httpx.AsyncClient(base_url=api) as client:
        yield client
        await client.post("/proxies/catalog", json={"enabled": True})
        await client.delete("/proxies/catalog/toxics/slow")


@pytest.fixture
async def booking(database_url, toxiproxy):
    _, catalog_url = toxiproxy
    transport = ResilientTransport(backoff=0, failure_threshold=3, reset_after=1)
    catalog = CatalogClient(
        httpx.AsyncClient(base_url=catalog_url, timeout=0.5, transport=transport)
    )
    catalog.CACHE_SECONDS = 0
    app = create_app(
        database_url, catalog, TokenVerifier("http://keycloak.test", lambda _: "unused")
    )
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client


async def availability(client: AsyncClient) -> tuple[int, float]:
    started = time.monotonic()
    response = await client.get("/availability", params=SCHEDULE)
    return response.status_code, time.monotonic() - started


async def test_a_slow_catalog_opens_the_circuit_and_requests_fail_fast(booking, toxi):
    slow = {"name": "slow", "type": "latency", "attributes": {"latency": 2000}}
    (await toxi.post("/proxies/catalog/toxics", json=slow)).raise_for_status()

    first_failures = [await availability(booking) for _ in range(3)]
    status, elapsed = await availability(booking)

    assert [status for status, _ in first_failures] == [503, 503, 503]
    assert status == 503
    assert elapsed < 0.2

    (await toxi.delete("/proxies/catalog/toxics/slow")).raise_for_status()
    await asyncio.sleep(1)
    assert (await availability(booking))[0] == 200


async def test_cached_schedules_keep_availability_up_while_the_catalog_is_down(booking, toxi):
    assert (await availability(booking))[0] == 200

    (await toxi.post("/proxies/catalog", json={"enabled": False})).raise_for_status()

    assert (await availability(booking))[0] == 200
