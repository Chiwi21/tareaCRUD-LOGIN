from __future__ import annotations

from app.constants import DOCUMENT_STATUSES
from app.repositories.protocols import DocumentFilters, DocumentRepository, OperationReader
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.audit_service import AuditService
from app.services.errors import NotFoundError, ValidationError


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        operations: OperationReader,
        audit: AuditService,
    ):
        self.repository = repository
        self.operations = operations
        self.audit = audit

    def list(self, filters: DocumentFilters | None = None):
        return self.repository.list(filters)

    def get(self, document_id: int):
        document = self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Documento no encontrado.")
        return document

    def checklist(self, operation_id: int):
        return self.repository.checklist(operation_id)

    def form_context(self) -> dict:
        return {
            "operations": self.operations.list(),
            "document_types": self.operations.list_document_types(),
        }

    def _validate(
        self,
        operation_id: int,
        document_type_id: int,
        status: str,
        expiry_date,
    ) -> list[str]:
        errors: list[str] = []
        if self.operations.get(operation_id) is None:
            errors.append("La operación seleccionada no existe.")
        document_type = next(
            (
                doc_type
                for doc_type in self.operations.list_document_types()
                if doc_type.id == document_type_id
            ),
            None,
        )
        if document_type is None:
            errors.append("El tipo de documento no existe.")
        elif document_type.requires_expiry and expiry_date is None:
            errors.append("Este tipo de documento requiere fecha de vencimiento.")
        if status not in DOCUMENT_STATUSES:
            errors.append("El estado del documento no es válido.")
        return errors

    def create(self, data: DocumentCreate, actor_id: int | None):
        errors = self._validate(
            data.operation_id, data.document_type_id, data.status, data.expiry_date
        )
        if errors:
            raise ValidationError(errors)
        document = self.repository.create(data, actor_id)
        self.audit.log(
            actor_id,
            "CREATE",
            "documents",
            document.id,
            f"Documento '{document.name}' agregado a la operación #{document.operation_id}",
        )
        return document

    def update(self, document_id: int, data: DocumentUpdate, actor_id: int | None):
        document = self.get(document_id)
        document_type_id = data.document_type_id or document.document_type_id
        status = data.status or document.status
        expiry_date = data.expiry_date if "expiry_date" in data.model_fields_set else document.expiry_date
        errors = self._validate(document.operation_id, document_type_id, status, expiry_date)
        if errors:
            raise ValidationError(errors)
        updated = self.repository.update(document_id, data)
        self.audit.log(
            actor_id,
            "UPDATE",
            "documents",
            document_id,
            f"Documento '{updated.name}' actualizado",
        )
        return updated

    def delete(self, document_id: int, actor_id: int | None) -> None:
        document = self.get(document_id)
        name = document.name
        self.repository.delete(document_id)
        self.audit.log(actor_id, "DELETE", "documents", document_id, f"Documento '{name}' eliminado")
