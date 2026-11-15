from __future__ import annotations

from app.constants import OPERATION_STATUSES, OPERATION_STATUS_FLOW, OPERATION_TYPES
from app.repositories.protocols import OperationFilters, OperationReader, OperationWriter
from app.schemas import OperationCreate, OperationItemCreate, OperationUpdate
from app.services.audit_service import AuditService
from app.services.errors import NotFoundError, ValidationError


class OperationService:
    """Reglas de negocio de operaciones; depende de interfaces, no de SQLAlchemy."""

    def __init__(
        self,
        reader: OperationReader,
        writer: OperationWriter,
        audit: AuditService,
    ):
        self.reader = reader
        self.writer = writer
        self.audit = audit

    def list(self, filters: OperationFilters | None = None):
        return self.reader.list(filters)

    def list_for_user(self, user_id: int):
        return self.reader.list_for_user(user_id)

    def get(self, operation_id: int):
        operation = self.reader.get(operation_id)
        if operation is None:
            raise NotFoundError("Operación no encontrada.")
        return operation

    def form_context(self) -> dict:
        return {
            "companies": self.reader.list_companies(),
            "available_users": self.reader.list_assignable_users(),
            "ports": self.reader.list_ports(),
            "currencies": self.reader.list_currencies(),
            "incoterms": self.reader.list_incoterms(),
            "products": self.reader.list_products(),
            "document_types": self.reader.list_document_types(),
            "carriers": self.reader.list_carriers(),
            "cost_concepts": self.reader.list_cost_concepts(),
        }

    def validate(self, data: OperationCreate | OperationUpdate) -> list[str]:
        errors: list[str] = []
        if data.type is not None and data.type not in OPERATION_TYPES:
            errors.append("Debe seleccionar un tipo de operación válido.")
        if getattr(data, "status", None) and data.status not in OPERATION_STATUSES:
            errors.append("Debe seleccionar un estado válido.")
        if data.user_id is not None and data.user_id not in {
            user.id for user in self.reader.list_assignable_users()
        }:
            errors.append("El usuario responsable no existe o no puede tener operaciones.")
        if data.company_id is not None and data.company_id not in {
            company.id for company in self.reader.list_companies()
        }:
            errors.append("La empresa seleccionada no existe.")
        port_ids = {port.id for port in self.reader.list_ports()}
        if data.origin_port_id is not None and data.origin_port_id not in port_ids:
            errors.append("El puerto de origen no existe.")
        if data.destination_port_id is not None and data.destination_port_id not in port_ids:
            errors.append("El puerto de destino no existe.")
        if data.currency_id is not None and data.currency_id not in {
            currency.id for currency in self.reader.list_currencies()
        }:
            errors.append("La moneda seleccionada no existe.")
        if data.incoterm_id is not None and data.incoterm_id not in {
            incoterm.id for incoterm in self.reader.list_incoterms()
        }:
            errors.append("El incoterm seleccionado no existe.")
        if data.items is not None:
            product_ids = {product.id for product in self.reader.list_products()}
            for item in data.items:
                if item.product_id not in product_ids:
                    errors.append("Uno de los productos seleccionados no existe.")
                if item.quantity <= 0:
                    errors.append("La cantidad de cada ítem debe ser mayor a cero.")
                if item.unit_price < 0:
                    errors.append("El precio unitario no puede ser negativo.")
        return errors

    def create(self, data: OperationCreate, actor_id: int | None) -> tuple:
        errors = self.validate(data)
        if errors:
            raise ValidationError(errors)
        operation = self.writer.create(data, actor_id)
        self.audit.log(
            actor_id,
            "CREATE",
            "operations",
            operation.id,
            f"Operación {operation.code} creada",
        )
        return operation

    def update(self, operation_id: int, data: OperationUpdate, actor_id: int | None):
        self.get(operation_id)
        errors = self.validate(data)
        if errors:
            raise ValidationError(errors)
        operation = self.writer.update(operation_id, data, actor_id)
        self.audit.log(
            actor_id,
            "UPDATE",
            "operations",
            operation.id,
            f"Operación {operation.code} actualizada",
        )
        return operation

    def delete(self, operation_id: int, actor_id: int | None) -> None:
        operation = self.get(operation_id)
        code = operation.code
        self.writer.delete(operation_id)
        self.audit.log(actor_id, "DELETE", "operations", operation_id, f"Operación {code} eliminada")

    def add_item(self, operation_id: int, data: OperationItemCreate, actor_id: int | None):
        self.get(operation_id)
        if data.product_id not in {product.id for product in self.reader.list_products()}:
            raise ValidationError(["El producto seleccionado no existe."])
        if data.quantity <= 0:
            raise ValidationError(["La cantidad debe ser mayor a cero."])
        if data.unit_price < 0:
            raise ValidationError(["El precio unitario no puede ser negativo."])
        item = self.writer.add_item(operation_id, data)
        self.audit.log(
            actor_id,
            "UPDATE",
            "operation_items",
            item.id,
            f"Ítem agregado a la operación #{operation_id}",
        )
        return item

    def remove_item(self, operation_id: int, item_id: int, actor_id: int | None) -> None:
        self.writer.remove_item(operation_id, item_id)
        self.audit.log(
            actor_id,
            "DELETE",
            "operation_items",
            item_id,
            f"Ítem eliminado de la operación #{operation_id}",
        )

    def change_status(
        self,
        operation_id: int,
        new_status: str,
        actor_id: int | None,
        note: str | None = None,
    ):
        operation = self.get(operation_id)
        if new_status not in OPERATION_STATUSES:
            raise ValidationError(["El estado seleccionado no es válido."])
        if new_status == operation.status:
            return operation
        allowed = OPERATION_STATUS_FLOW.get(operation.status, ())
        if new_status not in allowed:
            raise ValidationError(
                [
                    f"No se puede pasar de {OPERATION_STATUSES[operation.status]} "
                    f"a {OPERATION_STATUSES[new_status]}."
                ]
            )
        updated = self.writer.change_status(operation_id, new_status, actor_id, note)
        self.audit.log(
            actor_id,
            "STATUS_CHANGE",
            "operations",
            operation_id,
            f"Estado: {operation.status} → {new_status}",
        )
        return updated
