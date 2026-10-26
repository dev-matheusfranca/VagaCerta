from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field, TypeAdapter

TOPICS = ("booking.events", "waitlist.events")


class Slot(BaseModel):
    business_id: UUID
    starts_at: AwareDatetime
    timezone: str
    price_cents: int

    @property
    def day(self) -> date:
        return self.starts_at.astimezone(ZoneInfo(self.timezone)).date()


class BookedSlot(Slot):
    booking_id: UUID
    ends_at: AwareDatetime

    @property
    def minutes(self) -> int:
        return int((self.ends_at - self.starts_at).total_seconds()) // 60

    @property
    def local_start(self) -> datetime:
        return self.starts_at.astimezone(ZoneInfo(self.timezone))


class BookingRef(BaseModel):
    booking_id: UUID


class BookingCreated(BaseModel):
    event_id: UUID
    type: Literal["booking.created"]
    data: BookedSlot


class BookingCancelled(BaseModel):
    event_id: UUID
    type: Literal["booking.cancelled"]
    data: BookingRef


class BookingOutcome(BaseModel):
    event_id: UUID
    type: Literal["booking.completed", "booking.no_show"]
    data: BookingRef


class OfferEvent(BaseModel):
    event_id: UUID
    type: Literal["waitlist.offer_created", "waitlist.offer_claimed", "waitlist.offer_expired"]
    data: Slot


Event = BookingCreated | BookingCancelled | BookingOutcome | OfferEvent
event_adapter: TypeAdapter[Event] = TypeAdapter(Annotated[Event, Field(discriminator="type")])
