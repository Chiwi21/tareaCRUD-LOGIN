from __future__ import annotations

from app.constants import OPERATION_STATUSES, OPERATION_TYPES
from app.repositories.protocols import DashboardRepository


class DashboardService:
    def __init__(self, repository: DashboardRepository):
        self.repository = repository

    def overview(self, user_id: int | None = None) -> dict:
        status_rows = self.repository.operations_by_status(user_id)
        type_rows = self.repository.operations_by_type(user_id)
        max_status = max((row["count"] for row in status_rows), default=1) or 1
        max_type = max((row["count"] for row in type_rows), default=1) or 1
        for row in status_rows:
            row["label"] = OPERATION_STATUSES.get(row["status"], row["status"])
            row["percent"] = round(row["count"] * 100 / max_status)
        for row in type_rows:
            row["label"] = OPERATION_TYPES.get(row["type"], row["type"])
            row["percent"] = round(row["count"] * 100 / max_type)
        return {
            "summary": self.repository.summary(user_id),
            "status_rows": status_rows,
            "type_rows": type_rows,
            "recent_operations": self.repository.recent_operations(user_id=user_id),
            "top_products": self.repository.top_products(user_id=user_id),
            "upcoming_shipments": self.repository.upcoming_shipments(user_id=user_id),
            "alerts": self.repository.open_alerts(user_id=user_id),
        }
