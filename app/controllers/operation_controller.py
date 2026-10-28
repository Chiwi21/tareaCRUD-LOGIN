from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.constants import OPERATION_STATUSES, OPERATION_TYPES, ROLE_EXPORTER, ROLE_IMPORTER
from app.database import get_db
from app.models import Operation, User
from app.security import require_admin
from app.templating import templates

router = APIRouter(tags=["operations"])

DATE_FORMAT = "%Y-%m-%d"


def get_operation_or_404(db: Session, operation_id: int) -> Operation:
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operación no encontrada")
    return operation


def get_assignable_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.role.in_((ROLE_IMPORTER, ROLE_EXPORTER)))
        .order_by(User.username)
        .all()
    )


def validate_operation(
    type: str,
    product: str,
    quantity: str,
    country: str,
    date: str,
    op_status: str,
    selected_user_id: str,
    db: Session,
):
    errors: list[str] = []
    type = type.strip()
    product = product.strip()
    country = country.strip()
    op_status = op_status.strip()

    if type not in OPERATION_TYPES:
        errors.append("Debe seleccionar un tipo de operación válido.")
    if not product:
        errors.append("El producto es obligatorio.")

    quantity_value = None
    try:
        quantity_value = int(quantity)
        if quantity_value <= 0:
            errors.append("La cantidad debe ser mayor a 0.")
    except (TypeError, ValueError):
        errors.append("La cantidad debe ser un número entero.")

    if not country:
        errors.append("El país es obligatorio.")

    date_value = None
    try:
        date_value = datetime.strptime(date, DATE_FORMAT).date()
    except (TypeError, ValueError):
        errors.append("La fecha es inválida.")

    if op_status not in OPERATION_STATUSES:
        errors.append("Debe seleccionar un estado válido.")

    user_id = None
    try:
        user_id = int(selected_user_id)
    except (TypeError, ValueError):
        errors.append("Debe seleccionar un usuario Importador o Exportador.")
    else:
        assigned_user = db.get(User, user_id)
        if assigned_user is None or assigned_user.role not in (ROLE_IMPORTER, ROLE_EXPORTER):
            errors.append("El usuario seleccionado no existe o no puede tener operaciones asignadas.")

    return errors, type, product, quantity_value, country, date_value, op_status, user_id


def render_form(
    request: Request,
    user: User,
    action_url: str,
    title: str,
    values: dict,
    available_users: list[User],
    errors=None,
):
    return templates.TemplateResponse(
        request,
        "operations/form.html",
        {
            "user": user,
            "action_url": action_url,
            "title": title,
            "values": values,
            "available_users": available_users,
            "errors": errors or [],
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


@router.get("/operations")
def list_operations(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    operations = db.query(Operation).order_by(Operation.id.desc()).all()
    return templates.TemplateResponse(request, "operations/list.html", {"user": user, "operations": operations})


@router.get("/operations/new")
def new_operation_form(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return render_form(
        request,
        user,
        "/operations/new",
        "Nueva operación",
        {},
        get_assignable_users(db),
    )


@router.post("/operations/new")
def create_operation(
    request: Request,
    type: str = Form(...),
    product: str = Form(...),
    quantity: str = Form(...),
    country: str = Form(...),
    date: str = Form(...),
    op_status: str = Form(..., alias="status"),
    user_id: str = Form(""),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    errors, type, product, quantity_value, country, date_value, op_status, assigned_user_id = validate_operation(
        type, product, quantity, country, date, op_status, user_id, db
    )
    values = {
        "type": type,
        "product": product,
        "quantity": quantity,
        "country": country,
        "date": date,
        "status": op_status,
        "user_id": user_id,
    }
    if errors:
        return render_form(
            request,
            user,
            "/operations/new",
            "Nueva operación",
            values,
            get_assignable_users(db),
            errors,
        )

    operation = Operation(
        user_id=assigned_user_id,
        type=type,
        product=product,
        quantity=quantity_value,
        country=country,
        date=date_value,
        status=op_status,
    )
    db.add(operation)
    db.commit()
    return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/operations/{operation_id}")
def operation_detail(
    request: Request,
    operation_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    operation = get_operation_or_404(db, operation_id)
    return templates.TemplateResponse(request, "operations/detail.html", {"user": user, "operation": operation})


@router.get("/operations/{operation_id}/edit")
def edit_operation_form(
    request: Request,
    operation_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    operation = get_operation_or_404(db, operation_id)
    values = {
        "user_id": str(operation.user_id or ""),
        "type": operation.type,
        "product": operation.product,
        "quantity": operation.quantity,
        "country": operation.country,
        "date": operation.date.isoformat(),
        "status": operation.status,
    }
    return render_form(
        request,
        user,
        f"/operations/{operation.id}/edit",
        "Editar operación",
        values,
        get_assignable_users(db),
    )


@router.post("/operations/{operation_id}/edit")
def update_operation(
    request: Request,
    operation_id: int,
    type: str = Form(...),
    product: str = Form(...),
    quantity: str = Form(...),
    country: str = Form(...),
    date: str = Form(...),
    op_status: str = Form(..., alias="status"),
    user_id: str = Form(""),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    operation = get_operation_or_404(db, operation_id)
    errors, type, product, quantity_value, country, date_value, op_status, assigned_user_id = validate_operation(
        type, product, quantity, country, date, op_status, user_id, db
    )
    values = {
        "type": type,
        "product": product,
        "quantity": quantity,
        "country": country,
        "date": date,
        "status": op_status,
        "user_id": user_id,
    }
    if errors:
        return render_form(
            request,
            user,
            f"/operations/{operation.id}/edit",
            "Editar operación",
            values,
            get_assignable_users(db),
            errors,
        )

    operation.user_id = assigned_user_id
    operation.type = type
    operation.product = product
    operation.quantity = quantity_value
    operation.country = country
    operation.date = date_value
    operation.status = op_status
    db.commit()
    return RedirectResponse(f"/operations/{operation.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/operations/{operation_id}/delete")
def delete_operation(
    operation_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    operation = get_operation_or_404(db, operation_id)
    db.delete(operation)
    db.commit()
    return RedirectResponse("/operations", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/operations")
def api_list_operations(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    operations = db.query(Operation).order_by(Operation.id).all()
    return [
        {
            "id": operation.id,
            "user_id": operation.user_id,
            "username": operation.user.username if operation.user else None,
            "type": operation.type,
            "product": operation.product,
            "quantity": operation.quantity,
            "country": operation.country,
            "date": operation.date.isoformat(),
            "status": operation.status,
        }
        for operation in operations
    ]
