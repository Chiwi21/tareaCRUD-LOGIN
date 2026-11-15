from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ShipmentCreate(BaseModel):
    operation_id: int
    carrier_id: int | None = None
    tracking_number: str | None = Field(default=None, max_length=80)
    origin_port_id: int | None = None
    destination_port_id: int | None = None
    departure_date: date | None = None
    estimated_arrival: date | None = None
    actual_arrival: date | None = None
    status: str = "PENDING"
    notes: str | None = None


class ShipmentUpdate(BaseModel):
    carrier_id: int | None = None
    tracking_number: str | None = Field(default=None, max_length=80)
    origin_port_id: int | None = None
    destination_port_id: int | None = None
    departure_date: date | None = None
    estimated_arrival: date | None = None
    actual_arrival: date | None = None
    status: str | None = None
    notes: str | None = None


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: int
    operation_code: str
    carrier_name: str | None = None
    tracking_number: str | None = None
    origin_port: str | None = None
    destination_port: str | None = None
    departure_date: date | None = None
    estimated_arrival: date | None = None
    actual_arrival: date | None = None
    status: str
    notes: str | None = None
