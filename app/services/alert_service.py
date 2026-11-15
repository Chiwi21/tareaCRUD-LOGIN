from __future__ import annotations

from datetime import date, datetime, timedelta

from app.constants import (
    ALERT_DELAYED_SHIPMENT,
    ALERT_EXPIRING_DOC,
    ALERT_MISSING_DOC,
    ALERT_OVERDUE_INVOICE,
    ALERT_STALLED,
    EXPIRING_DAYS,
    STALLED_DAYS,
)
from app.repositories.protocols import (
    AlertFilters,
    AlertRepository,
    BillingRepository,
    DocumentRepository,
    InvoiceFilters,
    LogisticsRepository,
    OperationReader,
)


class AlertService:
    """Genera alertas de operación a partir de reglas de negocio."""

    def __init__(
        self,
        repository: AlertRepository,
        operations: OperationReader,
        documents: DocumentRepository,
        billing: BillingRepository,
        logistics: LogisticsRepository,
    ):
        self.repository = repository
        self.operations = operations
        self.documents = documents
        self.billing = billing
        self.logistics = logistics

    def list(self, filters: AlertFilters | None = None):
        return self.repository.list(filters)

    def open_count(self) -> int:
        return self.repository.open_count()

    def resolve(self, alert_id: int, user_id: int | None):
        return self.repository.resolve(alert_id, user_id)

    def _upsert(self, fingerprint: str, values: dict) -> None:
        self.repository.upsert(fingerprint, values)

    def generate_all(self) -> int:
        generated = 0
        today = date.today()
        now = datetime.now()

        for operation in self.operations.list():
            if operation.status in ("DONE", "CANCELLED"):
                continue
            last_movement = operation.updated_at or operation.created_at
            if last_movement and now - last_movement > timedelta(days=STALLED_DAYS):
                self._upsert(
                    f"stalled:{operation.id}",
                    {
                        "operation_id": operation.id,
                        "type": ALERT_STALLED,
                        "severity": "WARNING",
                        "title": f"Operación {operation.code} sin movimiento",
                        "message": (
                            f"La operación no registra cambios desde "
                            f"{last_movement.strftime('%Y-%m-%d')}. Revise su avance."
                        ),
                    },
                )
                generated += 1

            for entry in self.documents.checklist(operation.id):
                if entry.document_type.is_required and not entry.is_complete:
                    status_text = "no registrado" if entry.document is None else "no aprobado"
                    self._upsert(
                        f"missing:{operation.id}:{entry.document_type.id}",
                        {
                            "operation_id": operation.id,
                            "type": ALERT_MISSING_DOC,
                            "severity": "WARNING",
                            "title": f"Documento requerido: {entry.document_type.name}",
                            "message": (
                                f"La operación {operation.code} tiene el documento "
                                f"'{entry.document_type.name}' {status_text}."
                            ),
                        },
                    )
                    generated += 1

                if entry.document and entry.expiry_date:
                    days = (entry.expiry_date - today).days
                    if days < 0:
                        self._upsert(
                            f"expiring:{entry.document.id}",
                            {
                                "operation_id": operation.id,
                                "type": ALERT_EXPIRING_DOC,
                                "severity": "CRITICAL",
                                "title": f"Documento vencido: {entry.document.name}",
                                "message": (
                                    f"El documento venció el {entry.expiry_date.isoformat()} "
                                    f"en la operación {operation.code}."
                                ),
                            },
                        )
                        generated += 1
                    elif days <= EXPIRING_DAYS:
                        self._upsert(
                            f"expiring:{entry.document.id}",
                            {
                                "operation_id": operation.id,
                                "type": ALERT_EXPIRING_DOC,
                                "severity": "WARNING",
                                "title": f"Documento por vencer: {entry.document.name}",
                                "message": (
                                    f"El documento vence en {days} días "
                                    f"({entry.expiry_date.isoformat()})."
                                ),
                            },
                        )
                        generated += 1

        for invoice in self.billing.list(InvoiceFilters()):
            if invoice.is_overdue:
                self._upsert(
                    f"overdue:{invoice.id}",
                    {
                        "operation_id": invoice.operation_id,
                        "type": ALERT_OVERDUE_INVOICE,
                        "severity": "CRITICAL",
                        "title": f"Factura vencida {invoice.number}",
                        "message": (
                            f"La factura venció el {invoice.due_date.isoformat()} y mantiene "
                            f"un saldo de {invoice.balance:.2f}."
                        ),
                    },
                )
                generated += 1

        for shipment in self.logistics.list():
            if (
                shipment.estimated_arrival
                and shipment.estimated_arrival < today
                and shipment.status not in ("DELIVERED", "CANCELLED")
            ):
                self._upsert(
                    f"delayed:{shipment.id}",
                    {
                        "operation_id": shipment.operation_id,
                        "type": ALERT_DELAYED_SHIPMENT,
                        "severity": "CRITICAL",
                        "title": f"Embarque retrasado de {shipment.operation.code}",
                        "message": (
                            f"La llegada estimada era {shipment.estimated_arrival.isoformat()} "
                            f"y el embarque sigue en estado {shipment.status}."
                        ),
                    },
                )
                generated += 1

        return generated
