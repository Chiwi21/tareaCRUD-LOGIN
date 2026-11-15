from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Alert,
    Company,
    Invoice,
    Operation,
    OperationItem,
    Payment,
    Product,
    Shipment,
)


class SqlAlchemyDashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def _operation_scope(self, stmt, user_id: int | None):
        if user_id is not None:
            stmt = stmt.where(Operation.user_id == user_id)
        return stmt

    def summary(self, user_id: int | None = None) -> dict:
        operations = select(func.count()).select_from(Operation)
        operations = self._operation_scope(operations, user_id)
        open_operations = select(func.count()).select_from(Operation).where(
            Operation.status.notin_(("DONE", "CANCELLED"))
        )
        open_operations = self._operation_scope(open_operations, user_id)

        invoices = select(func.coalesce(func.sum(Invoice.total), 0))
        payments = select(func.coalesce(func.sum(Payment.amount), 0))
        alerts = select(func.count()).select_from(Alert).where(Alert.status == "OPEN")
        if user_id is not None:
            invoices = invoices.where(Invoice.operation.has(Operation.user_id == user_id))
            payments = payments.where(
                Payment.invoice.has(Invoice.operation.has(Operation.user_id == user_id))
            )
            alerts = alerts.where(Alert.operation.has(Operation.user_id == user_id))

        invoiced = self.db.scalar(invoices) or 0
        paid = self.db.scalar(payments) or 0
        return {
            "operations_total": self.db.scalar(operations) or 0,
            "operations_open": self.db.scalar(open_operations) or 0,
            "companies": self.db.scalar(select(func.count()).select_from(Company)) or 0,
            "products": self.db.scalar(select(func.count()).select_from(Product)) or 0,
            "invoiced_total": invoiced,
            "paid_total": paid,
            "balance_total": invoiced - paid,
            "open_alerts": self.db.scalar(alerts) or 0,
        }

    def operations_by_status(self, user_id: int | None = None):
        stmt = select(Operation.status, func.count()).group_by(Operation.status)
        stmt = self._operation_scope(stmt, user_id)
        rows = self.db.execute(stmt).all()
        return [{"status": status, "count": count} for status, count in rows]

    def operations_by_type(self, user_id: int | None = None):
        stmt = select(Operation.type, func.count()).group_by(Operation.type)
        stmt = self._operation_scope(stmt, user_id)
        rows = self.db.execute(stmt).all()
        return [{"type": type_, "count": count} for type_, count in rows]

    def recent_operations(self, limit: int = 6, user_id: int | None = None):
        stmt = select(Operation).options(
            joinedload(Operation.company),
            joinedload(Operation.user),
            selectinload(Operation.items),
        )
        stmt = self._operation_scope(stmt, user_id)
        return self.db.scalars(stmt.order_by(Operation.id.desc()).limit(limit)).unique().all()

    def top_products(self, limit: int = 5, user_id: int | None = None):
        stmt = (
            select(
                Product.name,
                Product.sku,
                func.coalesce(func.sum(OperationItem.quantity), 0).label("quantity"),
                func.coalesce(func.sum(OperationItem.subtotal), 0).label("subtotal"),
            )
            .join(OperationItem, OperationItem.product_id == Product.id)
            .join(Operation, Operation.id == OperationItem.operation_id)
        )
        if user_id is not None:
            stmt = stmt.where(Operation.user_id == user_id)
        stmt = (
            stmt.group_by(Product.id, Product.name, Product.sku)
            .order_by(func.sum(OperationItem.subtotal).desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {"name": name, "sku": sku, "quantity": quantity, "subtotal": subtotal}
            for name, sku, quantity, subtotal in rows
        ]

    def upcoming_shipments(self, limit: int = 5, user_id: int | None = None):
        stmt = (
            select(Shipment)
            .where(
                Shipment.estimated_arrival.is_not(None),
                Shipment.status.notin_(("DELIVERED", "CANCELLED")),
            )
            .options(joinedload(Shipment.carrier), joinedload(Shipment.operation))
        )
        if user_id is not None:
            stmt = stmt.where(Shipment.operation.has(Operation.user_id == user_id))
        return self.db.scalars(
            stmt.order_by(Shipment.estimated_arrival).limit(limit)
        ).unique().all()

    def open_alerts(self, limit: int = 6, user_id: int | None = None):
        stmt = select(Alert).where(Alert.status == "OPEN").options(
            joinedload(Alert.operation)
        )
        if user_id is not None:
            stmt = stmt.where(Alert.operation.has(Operation.user_id == user_id))
        return self.db.scalars(
            stmt.order_by(Alert.created_at.desc()).limit(limit)
        ).unique().all()
