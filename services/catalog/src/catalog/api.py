from collections.abc import AsyncIterator, Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from catalog import models, schemas
from vagacerta_auth import require_role

router = APIRouter()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
Admin = Depends(require_role("admin"))


async def get_business_or_404(
    session: AsyncSession, business_id: UUID, **kwargs: Any
) -> models.Business:
    business = await session.get(models.Business, business_id, **kwargs)
    if business is None:
        raise HTTPException(404, "Estabelecimento não encontrado")
    return business


@router.get("/businesses", response_model=list[schemas.Business])
async def list_businesses(session: Session) -> Sequence[models.Business]:
    return (await session.scalars(select(models.Business).order_by(models.Business.name))).all()


@router.post("/businesses", response_model=schemas.Business, status_code=201, dependencies=[Admin])
async def create_business(data: schemas.BusinessIn, session: Session) -> models.Business:
    business = models.Business(**data.model_dump())
    session.add(business)
    await session.commit()
    return business


@router.get("/businesses/{business_id}", response_model=schemas.BusinessDetail)
async def get_business(business_id: UUID, session: Session) -> models.Business:
    return await get_business_or_404(
        session,
        business_id,
        options=[
            selectinload(models.Business.professionals),
            selectinload(models.Business.services),
        ],
    )


@router.post(
    "/businesses/{business_id}/professionals",
    response_model=schemas.Professional,
    dependencies=[Admin],
    status_code=201,
)
async def create_professional(
    business_id: UUID, data: schemas.ProfessionalIn, session: Session
) -> models.Professional:
    await get_business_or_404(session, business_id)
    professional = models.Professional(
        business_id=business_id,
        name=data.name,
        specialty=data.specialty,
        working_hours=[models.WorkingHours(**hours.model_dump()) for hours in data.working_hours],
    )
    session.add(professional)
    await session.commit()
    return professional


@router.post(
    "/businesses/{business_id}/services",
    response_model=schemas.Service,
    status_code=201,
    dependencies=[Admin],
)
async def create_service(
    business_id: UUID, data: schemas.ServiceIn, session: Session
) -> models.Service:
    await get_business_or_404(session, business_id)
    service = models.Service(business_id=business_id, **data.model_dump())
    session.add(service)
    await session.commit()
    return service
