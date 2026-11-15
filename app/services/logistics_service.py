from __future__ import annotations

from app.constants import SHIPMENT_STATUSES
from app.repositories.protocols import LogisticsRepository, OperationReader
from app.schemas import ShipmentCreate, ShipmentUpdate
from app.services.audit_service import AuditService
from app.services.errors import NotFoundError, ValidationError


class LogisticsService:
    def __init__(
        self,
        repository: LogisticsRepository,
        operations: OperationReader,
        audit: AuditService,
    ):
        self.repository = repository
        self.operations = operations
        self.audit = audit

    def list(self):
        return self.repository.list()

    def get(self, shipment_id: int):
        shipment = self.repository.get(shipment_id)
        if shipment is None:
            raise NotFoundError("Embarque no encontrado.")
        return shipment

    def get_by_operation(self, operation_id: int):
        return self.repository.get_by_operation(operation_id)

    def form_context(self) -> dict:
        return {
            "operations": self.operations.list(),
            "carriers": self.operations.list_carriers(),
            "ports": self.operations.list_ports(),
        }

    def _validate(self, status: str, departure, arrival) -> list[str]:
        errors: list[str] = []
        if status not in SHIPMENT_STATUSES:
            errors.append("El estado del embarque no es válido.")
        if departure and arrival and arrival < departure:
            errors.append("La llegada estimada no puede ser anterior a la salida.")
        return errors

    def create(self, data: ShipmentCreate, actor_id: int | None):
        if self.operations.get(data.operation_id) is None:
            raise ValidationError(["La operación seleccionada no existe."])
        errors = self._validate(data.status, data.departure_date, data.estimated_arrival)
        if errors:
            raise ValidationError(errors)
        try:
            shipment = self.repository.create(data)
        except ValueError as exc:
            raise ValidationError([str(exc)]) from exc
        self.audit.log(
            actor_id,
            "CREATE",
            "shipments",
            shipment.id,
            f"Embarque creado para la operación #{shipment.operation_id}",
        )
        return shipment

    def update(self, shipment_id: int, data: ShipmentUpdate, actor_id: int | None):
        shipment = self.get(shipment_id)
        status = data.status or shipment.status
        departure = (
            data.departure_date
            if "departure_date" in data.model_fields_set
            else shipment.departure_date
        )
        arrival = (
            data.estimated_arrival
            if "estimated_arrival" in data.model_fields_set
            else shipment.estimated_arrival
        )
        errors = self._validate(status, departure, arrival)
        if errors:
            raise ValidationError(errors)
        updated = self.repository.update(shipment_id, data)
        self.audit.log(
            actor_id,
            "UPDATE",
            "shipments",
            shipment_id,
            f"Embarque de la operación #{updated.operation_id} actualizado",
        )
        return updated

    def delete(self, shipment_id: int, actor_id: int | None) -> None:
        self.get(shipment_id)
        self.repository.delete(shipment_id)
        self.audit.log(actor_id, "DELETE", "shipments", shipment_id, "Embarque eliminado")
