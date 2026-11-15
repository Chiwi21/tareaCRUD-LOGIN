from __future__ import annotations

from app.repositories.protocols import BillingRepository, InvoiceFilters, OperationReader
from app.schemas import InvoiceCreate, PaymentCreate
from app.services.audit_service import AuditService
from app.services.errors import NotFoundError, ValidationError


class BillingService:
    def __init__(
        self,
        repository: BillingRepository,
        operations: OperationReader,
        audit: AuditService,
    ):
        self.repository = repository
        self.operations = operations
        self.audit = audit

    def list(self, filters: InvoiceFilters | None = None):
        return self.repository.list(filters)

    def get(self, invoice_id: int):
        invoice = self.repository.get(invoice_id)
        if invoice is None:
            raise NotFoundError("Factura no encontrada.")
        return invoice

    def form_context(self) -> dict:
        return {
            "operations": self.operations.list(),
            "currencies": self.operations.list_currencies(),
        }

    def create(self, data: InvoiceCreate, actor_id: int | None):
        if self.operations.get(data.operation_id) is None:
            raise ValidationError(["La operación seleccionada no existe."])
        if data.due_date and data.due_date < data.issue_date:
            raise ValidationError(["La fecha de vencimiento no puede ser anterior a la emisión."])
        invoice = self.repository.create(data)
        self.audit.log(
            actor_id,
            "CREATE",
            "invoices",
            invoice.id,
            f"Factura {invoice.number} creada para la operación #{invoice.operation_id}",
        )
        return invoice

    def add_payment(self, data: PaymentCreate, actor_id: int | None):
        invoice = self.repository.get(data.invoice_id)
        if invoice is None:
            raise ValidationError(["La factura seleccionada no existe."])
        if data.amount <= 0:
            raise ValidationError(["El monto del pago debe ser mayor a cero."])
        if data.amount > invoice.balance:
            raise ValidationError(
                [f"El pago supera el saldo pendiente ({invoice.balance:.2f})."]
            )
        payment = self.repository.add_payment(data)
        self.audit.log(
            actor_id,
            "CREATE",
            "payments",
            payment.id,
            f"Pago de {payment.amount:.2f} registrado en la factura {invoice.number}",
        )
        return payment

    def delete_payment(self, payment_id: int, actor_id: int | None) -> None:
        self.repository.delete_payment(payment_id)
        self.audit.log(actor_id, "DELETE", "payments", payment_id, "Pago eliminado")

    def delete_invoice(self, invoice_id: int, actor_id: int | None) -> None:
        invoice = self.get(invoice_id)
        number = invoice.number
        self.repository.delete(invoice_id)
        self.audit.log(actor_id, "DELETE", "invoices", invoice_id, f"Factura {number} eliminada")
