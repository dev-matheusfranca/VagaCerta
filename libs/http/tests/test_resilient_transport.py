import asyncio

import httpx
import pytest

from vagacerta_http import CircuitOpenError, ResilientTransport


def client(*statuses: int | Exception, **options) -> tuple[httpx.AsyncClient, list[str]]:
    """Destino de mentira que responde na ordem dada e repete a última resposta."""
    calls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        status = statuses[min(len(calls), len(statuses)) - 1]
        if isinstance(status, Exception):
            raise status
        return httpx.Response(status)

    transport = ResilientTransport(httpx.MockTransport(handle), backoff=0, **options)
    return httpx.AsyncClient(base_url="http://catalog", transport=transport), calls


async def test_a_query_is_retried_until_it_works():
    http, calls = client(503, httpx.ConnectError("caiu"), 200)

    response = await http.get("/businesses")

    assert response.status_code == 200
    assert calls == ["GET", "GET", "GET"]


async def test_a_post_is_never_repeated():
    http, calls = client(503, 201)

    response = await http.post("/bookings")

    assert response.status_code == 503
    assert calls == ["POST"]


async def test_the_circuit_opens_after_repeated_failures_and_fails_fast():
    http, calls = client(httpx.ConnectError("caiu"), retries=0, failure_threshold=3)

    for _ in range(3):
        with pytest.raises(httpx.ConnectError):
            await http.get("/businesses")
    with pytest.raises(CircuitOpenError):
        await http.get("/businesses")

    assert len(calls) == 3


async def test_the_circuit_closes_when_the_destination_recovers():
    http, calls = client(503, 503, 200, retries=0, failure_threshold=2, reset_after=0.05)

    for _ in range(2):
        await http.get("/businesses")
    await asyncio.sleep(0.06)

    assert (await http.get("/businesses")).status_code == 200
    assert (await http.get("/businesses")).status_code == 200
    assert len(calls) == 4
