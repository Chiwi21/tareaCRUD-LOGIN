from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import PERSON_JURIDICA, PERSON_NATURAL, ROLE_EXPORTER, ROLE_IMPORTER
from app.models import User

MIN_PASSWORD_LENGTH = 6


def es_cedula_ecuatoriana_valida(cedula: str) -> bool:
    """Comprueba el formato y el dígito verificador de una cédula ecuatoriana.

    Verifica 10 dígitos ASCII, código de provincia (01-24 o 30),
    tercer dígito y algoritmo módulo 10. No consulta al Registro Civil
    ni confirma que el número haya sido emitido a una persona.
    """
    if len(cedula) != 10 or not cedula.isascii() or not cedula.isdigit():
        return False

    provincia = int(cedula[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False

    tercer_digito = int(cedula[2])
    if tercer_digito > 5:
        return False
    # Serie 30: ecuatorianos registrados en consulados en el exterior.
    if provincia == 30 and tercer_digito not in (4, 5):
        return False

    digitos = [int(numero) for numero in cedula]
    coeficientes = (2, 1, 2, 1, 2, 1, 2, 1, 2)
    total = 0
    for numero, coeficiente in zip(digitos[:9], coeficientes):
        producto = numero * coeficiente
        total += producto - 9 if producto > 9 else producto

    digito_verificador = (10 - (total % 10)) % 10
    return digitos[9] == digito_verificador


def _user_value_exists(db: Session, field, value: str, exclude_user_id: int | None) -> bool:
    query = db.query(User.id).filter(field == value)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def validate_user_profile(
    db: Session,
    *,
    role: str,
    person_type: str,
    username: str,
    full_name: str = "",
    cedula: str = "",
    ruc: str = "",
    razon_social: str = "",
    exclude_user_id: int | None = None,
) -> tuple[dict[str, str | None], list[str]]:
    username = username.strip()
    full_name = full_name.strip()
    cedula = cedula.strip()
    ruc = ruc.strip()
    razon_social = razon_social.strip()
    errors: list[str] = []

    if role not in (ROLE_IMPORTER, ROLE_EXPORTER):
        errors.append("Solo se pueden administrar usuarios Importador o Exportador.")
    if person_type not in (PERSON_NATURAL, PERSON_JURIDICA):
        errors.append("Debe seleccionar un tipo de persona válido.")
    if not username:
        errors.append("El usuario es obligatorio.")
    elif len(username) > 50:
        errors.append("El usuario no puede superar los 50 caracteres.")
    else:
        username_query = db.query(User.id).filter(func.lower(User.username) == username.lower())
        if exclude_user_id is not None:
            username_query = username_query.filter(User.id != exclude_user_id)
        if username_query.first() is not None:
            errors.append("El nombre de usuario ya está registrado.")

    if person_type == PERSON_NATURAL:
        if not full_name:
            errors.append("El nombre completo es obligatorio para Persona Natural.")
        elif len(full_name) > 120:
            errors.append("El nombre completo no puede superar los 120 caracteres.")

        if not cedula:
            errors.append("La cédula es obligatoria para Persona Natural.")
        elif not es_cedula_ecuatoriana_valida(cedula):
            errors.append(
                "La cédula ecuatoriana debe tener 10 dígitos, un código "
                "de provincia válido y un dígito verificador correcto."
            )
        elif _user_value_exists(db, User.cedula, cedula, exclude_user_id):
            errors.append("La cédula ya está registrada.")

        ruc = None
        razon_social = None
    elif person_type == PERSON_JURIDICA:
        if not ruc:
            errors.append("El RUC es obligatorio para Persona Jurídica.")
        elif len(ruc) > 20:
            errors.append("El RUC no puede superar los 20 caracteres.")
        elif _user_value_exists(db, User.ruc, ruc, exclude_user_id):
            errors.append("El RUC ya está registrado.")

        if not razon_social:
            errors.append("La razón social es obligatoria para Persona Jurídica.")
        elif len(razon_social) > 150:
            errors.append("La razón social no puede superar los 150 caracteres.")

        full_name = None
        cedula = None

    values: dict[str, str | None] = {
        "username": username,
        "role": role,
        "person_type": person_type,
        "full_name": full_name or None,
        "cedula": cedula or None,
        "ruc": ruc or None,
        "razon_social": razon_social or None,
    }
    return values, errors


def validate_password(password: str, confirmation: str, *, required: bool) -> list[str]:
    if not password:
        if required:
            return ["La contraseña es obligatoria."]
        if confirmation:
            return ["Ingrese la contraseña nueva o deje ambos campos vacíos."]
        return []

    errors: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != confirmation:
        errors.append("Las contraseñas no coinciden.")
    return errors
