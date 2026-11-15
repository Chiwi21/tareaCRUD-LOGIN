from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import CostConcept, CostScenario, CostScenarioItem, OperationItem
from app.schemas import CostScenarioItemCreate


class SqlAlchemyCostRepository:
    def __init__(self, db: Session):
        self.db = db

    def _options(self):
        return selectinload(CostScenario.items).joinedload(CostScenarioItem.concept)

    def list_by_operation(self, operation_id: int):
        return self.db.scalars(
            select(CostScenario)
            .where(CostScenario.operation_id == operation_id)
            .options(self._options())
            .order_by(CostScenario.id)
        ).unique().all()

    def get(self, scenario_id: int) -> CostScenario | None:
        return self.db.scalars(
            select(CostScenario)
            .where(CostScenario.id == scenario_id)
            .options(self._options())
        ).unique().first()

    def create(self, operation_id: int, name: str, description: str | None) -> CostScenario:
        scenario = CostScenario(
            operation_id=operation_id, name=name.strip(), description=description
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def add_item(
        self,
        scenario_id: int,
        data: CostScenarioItemCreate,
        amount: Decimal,
        sort_order: int,
    ) -> CostScenario:
        scenario = self.db.get(CostScenario, scenario_id)
        if scenario is None:
            raise ValueError("Escenario no encontrado.")
        concept = self.db.get(CostConcept, data.concept_id)
        if concept is None:
            raise ValueError("Concepto de costo no encontrado.")
        self.db.add(
            CostScenarioItem(
                scenario_id=scenario.id,
                concept_id=concept.id,
                description=data.description or concept.name,
                calculation_type=data.calculation_type,
                rate=data.rate,
                quantity=data.quantity,
                base_amount=data.base_amount,
                amount=amount,
                sort_order=sort_order,
            )
        )
        self.db.commit()
        return self.get(scenario.id) or scenario

    def delete_item(self, item_id: int) -> CostScenario | None:
        item = self.db.get(CostScenarioItem, item_id)
        if item is None:
            return None
        scenario_id = item.scenario_id
        self.db.delete(item)
        self.db.commit()
        return self.get(scenario_id)

    def select(self, scenario_id: int) -> CostScenario:
        scenario = self.db.get(CostScenario, scenario_id)
        if scenario is None:
            raise ValueError("Escenario no encontrado.")
        self.db.execute(
            update(CostScenario)
            .where(CostScenario.operation_id == scenario.operation_id)
            .values(is_selected=False)
        )
        scenario.is_selected = True
        self.db.commit()
        return self.get(scenario.id) or scenario

    def delete(self, scenario_id: int) -> None:
        scenario = self.db.get(CostScenario, scenario_id)
        if scenario is None:
            raise ValueError("Escenario no encontrado.")
        self.db.delete(scenario)
        self.db.commit()

    def product_subtotal(self, operation_id: int) -> Decimal:
        value = self.db.scalar(
            select(func.coalesce(func.sum(OperationItem.subtotal), 0)).where(
                OperationItem.operation_id == operation_id
            )
        )
        return Decimal(str(value or 0))
