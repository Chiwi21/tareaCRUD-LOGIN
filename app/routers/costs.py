from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.dependencies import get_cost_service
from app.flash import flash
from app.models import User
from app.schemas import (
    CostScenarioCreate,
    CostScenarioItemCreate,
    CostScenarioItemOut,
    CostScenarioOut,
    ScenarioComparisonOut,
)
from app.security import require_admin
from app.services.cost_service import CostService
from app.templating import templates

router = APIRouter(tags=["costs"])


def _scenario_out(scenario) -> CostScenarioOut:
    return CostScenarioOut(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        is_selected=scenario.is_selected,
        total=scenario.total,
        items=[
            CostScenarioItemOut(
                id=item.id,
                concept_id=item.concept_id,
                concept_name=item.concept.name if item.concept else "",
                description=item.description,
                calculation_type=item.calculation_type,
                rate=item.rate,
                quantity=item.quantity,
                base_amount=item.base_amount,
                amount=item.amount,
            )
            for item in scenario.items
        ],
    )


@router.post("/operations/{operation_id}/scenarios")
def create_scenario(
    request: Request,
    operation_id: int,
    name: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    try:
        if len(name.strip()) < 2:
            raise ValueError("El nombre del escenario es obligatorio.")
        service.create_scenario(operation_id, name.strip(), description.strip() or None)
        flash(request, "Escenario de costo creado.", "success")
    except ValueError as exc:
        flash(request, str(exc), "error")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/scenarios/{scenario_id}/items")
def add_scenario_item(
    request: Request,
    scenario_id: int,
    concept_id: int = Form(...),
    description: str = Form(""),
    calculation_type: str = Form(...),
    rate: str = Form(...),
    quantity: str = Form("1"),
    base_amount: str = Form("0"),
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    scenario = service.get(scenario_id)
    if scenario is None:
        flash(request, "Escenario no encontrado.", "error")
        return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)
    try:
        data = CostScenarioItemCreate(
            concept_id=concept_id,
            description=description or None,
            calculation_type=calculation_type,
            rate=Decimal(rate),
            quantity=Decimal(quantity),
            base_amount=Decimal(base_amount or "0"),
        )
        service.add_line(scenario_id, data)
        flash(request, "Línea de costo agregada.", "success")
    except (PydanticValidationError, InvalidOperation, ValueError) as exc:
        flash(request, "Revise el concepto, la tasa y la cantidad.", "error")
    return RedirectResponse(
        f"/operations/{scenario.operation_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/scenarios/{scenario_id}/select")
def select_scenario(
    request: Request,
    scenario_id: int,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    scenario = service.get(scenario_id)
    if scenario is None:
        flash(request, "Escenario no encontrado.", "error")
        return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)
    service.select(scenario_id)
    flash(request, f"Escenario '{scenario.name}' seleccionado.", "success")
    return RedirectResponse(
        f"/operations/{scenario.operation_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/scenarios/{scenario_id}/delete")
def delete_scenario(
    request: Request,
    scenario_id: int,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    scenario = service.get(scenario_id)
    if scenario is None:
        flash(request, "Escenario no encontrado.", "error")
        return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)
    operation_id = scenario.operation_id
    service.delete(scenario_id)
    flash(request, "Escenario eliminado.", "success")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/scenario-items/{item_id}/delete")
def delete_scenario_item(
    request: Request,
    item_id: int,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    scenario = service.delete_item(item_id)
    if scenario is None:
        flash(request, "Línea de costo no encontrada.", "error")
        return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)
    flash(request, "Línea de costo eliminada.", "success")
    return RedirectResponse(
        f"/operations/{scenario.operation_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/api/operations/{operation_id}/scenarios", response_model=ScenarioComparisonOut)
def api_scenarios(
    operation_id: int,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    comparison = service.compare(operation_id)
    return ScenarioComparisonOut(
        operation_id=operation_id,
        product_subtotal=comparison["product_subtotal"],
        scenarios=[_scenario_out(scenario) for scenario in comparison["scenarios"]],
        best_scenario_id=comparison["best"].id if comparison["best"] else None,
        best_total=comparison["best_total"],
    )


@router.post("/api/operations/{operation_id}/scenarios", response_model=CostScenarioOut)
def api_create_scenario(
    operation_id: int,
    payload: CostScenarioCreate,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    scenario = service.create_scenario(operation_id, payload.name, payload.description)
    for item in payload.items:
        service.add_line(scenario.id, item)
    updated = service.get(scenario.id)
    return _scenario_out(updated)


@router.post("/api/scenarios/{scenario_id}/select", response_model=CostScenarioOut)
def api_select_scenario(
    scenario_id: int,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    scenario = service.select(scenario_id)
    return _scenario_out(scenario)


@router.delete("/api/scenarios/{scenario_id}")
def api_delete_scenario(
    scenario_id: int,
    user: User = Depends(require_admin),
    service: CostService = Depends(get_cost_service),
):
    if service.get(scenario_id) is None:
        raise HTTPException(status_code=404, detail="Escenario no encontrado")
    service.delete(scenario_id)
    return {"detail": "Escenario eliminado correctamente", "id": scenario_id}
