from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pact import Pact, match

from booking.catalog_client import CatalogClient

PACTS = Path(__file__).parents[3] / "pacts"
BUSINESS = {
    "business_id": "6384a99a-146a-4b11-8e9b-db99b79e8fd2",
    "professional_id": "8f4c2a1e-5b6d-4e7f-9a0b-1c2d3e4f5a6b",
    "service_id": "2b3c4d5e-6f70-4812-93a4-b5c6d7e8f901",
}
TIME = r"^\d{2}:\d{2}:\d{2}$"


@pytest.fixture(scope="module", autouse=True)
def fresh_pact_file():
    (PACTS / "booking-catalog.json").unlink(missing_ok=True)


@pytest.fixture
def pact():
    pact = Pact("booking", "catalog").with_specification("V4")
    yield pact
    pact.write_file(PACTS)


async def test_reads_the_schedule_of_a_business(pact):
    (
        pact.upon_receiving("a request for a business with its schedule")
        .given("a business with a professional and a service exists", BUSINESS)
        .with_request("GET", f"/businesses/{BUSINESS['business_id']}")
        .will_respond_with(200)
        .with_body(
            {
                "id": match.uuid(BUSINESS["business_id"]),
                "name": match.str("Barbearia Navalha de Ouro"),
                "address": match.str("Av. Brasil, 1200"),
                "timezone": match.str("America/Sao_Paulo"),
                "professionals": match.each_like(
                    {
                        "id": match.uuid(BUSINESS["professional_id"]),
                        "name": match.str("Rafael Costa"),
                        "working_hours": match.each_like(
                            {
                                "weekday": match.int(1),
                                "start": match.regex("09:00:00", regex=TIME),
                                "end": match.regex("12:00:00", regex=TIME),
                            }
                        ),
                    }
                ),
                "services": match.each_like(
                    {
                        "id": match.uuid(BUSINESS["service_id"]),
                        "name": match.str("Corte masculino"),
                        "duration_minutes": match.int(30),
                        "price_cents": match.int(4500),
                    }
                ),
            },
            content_type="application/json",
        )
    )

    with pact.serve() as server:
        catalog = CatalogClient(httpx.AsyncClient(base_url=str(server.url)))
        business = await catalog.get_business(UUID(BUSINESS["business_id"]))

    assert business is not None
    assert business.professionals[0].working_hours[0].weekday == 1
    assert business.services[0].duration_minutes == 30


async def test_unknown_business_is_none(pact):
    unknown = "00000000-0000-4000-8000-000000000000"
    (
        pact.upon_receiving("a request for an unknown business")
        .given("no business exists")
        .with_request("GET", f"/businesses/{unknown}")
        .will_respond_with(404)
    )

    with pact.serve() as server:
        catalog = CatalogClient(httpx.AsyncClient(base_url=str(server.url)))
        assert await catalog.get_business(UUID(unknown)) is None
