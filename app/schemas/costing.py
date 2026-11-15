from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CostScenarioItemCreate(BaseModel):
    concept_id: int
    description: str | None = Field(default=None, max_length=200)
    calculation_type: str = Field(pattern="^(FIXED|PERCENTAGE|PER_UNIT)$")
    rate: Decimal = Field(ge=0)
    quantity: Decimal = Field(gt=0, default=1)
    base_amount: Decimal = Field(ge=0, default=0)


class CostScenarioCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    items: list[CostScenarioItemCreate] = Field(default_factory=list)


class CostScenarioItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    concept_id: int
    concept_name: str
    description: str | None = None
    calculation_type: str
    rate: Decimal
    quantity: Decimal
    base_amount: Decimal
    amount: Decimal


class CostScenarioOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_selected: bool
    total: Decimal
    items: list[CostScenarioItemOut] = Field(default_factory=list)


class ScenarioComparisonOut(BaseModel):
    operation_id: int
    product_subtotal: Decimal
    scenarios: list[CostScenarioOut]
    best_scenario_id: int | None = None
    best_total: Decimal | None = None
