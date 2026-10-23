from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, TypeAdapter

TOPICS = ("booking.events", "waitlist.events")


class BookingDetails(BaseModel):
    booking_id: UUID
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    customer_name: str
    customer_email: str
    business_name: str
    business_address: str
    timezone: str
    professional_name: str
    service_name: str
    price_cents: int


class BookingRef(BaseModel):
    booking_id: UUID


class BookingCreated(BaseModel):
    event_id: UUID
    type: Literal["booking.created"]
    data: BookingDetails


class BookingCancelled(BaseModel):
    event_id: UUID
    type: Literal["booking.cancelled"]
    data: BookingRef


class OfferDetails(BookingDetails):
    offer_id: UUID
    expires_at: AwareDatetime


class OfferCreated(BaseModel):
    event_id: UUID
    type: Literal["waitlist.offer_created"]
    data: OfferDetails


Event = BookingCreated | BookingCancelled | OfferCreated
event_adapter: TypeAdapter[Event] = TypeAdapter(Annotated[Event, Field(discriminator="type")])
