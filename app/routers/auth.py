from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
import re
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_audit_service
from app.flash import flash
from app.models import User, UserEmail
from app.schemas.auth import UserOut
from app.security import get_current_user, hash_password, require_login, verify_password
from app.services.audit_service import AuditService
from app.templating import templates
from app.user_validation import validate_password, validate_user_profile
from app.constants import ROLE_IMPORTER, PERSON_NATURAL

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
    identifier = username.strip().lower()
    if "@" in identifier:
        linked_email = db.query(UserEmail).filter(func.lower(UserEmail.email) == identifier).first()
        user = db.get(User, linked_email.user_id) if linked_email else None
    else:
        user = db.query(User).filter(func.lower(User.username) == identifier).first()
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
    full_name: str = Form(...),
    cedula: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
):
    """Registro público simplificado: importador persona natural.

    El nombre de usuario interno se genera automáticamente; el acceso público
    se realiza con el correo. Administrador y exportador conservan su alta
    mediante las herramientas administrativas preexistentes.
    """
    full_name = full_name.strip()
    cedula = cedula.strip()
    email = email.strip().lower()
    errors = []
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", email) or len(email) > 254:
        errors.append("Ingrese un correo electrónico válido.")
    elif db.query(UserEmail.id).filter(func.lower(UserEmail.email) == email).first():
        errors.append("El correo electrónico ya está registrado.")

    # Mantener compatibilidad con la validación backend original.
    # El usuario interno no se pide en el formulario.
    generated_username = "it_" + uuid4().hex[:24]
    profile, profile_errors = validate_user_profile(
        db, role=ROLE_IMPORTER, person_type=PERSON_NATURAL,
        username=generated_username, full_name=full_name, cedula=cedula,
    )
    errors.extend(profile_errors)
    errors.extend(validate_password(password, password, required=True))
    values = {"full_name": full_name, "cedula": cedula, "email": email}
    if errors:
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"user": None, "errors": errors, "values": values},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    account = User(password_hash=hash_password(password), **profile)
    db.add(account)
    db.flush()
    db.add(UserEmail(user_id=account.id, email=email))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"user": None, "errors": ["La cédula o el correo electrónico ya está registrado."], "values": values},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.refresh(account)
    audit.log(account.id, "CREATE", "users", account.id, "Registro de importador")
    flash(request, "Cuenta creada correctamente. Inicie sesión con su correo.", "success")
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
