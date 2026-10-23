from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EntryIn(BaseModel):
    business_id: UUID
    professional_id: UUID
    service_id: UUID
    day: date
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: EmailStr


class Entry(BaseModel):
    id: UUID
    position: int


class OfferEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_name: str
    details: dict[str, Any]


class Offer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    status: Literal["pending", "claimed", "expired"]
    starts_at: datetime
    ends_at: datetime
    expires_at: datetime
    entry: OfferEntry
