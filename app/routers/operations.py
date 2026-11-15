from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.constants import OPERATION_STATUS_FLOW, ROLE_ADMIN
from app.dependencies import (
    get_cost_service,
    get_document_service,
    get_operation_service,
)
from app.flash import flash
from app.models import User
from app.repositories.protocols import OperationFilters
from app.schemas import (
    OperationCreate,
    OperationItemCreate,
    OperationItemOut,
    OperationOut,
    OperationUpdate,
    StatusChange,
)
from app.security import require_admin, require_login
from app.services.cost_service import CostService
from app.services.document_service import DocumentService
from app.services.errors import NotFoundError, ValidationError
from app.services.operation_service import OperationService
from app.templating import templates

router = APIRouter(tags=["operations"])

FORM_FIELDS = (
    "type",
    "company_id",
    "user_id",
    "operation_date",
    "origin_port_id",
    "destination_port_id",
    "currency_id",
    "incoterm_id",
    "status",
    "notes",
)


def _optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _form_values(form) -> dict:
    return {field: form.get(field, "") or "" for field in FORM_FIELDS}


def _operation_create(form) -> OperationCreate:
    operation_date = form.get("operation_date") or date.today().isoformat()
    return OperationCreate(
        type=form.get("type", ""),
        company_id=_optional_int(form.get("company_id")),
        user_id=_optional_int(form.get("user_id")),
        operation_date=date.fromisoformat(operation_date),
        origin_port_id=_optional_int(form.get("origin_port_id")),
        destination_port_id=_optional_int(form.get("destination_port_id")),
        currency_id=_optional_int(form.get("currency_id")),
        incoterm_id=_optional_int(form.get("incoterm_id")),
        status=form.get("status") or "PENDING",
        notes=form.get("notes") or None,
        items=[],
    )


def _operation_update(form) -> OperationUpdate:
    operation_date = form.get("operation_date") or date.today().isoformat()
    return OperationUpdate(
        type=form.get("type", ""),
        company_id=_optional_int(form.get("company_id")),
        user_id=_optional_int(form.get("user_id")),
        operation_date=date.fromisoformat(operation_date),
        origin_port_id=_optional_int(form.get("origin_port_id")),
        destination_port_id=_optional_int(form.get("destination_port_id")),
        currency_id=_optional_int(form.get("currency_id")),
        incoterm_id=_optional_int(form.get("incoterm_id")),
        status=form.get("status") or "PENDING",
        notes=form.get("notes") or None,
    )


def _operation_out(operation) -> OperationOut:
    selected = operation.selected_scenario
    return OperationOut(
        id=operation.id,
        code=operation.code,
        type=operation.type,
        status=operation.status,
        operation_date=operation.operation_date,
        company_name=operation.company.name if operation.company else None,
        user_name=operation.user.username if operation.user else None,
        origin_port=(
            f"{operation.origin_port.name} ({operation.origin_port.code})"
            if operation.origin_port
            else None
        ),
        destination_port=(
            f"{operation.destination_port.name} ({operation.destination_port.code})"
            if operation.destination_port
            else None
        ),
        currency=operation.currency.code if operation.currency else None,
        incoterm=operation.incoterm.code if operation.incoterm else None,
        product_subtotal=operation.product_subtotal,
        selected_scenario_total=selected.total if selected else None,
        items=[
            OperationItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
            for item in operation.items
        ],
        created_at=operation.created_at.isoformat() if operation.created_at else None,
    )


