from __future__ import annotations

from decimal import Decimal

from app.core.costing import CostCalculatorFactory, money
from app.repositories.protocols import CostRepository
from app.schemas import CostScenarioItemCreate


class CostService:
    """Orquesta los escenarios de costo y aplica las estrategias de cálculo."""

    def __init__(self, repository: CostRepository):
        self.repository = repository

    def calculate_amount(
        self,
        calculation_type: str,
        base: Decimal,
        quantity: Decimal,
        rate: Decimal,
    ) -> Decimal:
        calculator = CostCalculatorFactory.get(calculation_type)
        return calculator.calculate(base=base, quantity=quantity, rate=rate)

    def list_scenarios(self, operation_id: int):
        return self.repository.list_by_operation(operation_id)

    def get(self, scenario_id: int):
        return self.repository.get(scenario_id)

    def compare(self, operation_id: int) -> dict:
        scenarios = list(self.repository.list_by_operation(operation_id))
        best = min(scenarios, key=lambda scenario: scenario.total, default=None)
        return {
            "product_subtotal": self.repository.product_subtotal(operation_id),
            "scenarios": scenarios,
            "best": best,
            "best_total": best.total if best else None,
        }

    def create_scenario(self, operation_id: int, name: str, description: str | None = None):
        return self.repository.create(operation_id, name, description)

    def add_line(self, scenario_id: int, data: CostScenarioItemCreate):
        scenario = self.repository.get(scenario_id)
        if scenario is None:
            raise ValueError("Escenario no encontrado.")
        base = data.base_amount
        if base == 0 and data.calculation_type == "PERCENTAGE":
            base = self.repository.product_subtotal(scenario.operation_id)
        amount = self.calculate_amount(
            data.calculation_type, base=base, quantity=data.quantity, rate=data.rate
        )
        data = data.model_copy(update={"base_amount": base})
        return self.repository.add_item(
            scenario_id, data, amount, sort_order=len(scenario.items)
        )

    def select(self, scenario_id: int):
        return self.repository.select(scenario_id)

    def delete(self, scenario_id: int) -> None:
        self.repository.delete(scenario_id)

    def delete_item(self, item_id: int):
        return self.repository.delete_item(item_id)

    def savings(self, operation_id: int) -> Decimal:
        scenarios = list(self.repository.list_by_operation(operation_id))
        if len(scenarios) < 2:
            return Decimal("0")
        totals = sorted(scenario.total for scenario in scenarios)
        return money(totals[-1] - totals[0])
