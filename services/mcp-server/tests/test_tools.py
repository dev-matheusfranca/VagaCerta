from uuid import uuid4

import httpx
from mcp import Client

from mcp_server.server import create_server

BUSINESS, PROFESSIONAL, SERVICE = uuid4(), uuid4(), uuid4()


def fake(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="http://fake", transport=httpx.MockTransport(handler))


def catalog(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"timezone": "America/Sao_Paulo"})


def booking(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/availability":
        return httpx.Response(200, json={"slots": ["2030-01-08T13:00:00Z", "2030-01-08T17:30:00Z"]})
    return httpx.Response(
        409, json={"detail": "Esse horário acabou de ser reservado por outra pessoa"}
    )


def server():
    return create_server(fake(catalog), fake(booking), fake(booking), "http://web")


async def test_slots_are_in_the_business_timezone():
    async with Client(server()) as client:
        result = await client.call_tool(
            "find_slots",
            {
                "business_id": str(BUSINESS),
                "professional_id": str(PROFESSIONAL),
                "service_id": str(SERVICE),
                "day": "2030-01-08",
            },
        )

    assert result.structured_content["weekday"] == "terça-feira"
    assert [s["time"] for s in result.structured_content["slots"]] == ["10:00", "14:30"]
    assert result.structured_content["slots"][0]["starts_at"] == "2030-01-08T10:00:00-03:00"


async def test_a_taken_slot_is_explained_to_the_model():
    async with Client(server()) as client:
        result = await client.call_tool(
            "book_appointment",
            {
                "business_id": str(BUSINESS),
                "professional_id": str(PROFESSIONAL),
                "service_id": str(SERVICE),
                "starts_at": "2030-01-08T10:00:00-03:00",
                "customer_name": "Ana Souza",
                "customer_email": "ana@example.com",
            },
        )

    assert result.is_error
    assert "acabou de ser reservado" in result.content[0].text
