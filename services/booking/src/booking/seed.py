"""Lota o próximo dia útil da Dra. Fernanda Lima, para demonstrar a lista de espera e o painel."""

import asyncio
from datetime import UTC, datetime, timedelta
from itertools import cycle
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from booking.catalog_client import CatalogClient
from booking.domain import available_slots
from booking.events import booking_created
from booking.main import CATALOG_URL, DATABASE_URL
from booking.models import Booking

CLINIC_ID = UUID("711fa378-fb4e-429e-bd5e-6a3f856ab875")
PATIENTS = (
    "Ana Souza", "Bruno Lima", "Carla Mendes", "Daniel Rocha",
    "Elisa Prado", "Felipe Nunes", "Gabriela Reis", "Henrique Alves",
    "Isabela Torres", "João Pedro Silva", "Karina Duarte", "Leonardo Castro",
    "Marina Lopes", "Natália Freitas", "Otávio Ramos", "Patrícia Gomes",
)  # fmt: skip


async def main() -> None:
    catalog = CatalogClient(httpx.AsyncClient(base_url=CATALOG_URL, timeout=5))
    clinic = await catalog.get_business(CLINIC_ID)
    assert clinic, "rode o seed do catálogo antes"
    dentist = next(p for p in clinic.professionals if p.name == "Dra. Fernanda Lima")
    # Avaliação (gratuita) e Manutenção de aparelho (paga), ambas de 30 minutos, alternadas.
    services = [s for s in clinic.services if s.duration_minutes == 30]
    tz, duration = ZoneInfo(clinic.timezone), timedelta(minutes=30)
    day = datetime.now(tz).date() + timedelta(days=1)
    while not dentist.periods_on(day):
        day += timedelta(days=1)
    slots = available_slots(day, tz, dentist.periods_on(day), duration, [], datetime.now(UTC))

    engine = create_async_engine(DATABASE_URL)
    async with async_sessionmaker(engine)() as session:
        if await session.scalar(select(Booking.id).limit(1)) is None:
            visits = zip(slots, PATIENTS, cycle(services), strict=False)
            for number, (slot, name, service) in enumerate(visits, 1):
                booking = Booking(
                    id=uuid4(),
                    business_id=clinic.id,
                    professional_id=dentist.id,
                    service_id=service.id,
                    starts_at=slot,
                    ends_at=slot + duration,
                    customer_name=name,
                    customer_email=f"paciente{number}@example.com",
                )
                # Pelo outbox, como um agendamento real: os outros serviços também enxergam a demo.
                session.add_all([booking, booking_created(booking, clinic, dentist, service)])
            await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
