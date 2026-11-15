from __future__ import annotations

from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.costing import money
from app.models import (
    Carrier,
    Company,
    CostConcept,
    CostScenario,
    CostScenarioItem,
    Currency,
    Document,
    DocumentType,
    Incoterm,
    Invoice,
    Operation,
    OperationItem,
    OperationStatusHistory,
    Port,
    Product,
    Shipment,
    User,
)
from app.repositories.protocols import OperationFilters
from app.schemas import OperationCreate, OperationItemCreate, OperationUpdate


class SqlAlchemyOperationRepository:
    def __init__(self, db: Session):
        self.db = db

    def _list_options(self):
        return (
            joinedload(Operation.user),
            joinedload(Operation.company),
            joinedload(Operation.origin_port),
            joinedload(Operation.destination_port),
            joinedload(Operation.currency),
            joinedload(Operation.incoterm),
            selectinload(Operation.items).joinedload(OperationItem.product),
            selectinload(Operation.cost_scenarios),
        )

    def _detail_options(self):
        return (
            joinedload(Operation.user),
            joinedload(Operation.company),
            joinedload(Operation.origin_port),
            joinedload(Operation.destination_port),
            joinedload(Operation.currency),
            joinedload(Operation.incoterm),
            selectinload(Operation.items).joinedload(OperationItem.product),
            selectinload(Operation.status_history).joinedload(OperationStatusHistory.changed_by),
            selectinload(Operation.cost_scenarios)
            .selectinload(CostScenario.items)
            .joinedload(CostScenarioItem.concept),
            selectinload(Operation.documents).joinedload(Document.document_type),
            selectinload(Operation.invoices).selectinload(Invoice.payments),
            joinedload(Operation.shipment).joinedload(Shipment.carrier),
            selectinload(Operation.alerts),
        )

    def list(self, filters: OperationFilters | None = None):
        stmt = select(Operation).options(*self._list_options())
        if filters:
            if filters.q:
                like = f"%{filters.q.strip()}%"
                stmt = stmt.where(
                    or_(
                        Operation.code.ilike(like),
                        Operation.notes.ilike(like),
                        Operation.company.has(Company.name.ilike(like)),
                        Operation.user.has(User.username.ilike(like)),
                    )
                )
            if filters.status:
                stmt = stmt.where(Operation.status == filters.status)
            if filters.type:
                stmt = stmt.where(Operation.type == filters.type)
            if filters.company_id:
                stmt = stmt.where(Operation.company_id == filters.company_id)
        stmt = stmt.order_by(Operation.id.desc())
        return self.db.scalars(stmt).unique().all()

    def get(self, operation_id: int) -> Operation | None:
        stmt = (
            select(Operation)
            .where(Operation.id == operation_id)
            .options(*self._detail_options())
        )
        return self.db.scalars(stmt).unique().first()

    def get_by_code(self, code: str) -> Operation | None:
        stmt = select(Operation).where(Operation.code == code)
        return self.db.scalars(stmt).first()

    def create(self, data: OperationCreate, changed_by_id: int | None = None) -> Operation:
        operation = Operation(
            code=f"TMP-{uuid4().hex[:12]}",
            type=data.type,
            company_id=data.company_id,
            user_id=data.user_id,
            operation_date=data.operation_date,
            origin_port_id=data.origin_port_id,
            destination_port_id=data.destination_port_id,
            currency_id=data.currency_id,
            incoterm_id=data.incoterm_id,
            status=data.status,
            notes=data.notes,
        )
        self.db.add(operation)
        self.db.flush()
        operation.code = f"OP-{operation.operation_date.year}-{operation.id:04d}"
        for item_data in data.items:
            product = self.db.get(Product, item_data.product_id)
            if product is None:
                raise ValueError("El producto seleccionado no existe.")
            subtotal = money(item_data.quantity * item_data.unit_price)
            operation.items.append(
                OperationItem(
                    product_id=product.id,
                    description=item_data.description,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    subtotal=subtotal,
                )
            )
        self.db.add(
            OperationStatusHistory(
                operation_id=operation.id,
                from_status=None,
                to_status=operation.status,
                changed_by_id=changed_by_id,
                note="Operación creada",
            )
        )
        self.db.commit()
        return self.get(operation.id) or operation

    def update(
        self, operation_id: int, data: OperationUpdate, changed_by_id: int | None = None
    ) -> Operation:
        operation = self.db.get(Operation, operation_id)
        if operation is None:
            raise ValueError("Operación no encontrada.")
        fields = data.model_fields_set
        for field in (
            "type",
            "company_id",
            "user_id",
            "operation_date",
            "origin_port_id",
            "destination_port_id",
            "currency_id",
            "incoterm_id",
            "notes",
        ):
            if field in fields:
                setattr(operation, field, getattr(data, field))
        if "status" in fields and data.status and data.status != operation.status:
            self._add_status_history(
                operation, data.status, changed_by_id, "Cambio de estado desde edición"
            )
            operation.status = data.status
        if data.items is not None:
            for item in list(operation.items):
                self.db.delete(item)
            operation.items.clear()
            for item_data in data.items:
                product = self.db.get(Product, item_data.product_id)
                if product is None:
                    raise ValueError("El producto seleccionado no existe.")
                operation.items.append(
                    OperationItem(
                        product_id=product.id,
                        description=item_data.description,
                        quantity=item_data.quantity,
                        unit_price=item_data.unit_price,
                        subtotal=money(item_data.quantity * item_data.unit_price),
                    )
                )
        self.db.commit()
        return self.get(operation.id) or operation

    def delete(self, operation_id: int) -> None:
        operation = self.db.get(Operation, operation_id)
        if operation is None:
            raise ValueError("Operación no encontrada.")
        self.db.delete(operation)
        self.db.commit()

    def add_item(self, operation_id: int, data: OperationItemCreate) -> OperationItem:
        operation = self.db.get(Operation, operation_id)
        if operation is None:
            raise ValueError("Operación no encontrada.")
        product = self.db.get(Product, data.product_id)
        if product is None:
            raise ValueError("El producto seleccionado no existe.")
        item = OperationItem(
            operation_id=operation.id,
            product_id=product.id,
            description=data.description,
            quantity=data.quantity,
            unit_price=data.unit_price,
            subtotal=money(data.quantity * data.unit_price),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(self, operation_id: int, item_id: int) -> None:
        item = self.db.get(OperationItem, item_id)
        if item is None or item.operation_id != operation_id:
            raise ValueError("Ítem no encontrado.")
        self.db.delete(item)
        self.db.commit()

    def change_status(
        self,
        operation_id: int,
        new_status: str,
        changed_by_id: int | None,
        note: str | None = None,
    ) -> Operation:
        operation = self.db.get(Operation, operation_id)
        if operation is None:
            raise ValueError("Operación no encontrada.")
        if operation.status != new_status:
            self._add_status_history(operation, new_status, changed_by_id, note)
            operation.status = new_status
            self.db.commit()
        return self.get(operation.id) or operation

    def _add_status_history(
        self,
        operation: Operation,
        new_status: str,
        changed_by_id: int | None,
        note: str | None,
    ) -> None:
        self.db.add(
            OperationStatusHistory(
                operation_id=operation.id,
                from_status=operation.status,
                to_status=new_status,
                changed_by_id=changed_by_id,
                note=note,
            )
        )

    def list_assignable_users(self):
        return self.db.scalars(
            select(User)
            .where(User.role.in_(("IMPORTER", "EXPORTER")), User.is_active.is_(True))
            .order_by(User.username)
        ).all()

    def list_companies(self):
        return self.db.scalars(
            select(Company).where(Company.is_active.is_(True)).order_by(Company.name)
        ).all()

    def list_ports(self):
        return self.db.scalars(
            select(Port).options(joinedload(Port.country)).order_by(Port.name)
        ).unique().all()

    def list_currencies(self):
        return self.db.scalars(select(Currency).order_by(Currency.code)).all()

    def list_incoterms(self):
        return self.db.scalars(select(Incoterm).order_by(Incoterm.code)).all()

    def list_products(self):
        return self.db.scalars(
            select(Product)
            .where(Product.is_active.is_(True))
            .options(joinedload(Product.category))
            .order_by(Product.name)
        ).unique().all()

    def list_document_types(self):
        return self.db.scalars(select(DocumentType).order_by(DocumentType.name)).all()

    def list_carriers(self):
        return self.db.scalars(
            select(Carrier).where(Carrier.is_active.is_(True)).order_by(Carrier.name)
        ).all()

    def list_cost_concepts(self):
        return self.db.scalars(
            select(CostConcept)
            .where(CostConcept.is_active.is_(True))
            .order_by(CostConcept.category, CostConcept.name)
        ).all()

    def list_for_user(self, user_id: int):
        return self.db.scalars(
            select(Operation)
            .where(Operation.user_id == user_id)
            .options(*self._list_options())
            .order_by(Operation.id.desc())
        ).unique().all()
