from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceCreate(BaseModel):
    operation_id: int
    currency_id: int | None = None
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    tax_amount: Decimal = Field(ge=0, default=0)
    notes: str | None = None


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0)
    payment_date: date = Field(default_factory=date.today)
    method: str = "TRANSFER"
    reference: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    payment_date: date
    method: str
    reference: str | None = None
    notes: str | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    operation_id: int
    operation_code: str
    currency: str | None = None
    issue_date: date
    due_date: date | None = None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    paid_amount: Decimal
    balance: Decimal
    status: str
    notes: str | None = None
    payments: list[PaymentOut] = Field(default_factory=list)