def _render_form(
    request: Request,
    user: User,
    service: OperationService,
    values: dict,
    errors: list[str],
    operation=None,
):
    context = service.form_context()
    return templates.TemplateResponse(
        request,
        "operations/form.html",
        {
            "user": user,
            "values": values,
            "errors": errors,
            "operation": operation,
            "is_edit": operation is not None,
            "title": "Editar operación" if operation else "Nueva operación",
            "action_url": f"/operations/{operation.id}/edit" if operation else "/operations/new",
            "cancel_url": f"/operations/{operation.id}" if operation else "/operations",
            **context,
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


def _get_for_user(service: OperationService, operation_id: int, user: User):
    operation = service.get(operation_id)
    if user.role != ROLE_ADMIN and operation.user_id != user.id:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta operación")
    return operation


@router.get("/operations")
def list_operations(
    request: Request,
    q: str = "",
    status_filter: str = Query("", alias="status"),
    type_filter: str = Query("", alias="type"),
    company_id: int | None = None,
    user: User = Depends(require_login),
    service: OperationService = Depends(get_operation_service),
):
    if user.role == ROLE_ADMIN:
        operations = service.list(
            OperationFilters(q=q, status=status_filter, type=type_filter, company_id=company_id)
        )
    else:
        operations = service.list_for_user(user.id)
    return templates.TemplateResponse(
        request,
        "operations/list.html",
        {
            "user": user,
            "operations": operations,
            "companies": service.form_context()["companies"],
            "q": q,
            "status_filter": status_filter,
            "type_filter": type_filter,
            "company_id": company_id or "",
            "is_admin": user.role == ROLE_ADMIN,
        },
    )


@router.get("/operations/new")
def new_operation_form(
    request: Request,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    return _render_form(
        request, user, service, {"status": "PENDING", "operation_date": date.today().isoformat()}, []
    )


@router.post("/operations/new")
async def create_operation(
    request: Request,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    form = await request.form()
    values = _form_values(form)
    try:
        data = _operation_create(form)
    except (ValueError, PydanticValidationError):
        return _render_form(request, user, service, values, ["Revise los datos del formulario."])
    try:
        operation = service.create(data, user.id)
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors)
    flash(request, f"Operación {operation.code} creada correctamente.", "success")
    return RedirectResponse(f"/operations/{operation.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/operations/{operation_id}")
def operation_detail(
    request: Request,
    operation_id: int,
    user: User = Depends(require_login),
    service: OperationService = Depends(get_operation_service),
    cost_service: CostService = Depends(get_cost_service),
    document_service: DocumentService = Depends(get_document_service),
):
    operation = _get_for_user(service, operation_id, user)
    context = service.form_context()
    checklist = document_service.checklist(operation.id)
    comparison = cost_service.compare(operation.id)
    return templates.TemplateResponse(
        request,
        "operations/detail.html",
        {
            "user": user,
            "operation": operation,
            "is_admin": user.role == ROLE_ADMIN,
            "checklist": checklist,
            "comparison": comparison,
            "savings": cost_service.savings(operation.id),
            "approved_documents": sum(1 for entry in checklist if entry.is_complete),
            "open_alerts": [alert for alert in operation.alerts if alert.status == "OPEN"],
            "status_options": OPERATION_STATUS_FLOW.get(operation.status, ()),
            **context,
        },
    )


@router.get("/operations/{operation_id}/edit")
def edit_operation_form(
    request: Request,
    operation_id: int,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    operation = service.get(operation_id)
    values = {
        "type": operation.type,
        "company_id": operation.company_id or "",
        "user_id": operation.user_id or "",
        "operation_date": operation.operation_date.isoformat(),
        "origin_port_id": operation.origin_port_id or "",
        "destination_port_id": operation.destination_port_id or "",
        "currency_id": operation.currency_id or "",
        "incoterm_id": operation.incoterm_id or "",
        "status": operation.status,
        "notes": operation.notes or "",
    }
    return _render_form(request, user, service, values, [], operation)


@router.post("/operations/{operation_id}/edit")
async def update_operation(
    request: Request,
    operation_id: int,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    operation = service.get(operation_id)
    form = await request.form()
    values = _form_values(form)
    try:
        data = _operation_update(form)
    except (ValueError, PydanticValidationError):
        return _render_form(
            request, user, service, values, ["Revise los datos del formulario."], operation
        )
    try:
        updated = service.update(operation_id, data, user.id)
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors, operation)
    flash(request, f"Operación {updated.code} actualizada correctamente.", "success")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/operations/{operation_id}/delete")
def delete_operation(
    request: Request,
    operation_id: int,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        service.delete(operation_id, user.id)
    except NotFoundError:
        flash(request, "Operación no encontrada.", "error")
    else:
        flash(request, "Operación eliminada correctamente.", "success")
    return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/operations/{operation_id}/items")
async def add_item(
    request: Request,
    operation_id: int,
    product_id: int = Form(...),
    quantity: str = Form(...),
    unit_price: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        item = OperationItemCreate(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            description=description or None,
        )
        service.add_item(operation_id, item, user.id)
        flash(request, "Producto agregado a la operación.", "success")
    except (ValidationError, ValueError) as exc:
        message = exc.errors[0] if isinstance(exc, ValidationError) else str(exc)
        flash(request, message, "error")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/operations/{operation_id}/items/{item_id}/delete")
def remove_item(
    request: Request,
    operation_id: int,
    item_id: int,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        service.remove_item(operation_id, item_id, user.id)
        flash(request, "Ítem eliminado.", "success")
    except (ValidationError, ValueError) as exc:
        message = exc.errors[0] if isinstance(exc, ValidationError) else str(exc)
        flash(request, message, "error")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/operations/{operation_id}/status")
def change_status(
    request: Request,
    operation_id: int,
    new_status: str = Form(..., alias="status"),
    note: str = Form(""),
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        service.change_status(operation_id, new_status, user.id, note or None)
        flash(request, "Estado de la operación actualizado.", "success")
    except (ValidationError, NotFoundError) as exc:
        message = exc.errors[0] if isinstance(exc, ValidationError) else str(exc)
        flash(request, message, "error")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@router.get("/api/operations", response_model=list[OperationOut])
def api_list_operations(
    q: str = "",
    status_filter: str = Query("", alias="status"),
    type_filter: str = Query("", alias="type"),
    user: User = Depends(require_login),
    service: OperationService = Depends(get_operation_service),
):
    if user.role == ROLE_ADMIN:
        operations = service.list(OperationFilters(q=q, status=status_filter, type=type_filter))
    else:
        operations = service.list_for_user(user.id)
    return [_operation_out(operation) for operation in operations]


@router.get("/api/operations/{operation_id}", response_model=OperationOut)
def api_operation_detail(
    operation_id: int,
    user: User = Depends(require_login),
    service: OperationService = Depends(get_operation_service),
):
    return _operation_out(_get_for_user(service, operation_id, user))


@router.post("/api/operations", response_model=OperationOut)
def api_create_operation(
    payload: OperationCreate,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        operation = service.create(payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _operation_out(operation)


@router.put("/api/operations/{operation_id}", response_model=OperationOut)
def api_update_operation(
    operation_id: int,
    payload: OperationUpdate,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        operation = service.update(operation_id, payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _operation_out(operation)


@router.delete("/api/operations/{operation_id}")
def api_delete_operation(
    operation_id: int,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        service.delete(operation_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Operación eliminada correctamente", "id": operation_id}


@router.post("/api/operations/{operation_id}/items", response_model=OperationItemOut)
def api_add_item(
    operation_id: int,
    payload: OperationItemCreate,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        item = service.add_item(operation_id, payload, user.id)
    except (ValidationError, NotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OperationItemOut(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product.name,
        description=item.description,
        quantity=item.quantity,
        unit_price=item.unit_price,
        subtotal=item.subtotal,
    )


@router.delete("/api/operations/{operation_id}/items/{item_id}")
def api_remove_item(
    operation_id: int,
    item_id: int,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        service.remove_item(operation_id, item_id, user.id)
    except (ValidationError, NotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"detail": "Ítem eliminado correctamente", "id": item_id}


@router.post("/api/operations/{operation_id}/status", response_model=OperationOut)
def api_change_status(
    operation_id: int,
    payload: StatusChange,
    user: User = Depends(require_admin),
    service: OperationService = Depends(get_operation_service),
):
    try:
        operation = service.change_status(operation_id, payload.status, user.id, payload.note)
    except (ValidationError, NotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _operation_out(operation)
