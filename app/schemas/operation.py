from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OperationItemCreate(BaseModel):
    product_id: int
    description: str | None = Field(default=None, max_length=200)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class OperationItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class OperationCreate(BaseModel):
    type: str = Field(pattern="^(IMPORT|EXPORT)$")
    company_id: int | None = None
    user_id: int | None = None
    operation_date: date = Field(default_factory=date.today)
    origin_port_id: int | None = None
    destination_port_id: int | None = None
    currency_id: int | None = None
    incoterm_id: int | None = None
    status: str = "PENDING"
    notes: str | None = None
    items: list[OperationItemCreate] = Field(default_factory=list)


class OperationUpdate(BaseModel):
    type: str | None = Field(default=None, pattern="^(IMPORT|EXPORT)$")
    company_id: int | None = None
    user_id: int | None = None
    operation_date: date | None = None
    origin_port_id: int | None = None
    destination_port_id: int | None = None
    currency_id: int | None = None
    incoterm_id: int | None = None
    status: str | None = None
    notes: str | None = None
    items: list[OperationItemCreate] | None = None


class OperationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    type: str
    status: str
    operation_date: date
    company_name: str | None = None
    user_name: str | None = None
    origin_port: str | None = None
    destination_port: str | None = None
    currency: str | None = None
    incoterm: str | None = None
    product_subtotal: Decimal
    selected_scenario_total: Decimal | None = None
    items: list[OperationItemOut] = Field(default_factory=list)
    created_at: str | None = None


class StatusChange(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=300)
