from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Alert
from app.repositories.protocols import AlertFilters


class SqlAlchemyAlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, filters: AlertFilters | None = None):
        stmt = select(Alert).options(joinedload(Alert.operation))
        if filters:
            if filters.status:
                stmt = stmt.where(Alert.status == filters.status)
            if filters.severity:
                stmt = stmt.where(Alert.severity == filters.severity)
            if filters.operation_id:
                stmt = stmt.where(Alert.operation_id == filters.operation_id)
        return self.db.scalars(
            stmt.order_by(Alert.status, Alert.created_at.desc())
        ).unique().all()

    def get(self, alert_id: int) -> Alert | None:
        return self.db.scalars(
            select(Alert).where(Alert.id == alert_id).options(joinedload(Alert.operation))
        ).unique().first()

    def upsert(self, fingerprint: str, values: dict[str, Any]) -> Alert:
        alert = self.db.scalars(
            select(Alert).where(Alert.fingerprint == fingerprint)
        ).first()
        if alert is None:
            alert = Alert(fingerprint=fingerprint, **values)
            self.db.add(alert)
        else:
            alert.type = values.get("type", alert.type)
            alert.severity = values.get("severity", alert.severity)
            alert.title = values.get("title", alert.title)
            alert.message = values.get("message", alert.message)
            alert.operation_id = values.get("operation_id", alert.operation_id)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve(self, alert_id: int, user_id: int | None) -> Alert:
        alert = self.db.get(Alert, alert_id)
        if alert is None:
            raise ValueError("Alerta no encontrada.")
        alert.status = "RESOLVED"
        alert.resolved_at = datetime.now()
        alert.resolved_by_id = user_id
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def open_count(self) -> int:
        return (
            self.db.scalar(
                select(func.count()).select_from(Alert).where(Alert.status == "OPEN")
            )
            or 0
        )
