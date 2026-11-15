from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    person_type: str | None = None
    full_name: str | None = None
    cedula: str | None = None
    ruc: str | None = None
    razon_social: str | None = None
    company_name: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)
