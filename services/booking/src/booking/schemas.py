from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field


class BookingIn(BaseModel):
    business_id: UUID
    professional_id: UUID
    service_id: UUID
    starts_at: AwareDatetime
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: EmailStr


class Booking(BookingIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ends_at: datetime
    status: Literal["confirmed", "cancelled"]


class Availability(BaseModel):
    slots: list[datetime]
