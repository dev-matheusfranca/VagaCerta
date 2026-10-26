"""Dados de demonstração da clínica: o próximo dia útil da Dra. Fernanda lotado (lista de espera)
e 30 dias de histórico com faltas (painel).
"""

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from itertools import cycle
from random import Random
from unicodedata import normalize
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from booking.catalog_client import Business, CatalogClient, Service
from booking.domain import available_slots
from booking.events import booking_created, booking_outcome
from booking.main import CATALOG_URL, DATABASE_URL
from booking.models import Booking

CLINIC_ID = UUID("711fa378-fb4e-429e-bd5e-6a3f856ab875")
PATIENTS = (
    "Ana Souza", "Bruno Lima", "Carla Mendes", "Daniel Rocha",
    "Elisa Prado", "Felipe Nunes", "Gabriela Reis", "Henrique Alves",
    "Isabela Torres", "João Pedro Silva", "Karina Duarte", "Leonardo Castro",
    "Marina Lopes", "Natália Freitas", "Otávio Ramos", "Patrícia Gomes",
)  # fmt: skip
# Chance de um horário estar ocupado: cheio cedo e no fim da tarde, vazio perto do almoço.
DEMAND = {8: 0.9, 9: 0.75, 10: 0.6, 11: 0.45, 13: 0.4, 14: 0.5, 15: 0.65, 16: 0.85, 17: 0.9}
BUSY_DAYS = {0: 1.0, 4: 0.95}  # segunda e sexta; os outros dias valem 0,75
NO_SHOW_RATE = 0.12


def email_name(name: str) -> str:
    """ "João Pedro Silva" vira "joao.pedro.silva"."""
    return normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace(" ", ".")


def history(clinic: Business, services: list[Service], today: date) -> list[object]:
    """Atendimentos dos últimos 30 dias, já com comparecimento ou falta, sempre os mesmos."""
    rng = Random(42)
    tz, duration = ZoneInfo(clinic.timezone), timedelta(minutes=30)
    rows: list[object] = []
    for offset in range(30, 0, -1):
        day = today - timedelta(days=offset)
        for professional in clinic.professionals:
            day_start = datetime.combine(day, time(), tz)
            for slot in available_slots(
                day, tz, professional.periods_on(day), duration, [], day_start
            ):
                local = slot.astimezone(tz)
                chance = DEMAND.get(local.hour, 0.3) * BUSY_DAYS.get(day.weekday(), 0.75)
                if rng.random() > chance:
                    continue
                service, name = rng.choice(services), rng.choice(PATIENTS)
                visit = Booking(
                    id=uuid4(),
                    business_id=clinic.id,
                    professional_id=professional.id,
                    service_id=service.id,
                    starts_at=slot,
                    ends_at=slot + duration,
                    customer_name=name,
                    customer_email=f"{email_name(name)}@example.com",
                    status="no_show" if rng.random() < NO_SHOW_RATE else "completed",
                )
                rows += [
                    visit,
                    booking_created(visit, clinic, professional, service),
                    booking_outcome(visit),
                ]
    return rows


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
            session.add_all(history(clinic, services, datetime.now(tz).date()))
            await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
