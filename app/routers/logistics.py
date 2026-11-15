from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.dependencies import get_logistics_service
from app.flash import flash
from app.models import User
from app.schemas import ShipmentCreate, ShipmentOut, ShipmentUpdate
from app.security import require_admin
from app.services.errors import NotFoundError, ValidationError
from app.services.logistics_service import LogisticsService
from app.templating import templates

router = APIRouter(tags=["logistics"])


def _date_or_none(value: str | None):
    return date.fromisoformat(value) if value else None


def _int_or_none(value: str | None):
    return int(value) if value else None


def _shipment_out(shipment) -> ShipmentOut:
    return ShipmentOut(
        id=shipment.id,
        operation_id=shipment.operation_id,
        operation_code=shipment.operation.code if shipment.operation else "",
        carrier_name=shipment.carrier.name if shipment.carrier else None,
        tracking_number=shipment.tracking_number,
        origin_port=shipment.origin_port.name if shipment.origin_port else None,
        destination_port=(
            shipment.destination_port.name if shipment.destination_port else None
        ),
        departure_date=shipment.departure_date,
        estimated_arrival=shipment.estimated_arrival,
        actual_arrival=shipment.actual_arrival,
        status=shipment.status,
        notes=shipment.notes,
    )


def _render_form(
    request: Request,
    user: User,
    service: LogisticsService,
    values: dict,
    errors: list[str],
    shipment=None,
):
    context = service.form_context()
    return templates.TemplateResponse(
        request,
        "shipments/form.html",
        {
            "user": user,
            "values": values,
            "errors": errors,
            "shipment": shipment,
            "is_edit": shipment is not None,
            "title": "Editar embarque" if shipment else "Nuevo embarque",
            "action_url": f"/shipments/{shipment.id}/edit" if shipment else "/shipments/new",
            "cancel_url": f"/operations/{shipment.operation_id}" if shipment else "/shipments",
            **context,
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


@router.get("/shipments")
def list_shipments(
    request: Request,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    return templates.TemplateResponse(
        request, "shipments/list.html", {"user": user, "shipments": service.list()}
    )


@router.get("/shipments/new")
def new_shipment_form(
    request: Request,
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    values = {
        "operation_id": operation_id or "",
        "status": "PENDING",
        "departure_date": date.today().isoformat(),
        "estimated_arrival": "",
    }
    return _render_form(request, user, service, values, [])


@router.post("/shipments/new")
async def create_shipment(
    request: Request,
    operation_id: int = Form(...),
    carrier_id: str = Form(""),
    tracking_number: str = Form(""),
    origin_port_id: str = Form(""),
    destination_port_id: str = Form(""),
    departure_date: str = Form(""),
    estimated_arrival: str = Form(""),
    actual_arrival: str = Form(""),
    status_value: str = Form("PENDING", alias="status"),
    notes: str = Form(""),
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    values = {
        "operation_id": operation_id,
        "carrier_id": carrier_id,
        "tracking_number": tracking_number,
        "origin_port_id": origin_port_id,
        "destination_port_id": destination_port_id,
        "departure_date": departure_date,
        "estimated_arrival": estimated_arrival,
        "actual_arrival": actual_arrival,
        "status": status_value,
        "notes": notes,
    }
    try:
        data = ShipmentCreate(
            operation_id=operation_id,
            carrier_id=_int_or_none(carrier_id),
            tracking_number=tracking_number or None,
            origin_port_id=_int_or_none(origin_port_id),
            destination_port_id=_int_or_none(destination_port_id),
            departure_date=_date_or_none(departure_date),
            estimated_arrival=_date_or_none(estimated_arrival),
            actual_arrival=_date_or_none(actual_arrival),
            status=status_value,
            notes=notes or None,
        )
        service.create(data, user.id)
    except (ValueError, PydanticValidationError):
        return _render_form(request, user, service, values, ["Revise las fechas del embarque."])
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors)
    flash(request, "Embarque registrado correctamente.", "success")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/shipments/{shipment_id}/edit")
def edit_shipment_form(
    request: Request,
    shipment_id: int,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    shipment = service.get(shipment_id)
    values = {
        "operation_id": shipment.operation_id,
        "carrier_id": shipment.carrier_id or "",
        "tracking_number": shipment.tracking_number or "",
        "origin_port_id": shipment.origin_port_id or "",
        "destination_port_id": shipment.destination_port_id or "",
        "departure_date": shipment.departure_date.isoformat() if shipment.departure_date else "",
        "estimated_arrival": (
            shipment.estimated_arrival.isoformat() if shipment.estimated_arrival else ""
        ),
        "actual_arrival": shipment.actual_arrival.isoformat() if shipment.actual_arrival else "",
        "status": shipment.status,
        "notes": shipment.notes or "",
    }
    return _render_form(request, user, service, values, [], shipment)


@router.post("/shipments/{shipment_id}/edit")
async def update_shipment(
    request: Request,
    shipment_id: int,
    carrier_id: str = Form(""),
    tracking_number: str = Form(""),
    origin_port_id: str = Form(""),
    destination_port_id: str = Form(""),
    departure_date: str = Form(""),
    estimated_arrival: str = Form(""),
    actual_arrival: str = Form(""),
    status_value: str = Form(..., alias="status"),
    notes: str = Form(""),
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    shipment = service.get(shipment_id)
    values = {
        "operation_id": shipment.operation_id,
        "carrier_id": carrier_id,
        "tracking_number": tracking_number,
        "origin_port_id": origin_port_id,
        "destination_port_id": destination_port_id,
        "departure_date": departure_date,
        "estimated_arrival": estimated_arrival,
        "actual_arrival": actual_arrival,
        "status": status_value,
        "notes": notes,
    }
    try:
        data = ShipmentUpdate(
            carrier_id=_int_or_none(carrier_id),
            tracking_number=tracking_number or None,
            origin_port_id=_int_or_none(origin_port_id),
            destination_port_id=_int_or_none(destination_port_id),
            departure_date=_date_or_none(departure_date),
            estimated_arrival=_date_or_none(estimated_arrival),
            actual_arrival=_date_or_none(actual_arrival),
            status=status_value,
            notes=notes or None,
        )
        service.update(shipment_id, data, user.id)
    except (ValueError, PydanticValidationError):
        return _render_form(request, user, service, values, ["Revise las fechas del embarque."], shipment)
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors, shipment)
    flash(request, "Embarque actualizado correctamente.", "success")
    return RedirectResponse(f"/operations/{shipment.operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/shipments/{shipment_id}/delete")
def delete_shipment(
    request: Request,
    shipment_id: int,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    shipment = service.get(shipment_id)
    operation_id = shipment.operation_id
    service.delete(shipment_id, user.id)
    flash(request, "Embarque eliminado.", "success")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/shipments", response_model=list[ShipmentOut])
def api_list_shipments(
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    return [_shipment_out(shipment) for shipment in service.list()]


@router.get("/api/shipments/{shipment_id}", response_model=ShipmentOut)
def api_shipment_detail(
    shipment_id: int,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    return _shipment_out(service.get(shipment_id))


@router.post("/api/shipments", response_model=ShipmentOut)
def api_create_shipment(
    payload: ShipmentCreate,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    try:
        shipment = service.create(payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _shipment_out(shipment)


@router.put("/api/shipments/{shipment_id}", response_model=ShipmentOut)
def api_update_shipment(
    shipment_id: int,
    payload: ShipmentUpdate,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    try:
        shipment = service.update(shipment_id, payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _shipment_out(shipment)


@router.delete("/api/shipments/{shipment_id}")
def api_delete_shipment(
    shipment_id: int,
    user: User = Depends(require_admin),
    service: LogisticsService = Depends(get_logistics_service),
):
    try:
        service.delete(shipment_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Embarque eliminado correctamente", "id": shipment_id}
