from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import PERSON_JURIDICA, PERSON_NATURAL, ROLE_EXPORTER, ROLE_IMPORTER
from app.database import get_db
from app.models import User
from app.security import get_current_user, hash_password, verify_password
from app.templating import templates

router = APIRouter(tags=["auth"])

MIN_PASSWORD_LENGTH = 6


@router.get("/login")
def login_form(request: Request, registered: int = 0, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "auth/login.html", {"user": None, "registered": registered})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(func.lower(User.username) == username.strip().lower()).first()
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {"user": None, "error": "Usuario o contraseña incorrectos.", "username": username.strip()},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register")
def register_form(request: Request, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "auth/register.html", {"user": None, "values": {}})


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
):
    username = username.strip()
    full_name = full_name.strip()
    cedula = cedula.strip()
    ruc = ruc.strip()
    razon_social = razon_social.strip()

    errors: list[str] = []

    if user_type not in (ROLE_IMPORTER, ROLE_EXPORTER):
        errors.append("Debe seleccionar un tipo de usuario válido (Importador o Exportador).")
    if person_type not in (PERSON_NATURAL, PERSON_JURIDICA):
        errors.append("Debe seleccionar un tipo de persona válido (Natural o Jurídica).")
    if not username:
        errors.append("El usuario es obligatorio.")
    elif db.query(User).filter(func.lower(User.username) == username.lower()).first():
        errors.append("El nombre de usuario ya está registrado.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != confirm_password:
        errors.append("Las contraseñas no coinciden.")

    if person_type == PERSON_NATURAL:
        if not full_name:
            errors.append("El nombre completo es obligatorio para Persona Natural.")
        if not cedula:
            errors.append("La cédula es obligatoria para Persona Natural.")
        elif db.query(User).filter(User.cedula == cedula).first():
            errors.append("La cédula ya está registrada.")
        ruc = None
        razon_social = None
    elif person_type == PERSON_JURIDICA:
        if not ruc:
            errors.append("El RUC es obligatorio para Persona Jurídica.")
        elif db.query(User).filter(User.ruc == ruc).first():
            errors.append("El RUC ya está registrado.")
        if not razon_social:
            errors.append("La razón social es obligatoria para Persona Jurídica.")
        full_name = None
        cedula = None

    if errors:
        values = {
            "user_type": user_type,
            "person_type": person_type,
            "username": username,
            "full_name": full_name or "",
            "cedula": cedula or "",
            "ruc": ruc or "",
            "razon_social": razon_social or "",
        }
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {"user": None, "errors": errors, "values": values},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=user_type,
        person_type=person_type,
        full_name=full_name,
        cedula=cedula,
        ruc=ruc,
        razon_social=razon_social,
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/login?registered=1", status_code=status.HTTP_303_SEE_OTHER)
