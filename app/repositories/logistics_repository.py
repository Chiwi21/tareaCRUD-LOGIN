from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Carrier, Operation, Shipment
from app.schemas import ShipmentCreate, ShipmentUpdate


class SqlAlchemyLogisticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def _options(self):
        return (
            joinedload(Shipment.carrier),
            joinedload(Shipment.operation),
            joinedload(Shipment.origin_port),
            joinedload(Shipment.destination_port),
        )

    def list(self):
        return self.db.scalars(
            select(Shipment).options(*self._options()).order_by(Shipment.id.desc())
        ).unique().all()

    def get(self, shipment_id: int) -> Shipment | None:
        return self.db.scalars(
            select(Shipment).where(Shipment.id == shipment_id).options(*self._options())
        ).unique().first()

    def get_by_operation(self, operation_id: int) -> Shipment | None:
        return self.db.scalars(
            select(Shipment)
            .where(Shipment.operation_id == operation_id)
            .options(*self._options())
        ).unique().first()

    def create(self, data: ShipmentCreate) -> Shipment:
        if self.db.get(Operation, data.operation_id) is None:
            raise ValueError("Operación no encontrada.")
        if self.get_by_operation(data.operation_id) is not None:
            raise ValueError("La operación ya tiene un embarque registrado.")
        if data.carrier_id and self.db.get(Carrier, data.carrier_id) is None:
            raise ValueError("Transportista no encontrado.")
        shipment = Shipment(**data.model_dump())
        self.db.add(shipment)
        self.db.commit()
        self.db.refresh(shipment)
        return shipment

    def update(self, shipment_id: int, data: ShipmentUpdate) -> Shipment:
        shipment = self.db.get(Shipment, shipment_id)
        if shipment is None:
            raise ValueError("Embarque no encontrado.")
        for field in data.model_fields_set:
            setattr(shipment, field, getattr(data, field))
        self.db.commit()
        self.db.refresh(shipment)
        return shipment

    def delete(self, shipment_id: int) -> None:
        shipment = self.db.get(Shipment, shipment_id)
        if shipment is None:
            raise ValueError("Embarque no encontrado.")
        self.db.delete(shipment)
        self.db.commit()
