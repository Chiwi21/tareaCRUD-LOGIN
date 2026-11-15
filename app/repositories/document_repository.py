from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Document, DocumentType, Operation
from app.repositories.protocols import ChecklistEntry, DocumentFilters
from app.schemas import DocumentCreate, DocumentUpdate

STATUS_PRIORITY = {"APPROVED": 5, "RECEIVED": 4, "PENDING": 3, "REJECTED": 2, "EXPIRED": 1}


class SqlAlchemyDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, filters: DocumentFilters | None = None):
        stmt = select(Document).options(
            joinedload(Document.document_type),
            joinedload(Document.operation),
        )
        if filters:
            if filters.q:
                like = f"%{filters.q.strip()}%"
                stmt = stmt.where(
                    or_(
                        Document.name.ilike(like),
                        Document.operation.has(Operation.code.ilike(like)),
                        Document.document_type.has(DocumentType.name.ilike(like)),
                    )
                )
            if filters.status:
                stmt = stmt.where(Document.status == filters.status)
            if filters.operation_id:
                stmt = stmt.where(Document.operation_id == filters.operation_id)
        return self.db.scalars(stmt.order_by(Document.id.desc())).unique().all()

    def get(self, document_id: int) -> Document | None:
        return self.db.scalars(
            select(Document)
            .where(Document.id == document_id)
            .options(joinedload(Document.document_type), joinedload(Document.operation))
        ).unique().first()

    def create(self, data: DocumentCreate, uploaded_by_id: int | None = None) -> Document:
        if self.db.get(Operation, data.operation_id) is None:
            raise ValueError("Operación no encontrada.")
        if self.db.get(DocumentType, data.document_type_id) is None:
            raise ValueError("Tipo de documento no encontrado.")
        document = Document(
            operation_id=data.operation_id,
            document_type_id=data.document_type_id,
            name=data.name.strip(),
            status=data.status,
            file_url=data.file_url,
            issue_date=data.issue_date,
            expiry_date=data.expiry_date,
            notes=data.notes,
            uploaded_by_id=uploaded_by_id,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def update(self, document_id: int, data: DocumentUpdate) -> Document:
        document = self.db.get(Document, document_id)
        if document is None:
            raise ValueError("Documento no encontrado.")
        for field in data.model_fields_set:
            setattr(document, field, getattr(data, field))
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document_id: int) -> None:
        document = self.db.get(Document, document_id)
        if document is None:
            raise ValueError("Documento no encontrado.")
        self.db.delete(document)
        self.db.commit()

    def checklist(self, operation_id: int) -> list[ChecklistEntry]:
        operation = self.db.get(Operation, operation_id)
        if operation is None:
            raise ValueError("Operación no encontrada.")
        types = self.db.scalars(
            select(DocumentType)
            .where(DocumentType.applies_to.in_((operation.type, "BOTH")))
            .order_by(DocumentType.is_required.desc(), DocumentType.name)
        ).all()
        documents = self.db.scalars(
            select(Document).where(Document.operation_id == operation_id)
        ).all()
        by_type: dict[int, list[Document]] = {}
        for document in documents:
            by_type.setdefault(document.document_type_id, []).append(document)

        entries: list[ChecklistEntry] = []
        for doc_type in types:
            candidates = by_type.get(doc_type.id, [])
            best = max(candidates, key=lambda d: STATUS_PRIORITY.get(d.status, 0), default=None)
            status = best.status if best else "PENDING"
            expired = best is not None and best.expiry_date is not None and best.expiry_date < date.today()
            is_complete = best is not None and best.status == "APPROVED" and not expired
            if expired and status == "APPROVED":
                status = "EXPIRED"
            entries.append(
                ChecklistEntry(
                    document_type=doc_type,
                    document=best,
                    status=status,
                    is_complete=is_complete,
                    expiry_date=best.expiry_date if best else None,
                )
            )
        return entries

    def pending_count(self) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Document)
                .where(Document.status.in_(("PENDING", "REJECTED")))
            )
            or 0
        )
