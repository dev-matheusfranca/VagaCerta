from datetime import time
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class WorkingHours(Schema):
    weekday: int = Field(ge=0, le=6)
    start: time
    end: time

    @model_validator(mode="after")
    def check_range(self) -> Self:
        if self.start >= self.end:
            raise ValueError("O início do expediente deve ser antes do fim")
        return self


class ProfessionalIn(Schema):
    name: str = Field(min_length=2, max_length=120)
    specialty: str = Field(max_length=80)
    working_hours: list[WorkingHours]


class Professional(ProfessionalIn):
    id: UUID


class ServiceIn(Schema):
    name: str = Field(min_length=2, max_length=120)
    duration_minutes: int = Field(gt=0, le=480)
    price_cents: int = Field(ge=0)


class Service(ServiceIn):
    id: UUID


class BusinessIn(Schema):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(max_length=40)
    description: str = Field(max_length=500)
    address: str = Field(max_length=200)
    timezone: str = "America/Sao_Paulo"

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Fuso horário desconhecido") from None
        return value


class Business(BusinessIn):
    id: UUID


class BusinessDetail(Business):
    professionals: list[Professional]
    services: list[Service]
