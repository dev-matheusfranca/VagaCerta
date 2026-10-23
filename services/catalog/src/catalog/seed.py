import asyncio
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from catalog.main import DATABASE_URL
from catalog.models import Business, Professional, Service, WorkingHours

WEEKDAYS, MON_TO_SAT, TUE_TO_SAT = range(5), range(6), range(1, 6)


def hours(days: range, *periods: tuple[str, str]) -> list[WorkingHours]:
    return [
        WorkingHours(weekday=day, start=time.fromisoformat(start), end=time.fromisoformat(end))
        for day in days
        for start, end in periods
    ]


def businesses() -> list[Business]:
    return [
        Business(
            name="Barbearia Navalha de Ouro",
            category="barbearia",
            description="Cortes clássicos e modernos, barba na toalha quente e um bom café.",
            address="Av. Brasil, 1200 · Zona 01, Maringá/PR",
            timezone="America/Sao_Paulo",
            professionals=[
                Professional(
                    name="Rafael Costa",
                    specialty="Barbeiro",
                    working_hours=hours(TUE_TO_SAT, ("09:00", "12:00"), ("13:30", "19:00")),
                ),
                Professional(
                    name="Diego Almeida",
                    specialty="Barbeiro",
                    working_hours=hours(TUE_TO_SAT, ("10:00", "20:00")),
                ),
            ],
            services=[
                Service(name="Corte masculino", duration_minutes=30, price_cents=4500),
                Service(name="Barba completa", duration_minutes=30, price_cents=3500),
                Service(name="Corte + barba", duration_minutes=60, price_cents=7000),
            ],
        ),
        Business(
            name="Studio Bella Unhas",
            category="beleza",
            description="Manicure, pedicure e design de sobrancelhas com atendimento hora marcada.",
            address="Rua Néo Alves Martins, 450 · Centro, Maringá/PR",
            timezone="America/Sao_Paulo",
            professionals=[
                Professional(
                    name="Juliana Ribeiro",
                    specialty="Manicure e pedicure",
                    working_hours=hours(MON_TO_SAT, ("08:00", "12:00"), ("13:00", "18:00")),
                ),
                Professional(
                    name="Camila Souza",
                    specialty="Designer de sobrancelhas",
                    working_hours=hours(MON_TO_SAT, ("09:00", "17:00")),
                ),
            ],
            services=[
                Service(name="Manicure", duration_minutes=45, price_cents=4000),
                Service(name="Pedicure", duration_minutes=45, price_cents=4500),
                Service(name="Design de sobrancelha", duration_minutes=30, price_cents=5000),
            ],
        ),
        Business(
            name="Clínica Sorriso Pleno",
            category="saude",
            description="Odontologia para toda a família: avaliação, limpeza e ortodontia.",
            address="Av. Tiradentes, 890 · Zona 03, Maringá/PR",
            timezone="America/Sao_Paulo",
            professionals=[
                Professional(
                    name="Dra. Fernanda Lima",
                    specialty="Ortodontista",
                    working_hours=hours(WEEKDAYS, ("08:00", "12:00"), ("14:00", "18:00")),
                ),
                Professional(
                    name="Dr. Bruno Martins",
                    specialty="Clínico geral",
                    working_hours=hours(WEEKDAYS, ("08:00", "12:00"), ("13:00", "17:00")),
                ),
            ],
            services=[
                Service(name="Avaliação", duration_minutes=30, price_cents=0),
                Service(name="Limpeza", duration_minutes=60, price_cents=18000),
                Service(name="Manutenção de aparelho", duration_minutes=30, price_cents=12000),
            ],
        ),
        Business(
            name="Espaço Zen Massoterapia",
            category="bem-estar",
            description="Massagens relaxantes e terapêuticas para aliviar a rotina.",
            address="Rua Santos Dumont, 2100 · Zona 07, Maringá/PR",
            timezone="America/Sao_Paulo",
            professionals=[
                Professional(
                    name="Lucas Pereira",
                    specialty="Massoterapeuta",
                    working_hours=hours(MON_TO_SAT, ("10:00", "20:00")),
                ),
            ],
            services=[
                Service(name="Massagem relaxante", duration_minutes=60, price_cents=15000),
                Service(name="Quick massage", duration_minutes=30, price_cents=7000),
            ],
        ),
    ]


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with async_sessionmaker(engine)() as session:
        if await session.scalar(select(Business.id).limit(1)) is None:
            session.add_all(businesses())
            await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
