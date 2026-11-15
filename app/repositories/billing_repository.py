from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.costing import money
from app.models import Invoice, Operation, Payment
from app.repositories.protocols import InvoiceFilters
from app.schemas import InvoiceCreate, PaymentCreate


class SqlAlchemyBillingRepository:
    def __init__(self, db: Session):
        self.db = db

    def _options(self):
        return (
            joinedload(Invoice.operation),
            joinedload(Invoice.currency),
            selectinload(Invoice.payments),
        )

    def list(self, filters: InvoiceFilters | None = None):
        stmt = select(Invoice).options(*self._options())
        if filters:
            if filters.q:
                like = f"%{filters.q.strip()}%"
                stmt = stmt.where(
                    or_(
                        Invoice.number.ilike(like),
                        Invoice.operation.has(Operation.code.ilike(like)),
                    )
                )
            if filters.status:
                stmt = stmt.where(Invoice.status == filters.status)
            if filters.operation_id:
                stmt = stmt.where(Invoice.operation_id == filters.operation_id)
        return self.db.scalars(stmt.order_by(Invoice.id.desc())).unique().all()

    def get(self, invoice_id: int) -> Invoice | None:
        return self.db.scalars(
            select(Invoice).where(Invoice.id == invoice_id).options(*self._options())
        ).unique().first()

    def create(self, data: InvoiceCreate) -> Invoice:
        operation = self.db.get(Operation, data.operation_id)
        if operation is None:
            raise ValueError("Operación no encontrada.")
        subtotal = sum((item.subtotal for item in operation.items), Decimal("0"))
        next_id = (self.db.scalar(select(func.max(Invoice.id))) or 0) + 1
        invoice = Invoice(
            operation_id=operation.id,
            currency_id=data.currency_id or operation.currency_id,
            number=f"INV-{data.issue_date.year}-{next_id:04d}",
            issue_date=data.issue_date,
            due_date=data.due_date,
            subtotal=money(subtotal),
            tax_amount=money(data.tax_amount),
            total=money(subtotal + data.tax_amount),
            status="ISSUED",
            notes=data.notes,
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def delete(self, invoice_id: int) -> None:
        invoice = self.db.get(Invoice, invoice_id)
        if invoice is None:
            raise ValueError("Factura no encontrada.")
        self.db.delete(invoice)
        self.db.commit()

    def add_payment(self, data: PaymentCreate) -> Payment:
        invoice = self.db.get(Invoice, data.invoice_id)
        if invoice is None:
            raise ValueError("Factura no encontrada.")
        if invoice.status == "CANCELLED":
            raise ValueError("No se pueden registrar pagos de una factura anulada.")
        if money(data.amount) > invoice.balance:
            raise ValueError("El pago supera el saldo pendiente de la factura.")
        payment = Payment(
            invoice_id=invoice.id,
            amount=money(data.amount),
            payment_date=data.payment_date,
            method=data.method,
            reference=data.reference,
            notes=data.notes,
        )
        self.db.add(payment)
        self.db.commit()
        self.refresh_status(invoice.id)
        self.db.refresh(payment)
        return payment

    def delete_payment(self, payment_id: int) -> None:
        payment = self.db.get(Payment, payment_id)
        if payment is None:
            raise ValueError("Pago no encontrado.")
        invoice_id = payment.invoice_id
        self.db.delete(payment)
        self.db.commit()
        self.refresh_status(invoice_id)

    def refresh_status(self, invoice_id: int) -> Invoice:
        invoice = self.db.get(Invoice, invoice_id)
        if invoice is None:
            raise ValueError("Factura no encontrada.")
        if invoice.status != "CANCELLED":
            if invoice.total > 0 and invoice.paid_amount >= invoice.total:
                invoice.status = "PAID"
            elif invoice.paid_amount > 0:
                invoice.status = "PARTIAL"
            elif invoice.due_date is not None and invoice.due_date < date.today():
                invoice.status = "OVERDUE"
            else:
                invoice.status = "ISSUED"
            self.db.commit()
        return invoice
