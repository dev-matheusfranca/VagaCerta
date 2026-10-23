"""Lota o próximo dia útil da Dra. Fernanda Lima, para demonstrar a lista de espera e o painel."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from booking.catalog_client import CatalogClient
from booking.domain import available_slots
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
    clinic = await CatalogClient(CATALOG_URL).get_business(CLINIC_ID)
    assert clinic, "rode o seed do catálogo antes"
    dentist = next(p for p in clinic.professionals if p.name == "Dra. Fernanda Lima")
    evaluation = next(s for s in clinic.services if s.name == "Avaliação")
    tz, duration = ZoneInfo(clinic.timezone), timedelta(minutes=evaluation.duration_minutes)
    day = datetime.now(tz).date() + timedelta(days=1)
    while not dentist.periods_on(day):
        day += timedelta(days=1)
    slots = available_slots(day, tz, dentist.periods_on(day), duration, [], datetime.now(UTC))

    engine = create_async_engine(DATABASE_URL)
    async with async_sessionmaker(engine)() as session:
        if await session.scalar(select(Booking.id).limit(1)) is None:
            session.add_all(
                Booking(
                    business_id=clinic.id,
                    professional_id=dentist.id,
                    service_id=evaluation.id,
                    starts_at=slot,
                    ends_at=slot + duration,
                    customer_name=name,
                    customer_email=f"paciente{number}@example.com",
                )
                for number, (slot, name) in enumerate(zip(slots, PATIENTS, strict=False), 1)
            )
            await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
