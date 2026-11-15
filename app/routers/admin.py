from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.constants import ROLE_ADMIN
from app.database import get_db
from app.dependencies import get_audit_service
from app.flash import flash
from app.models import Company, Operation, User
from app.security import hash_password, require_admin
from app.services.audit_service import AuditService
from app.templating import templates
from app.user_validation import validate_password, validate_user_profile

router = APIRouter(tags=["admin"])


def get_user_or_404(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return target


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "person_type": user.person_type,
        "full_name": user.full_name,
        "cedula": user.cedula,
        "ruc": user.ruc,
        "razon_social": user.razon_social,
        "company_id": user.company_id,
        "company_name": user.company.name if user.company else None,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def render_user_form(
    request: Request,
    admin: User,
    values: dict,
    errors: list[str] | None = None,
    target_id: int | None = None,
):
    editing = target_id is not None
    companies = request.state.db.query(Company).order_by(Company.name).all()
    return templates.TemplateResponse(
        request,
        "admin/user_form.html",
        {
            "user": admin,
            "values": values,
            "errors": errors or [],
            "is_edit": editing,
            "companies": companies,
            "title": "Editar usuario" if editing else "Nuevo usuario",
            "action_url": f"/admin/users/{target_id}/edit" if editing else "/admin/users/new",
            "cancel_url": f"/admin/users/{target_id}" if editing else "/admin/users",
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


def values_without_form_role(values: dict) -> dict:
    return {
        field: value
        for field, value in values.items()
        if field not in ("user_type", "company_id", "is_active")
    }


def get_editable_user_or_403(db: Session, user_id: int) -> User:
    target = get_user_or_404(db, user_id)
    if target.role == ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta Administrador se administra mediante el seed.",
        )
    return target


def _company_id(raw: str) -> tuple[int | None, list[str]]:
    if not raw:
        return None, []
    try:
        return int(raw), []
    except ValueError:
        return None, ["La empresa seleccionada no es válida."]


@router.get("/admin/users")
def list_users(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).options(joinedload(User.company)).order_by(User.id).all()
    return templates.TemplateResponse(
        request, "admin/users.html", {"user": user, "users": users}
    )


@router.get("/admin/users/new")
def new_user_form(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    request.state.db = db
    return render_user_form(request, user, {"is_active": True})


@router.post("/admin/users/new")
def create_user_html(
    request: Request,
    user_type: str = Form(...),
    person_type: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(""),
    cedula: str = Form(""),
    ruc: str = Form(""),
    razon_social: str = Form(""),
    company_id: str = Form(""),
    is_active: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    values, errors = validate_user_profile(
        db,
        role=user_type,
        person_type=person_type,
        username=username,
        full_name=full_name,
        cedula=cedula,
        ruc=ruc,
        razon_social=razon_social,
    )
    errors.extend(validate_password(password, confirm_password, required=True))
    company_id_value, company_errors = _company_id(company_id)
    errors.extend(company_errors)
    if company_id_value is not None and db.get(Company, company_id_value) is None:
        errors.append("La empresa seleccionada no existe.")
    values.update({"user_type": user_type, "company_id": company_id or "", "is_active": bool(is_active)})
    request.state.db = db
    if errors:
        return render_user_form(request, admin, values, errors)

    account = User(
        password_hash=hash_password(password),
        company_id=company_id_value,
        is_active=bool(is_active),
        **values_without_form_role(values),
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_user_form(
            request, admin, values, ["El usuario, la cédula o el RUC ya están registrados."]
        )
    db.refresh(account)
    audit.log(admin.id, "CREATE", "users", account.id, f"Usuario {account.username} creado")
    flash(request, "Usuario creado correctamente.", "success")
    return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/users/{user_id}/edit")
def edit_user_form(
    request: Request,
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_editable_user_or_403(db, user_id)
    request.state.db = db
    values = {
        "user_type": target.role,
        "person_type": target.person_type,
        "username": target.username,
        "full_name": target.full_name or "",
        "cedula": target.cedula or "",
        "ruc": target.ruc or "",
        "razon_social": target.razon_social or "",
        "company_id": str(target.company_id or ""),
        "is_active": target.is_active,
    }
    return render_user_form(request, admin, values, target_id=target.id)


@router.post("/admin/users/{user_id}/edit")
def update_user_html(
    request: Request,
    user_id: int,
    user_type: str = Form(...),
    person_type: str = Form(...),
    username: str = Form(...),
    password: str = Form(""),
    confirm_password: str = Form(""),
    full_name: str = Form(""),
    cedula: str = Form(""),
    ruc: str = Form(""),
    razon_social: str = Form(""),
    company_id: str = Form(""),
    is_active: str = Form(""),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    target = get_editable_user_or_403(db, user_id)
    values, errors = validate_user_profile(
        db,
        role=user_type,
        person_type=person_type,
        username=username,
        full_name=full_name,
        cedula=cedula,
        ruc=ruc,
        razon_social=razon_social,
        exclude_user_id=target.id,
    )
    errors.extend(validate_password(password, confirm_password, required=False))
    company_id_value, company_errors = _company_id(company_id)
    errors.extend(company_errors)
    if company_id_value is not None and db.get(Company, company_id_value) is None:
        errors.append("La empresa seleccionada no existe.")
    values.update({"user_type": user_type, "company_id": company_id or "", "is_active": bool(is_active)})
    request.state.db = db
    if errors:
        return render_user_form(request, admin, values, errors, target_id=target.id)

    for field, value in values_without_form_role(values).items():
        setattr(target, field, value)
    target.company_id = company_id_value
    target.is_active = bool(is_active)
    if password:
        target.password_hash = hash_password(password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_user_form(
            request, admin, values, ["El usuario, la cédula o el RUC ya están registrados."], target.id
        )
    audit.log(admin.id, "UPDATE", "users", target.id, f"Usuario {target.username} actualizado")
    flash(request, "Usuario actualizado correctamente.", "success")
    return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/users/{user_id}")
def user_detail(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.query(User).options(joinedload(User.company)).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    operations = db.query(Operation).filter(Operation.user_id == target.id).order_by(Operation.id.desc()).all()
    return templates.TemplateResponse(
        request, "admin/user_detail.html", {"user": user, "target": target, "operations": operations}
    )


@router.post("/admin/users/{user_id}/delete")
def delete_user_html(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    target = get_user_or_404(db, user_id)
    if target.id == user.id:
        flash(request, "No puede eliminar su propia cuenta de administrador.", "error")
        return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)
    if db.query(Operation.id).filter(Operation.user_id == target.id).first() is not None:
        flash(request, "No se puede eliminar el usuario porque tiene operaciones asignadas.", "error")
        return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)
    username = target.username
    db.delete(target)
    db.commit()
    audit.log(user.id, "DELETE", "users", user_id, f"Usuario {username} eliminado")
    flash(request, "Usuario eliminado correctamente.", "success")
    return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/admin/users")
def api_list_users(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).options(joinedload(User.company)).order_by(User.id).all()
    return [serialize_user(u) for u in users]


@router.get("/api/admin/users/{user_id}")
def api_user_detail(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return serialize_user(get_user_or_404(db, user_id))


@router.delete("/api/admin/users/{user_id}")
def api_delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    if target.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta de administrador.",
        )
    if db.query(Operation.id).filter(Operation.user_id == target.id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el usuario porque tiene operaciones asignadas.",
        )
    db.delete(target)
    db.commit()
    return {"detail": "Usuario eliminado correctamente", "id": user_id}
