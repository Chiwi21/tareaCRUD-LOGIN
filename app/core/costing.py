"""Estrategias de cálculo de costos (principio Abierto/Cerrado).

Cada tipo de cálculo vive en una clase independiente. Para agregar un nuevo
tipo (por ejemplo, un costo escalonado) basta con crear otra subclase de
``CostCalculator`` y registrarla en la fábrica, sin modificar las existentes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


class CostCalculator(ABC):
    """Contrato común para todos los cálculos de una línea de costo."""

    @abstractmethod
    def calculate(self, *, base: Decimal, quantity: Decimal, rate: Decimal) -> Decimal:
        """Devuelve el monto de la línea con dos decimales."""


class FixedCostCalculator(CostCalculator):
    def calculate(self, *, base: Decimal, quantity: Decimal, rate: Decimal) -> Decimal:
        return money(rate)


class PercentageCostCalculator(CostCalculator):
    def calculate(self, *, base: Decimal, quantity: Decimal, rate: Decimal) -> Decimal:
        return money(base * rate / Decimal("100"))


class PerUnitCostCalculator(CostCalculator):
    def calculate(self, *, base: Decimal, quantity: Decimal, rate: Decimal) -> Decimal:
        return money(quantity * rate)


class CostCalculatorFactory:
    """Fábrica de estrategias; el servicio no conoce las clases concretas."""

    _calculators: dict[str, CostCalculator] = {
        "FIXED": FixedCostCalculator(),
        "PERCENTAGE": PercentageCostCalculator(),
        "PER_UNIT": PerUnitCostCalculator(),
    }

    @classmethod
    def get(cls, calculation_type: str) -> CostCalculator:
        return cls._calculators.get(calculation_type, cls._calculators["FIXED"])

    @classmethod
    def register(cls, calculation_type: str, calculator: CostCalculator) -> None:
        cls._calculators[calculation_type] = calculator
