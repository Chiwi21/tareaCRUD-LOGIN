from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    operation_id: int
    document_type_id: int
    name: str = Field(min_length=2, max_length=160)
    status: str = "PENDING"
    file_url: str | None = Field(default=None, max_length=500)
    issue_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class DocumentUpdate(BaseModel):
    document_type_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: str | None = None
    file_url: str | None = Field(default=None, max_length=500)
    issue_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: int
    document_type_id: int
    document_type_name: str
    name: str
    status: str
    file_url: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class ChecklistItemOut(BaseModel):
    document_type_id: int
    document_type_name: str
    is_required: bool
    requires_expiry: bool
    document_id: int | None = None
    status: str
    expiry_date: date | None = None
    is_complete: bool
