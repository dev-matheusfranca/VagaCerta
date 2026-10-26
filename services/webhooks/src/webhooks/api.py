import secrets
from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vagacerta_auth import Claims, require_role
from webhooks.models import Delivery, Subscription
from webhooks.targets import ForbiddenTarget, check_target

router = APIRouter()

EventType = Literal[
    "booking.created",
    "booking.cancelled",
    "booking.completed",
    "booking.no_show",
    "waitlist.offer_created",
    "waitlist.offer_claimed",
    "waitlist.offer_expired",
]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
Owner = Annotated[Claims, Depends(require_role("owner"))]


class SubscriptionIn(BaseModel):
    url: str = Field(max_length=500)
    events: list[EventType] = Field(min_length=1)


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    events: list[str]
    created_at: datetime


class CreatedSubscription(SubscriptionOut):
    # Única resposta que traz o segredo.
    secret: str


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    status: str
    attempts: int
    last_status_code: int | None
    last_error: str | None
    updated_at: datetime


def check_owner(claims: Claims, business_id: UUID) -> None:
    if str(business_id) not in claims.get("businesses", []):
        raise HTTPException(403, "Você não tem acesso a este estabelecimento")


async def owned_subscription(
    session: AsyncSession, business_id: UUID, subscription_id: UUID
) -> Subscription:
    subscription = await session.get(Subscription, subscription_id)
    if subscription is None or subscription.business_id != business_id:
        raise HTTPException(404, "Webhook não encontrado")
    return subscription


@router.post(
    "/businesses/{business_id}/webhooks", response_model=CreatedSubscription, status_code=201
)
async def subscribe(
    business_id: UUID, data: SubscriptionIn, request: Request, session: Session, claims: Owner
) -> Subscription:
    check_owner(claims, business_id)
    try:
        await check_target(data.url, request.app.state.allow_private_targets)
    except ForbiddenTarget as error:
        raise HTTPException(422, str(error)) from None
    subscription = Subscription(
        business_id=business_id, url=data.url, events=data.events, secret=secrets.token_hex(24)
    )
    session.add(subscription)
    await session.commit()
    return subscription


@router.get("/businesses/{business_id}/webhooks", response_model=list[SubscriptionOut])
async def list_subscriptions(
    business_id: UUID, session: Session, claims: Owner
) -> Sequence[Subscription]:
    check_owner(claims, business_id)
    subscriptions = await session.scalars(
        select(Subscription)
        .where(Subscription.business_id == business_id)
        .order_by(Subscription.created_at)
    )
    return subscriptions.all()


@router.delete("/businesses/{business_id}/webhooks/{subscription_id}", status_code=204)
async def unsubscribe(
    business_id: UUID, subscription_id: UUID, session: Session, claims: Owner
) -> None:
    check_owner(claims, business_id)
    await session.delete(await owned_subscription(session, business_id, subscription_id))
    await session.commit()


@router.get(
    "/businesses/{business_id}/webhooks/{subscription_id}/deliveries",
    response_model=list[DeliveryOut],
)
async def list_deliveries(
    business_id: UUID, subscription_id: UUID, session: Session, claims: Owner
) -> Sequence[Delivery]:
    check_owner(claims, business_id)
    await owned_subscription(session, business_id, subscription_id)
    deliveries = await session.scalars(
        select(Delivery)
        .where(Delivery.subscription_id == subscription_id)
        .order_by(Delivery.created_at.desc())
        .limit(20)
    )
    return deliveries.all()
