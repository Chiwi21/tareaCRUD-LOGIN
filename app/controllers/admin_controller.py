from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import ROLE_ADMIN
from app.database import get_db
from app.models import Operation, User
from app.security import hash_password, require_admin
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
    return templates.TemplateResponse(
        request,
        "admin/user_form.html",
        {
            "user": admin,
            "values": values,
            "errors": errors or [],
            "is_edit": editing,
            "title": "Editar usuario" if editing else "Nuevo usuario",
            "action_url": f"/admin/users/{target_id}/edit" if editing else "/admin/users/new",
            "cancel_url": f"/admin/users/{target_id}" if editing else "/admin/users",
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


def values_without_form_role(values: dict) -> dict:
    return {field: value for field, value in values.items() if field != "user_type"}


def get_editable_user_or_403(db: Session, user_id: int) -> User:
    target = get_user_or_404(db, user_id)
    if target.role == ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta Administrador se administra mediante el seed.",
        )
    return target


@router.get("/admin/users")
def list_users(
    request: Request,
    created: int = 0,
    updated: int = 0,
    deleted: int = 0,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id).all()
    success = None
    if created:
        success = "Usuario creado correctamente."
    elif updated:
        success = "Usuario actualizado correctamente."
    elif deleted:
        success = "Usuario eliminado correctamente."
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {"user": user, "users": users, "success": success},
    )


@router.get("/admin/users/new")
def new_user_form(request: Request, user: User = Depends(require_admin)):
    return render_user_form(request, user, {})


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
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
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
    values["user_type"] = user_type
    if errors:
        return render_user_form(request, admin, values, errors)

    account = User(password_hash=hash_password(password), **values_without_form_role(values))
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors = ["El usuario, la cédula o el RUC ya están registrados."]
        return render_user_form(request, admin, values, errors)

    return RedirectResponse("/admin/users?created=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/users/{user_id}/edit")
def edit_user_form(
    request: Request,
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_editable_user_or_403(db, user_id)
    values = {
        "user_type": target.role,
        "person_type": target.person_type,
        "username": target.username,
        "full_name": target.full_name or "",
        "cedula": target.cedula or "",
        "ruc": target.ruc or "",
        "razon_social": target.razon_social or "",
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
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
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
    values["user_type"] = user_type
    if errors:
        return render_user_form(request, admin, values, errors, target_id=target.id)

    for field, value in values_without_form_role(values).items():
        setattr(target, field, value)
    if password:
        target.password_hash = hash_password(password)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors = ["El usuario, la cédula o el RUC ya están registrados."]
        return render_user_form(request, admin, values, errors, target_id=target.id)

    return RedirectResponse("/admin/users?updated=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/users/{user_id}")
def user_detail(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    return templates.TemplateResponse(request, "admin/user_detail.html", {"user": user, "target": target})


@router.post("/admin/users/{user_id}/delete")
def delete_user_html(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    if target.id == user.id:
        users = db.query(User).order_by(User.id).all()
        return templates.TemplateResponse(
            request,
            "admin/users.html",
            {
                "user": user,
                "users": users,
                "error": "No puede eliminar su propia cuenta de administrador.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if db.query(Operation.id).filter(Operation.user_id == target.id).first() is not None:
        users = db.query(User).order_by(User.id).all()
        return templates.TemplateResponse(
            request,
            "admin/users.html",
            {
                "user": user,
                "users": users,
                "error": "No se puede eliminar el usuario porque tiene operaciones asignadas.",
            },
            status_code=status.HTTP_409_CONFLICT,
        )
    db.delete(target)
    db.commit()
    return RedirectResponse("/admin/users?deleted=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/admin/users")
def api_list_users(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [serialize_user(u) for u in users]


@router.get("/api/admin/users/{user_id}")
def api_user_detail(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    return serialize_user(target)


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
