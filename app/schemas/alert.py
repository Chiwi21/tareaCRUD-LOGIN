from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: int | None = None
    operation_code: str | None = None
    type: str
    severity: str
    title: str
    message: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
