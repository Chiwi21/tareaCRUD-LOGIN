from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_audit_service
from app.flash import flash
from app.models import User
from app.schemas.auth import UserOut
from app.security import get_current_user, hash_password, require_login, verify_password
from app.services.audit_service import AuditService
from app.templating import templates
from app.user_validation import validate_password, validate_user_profile

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_form(
    request: Request,
    registered: int = 0,
    user: User | None = Depends(get_current_user),
):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request, "auth/login.html", {"user": None, "registered": registered}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    user = db.query(User).filter(func.lower(User.username) == username.strip().lower()).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "user": None,
                "error": "Usuario o contraseña incorrectos.",
                "username": username.strip(),
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    audit.log(user.id, "LOGIN", "users", user.id, "Inicio de sesión")
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(
    request: Request,
    user: User | None = Depends(get_current_user),
    audit: AuditService = Depends(get_audit_service),
):
    if user is not None:
        audit.log(user.id, "LOGOUT", "users", user.id, "Cierre de sesión")
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register")
def register_form(request: Request, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request, "auth/register.html", {"user": None, "values": {}}
    )


@router.post("/register")
def register(
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
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    profile, errors = validate_user_profile(
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
    if errors:
        values = {**profile, "user_type": user_type}
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"user": None, "errors": errors, "values": values},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    user = User(password_hash=hash_password(password), **profile)
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.log(user.id, "CREATE", "users", user.id, f"Registro público de {user.username}")
    flash(request, "Registro exitoso. Ya puede iniciar sesión.", "success")
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/auth/me", response_model=UserOut)
def api_me(user: User = Depends(require_login)):
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        person_type=user.person_type,
        full_name=user.full_name,
        cedula=user.cedula,
        ruc=user.ruc,
        razon_social=user.razon_social,
        company_name=user.company.name if user.company else None,
        is_active=user.is_active,
        created_at=user.created_at,
    )
