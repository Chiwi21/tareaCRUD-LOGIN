"""Inicialización segura e idempotente de International Trade en Render.

NO migra, altera ni elimina tablas existentes. Si el esquema es incompatible,
interrumpe el despliegue sin modificar información. Usar una base Neon nueva.
"""
from __future__ import annotations

import os

from sqlalchemy import inspect

from app.database import Base, SessionLocal, engine, init_database
from app import models  # noqa: F401  registra todas las tablas ORM


def check_production_settings() -> None:
    if os.getenv("APP_ENV") != "production":
        raise SystemExit("APP_ENV debe ser production para ejecutar este inicializador.")
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
        raise SystemExit("DATABASE_URL debe ser la conexión PostgreSQL de Neon (no SQLite).")
    secret = os.getenv("SECRET_KEY", "")
    if len(secret) < 32 or secret == "dev-secret-key-cambiar-en-produccion":
        raise SystemExit("SECRET_KEY no es segura. Render debe generarla automáticamente.")
    password = os.getenv("ADMIN_PASSWORD", "")
    if len(password) < 12 or password in {"admin123", "demo123", "password123"}:
        raise SystemExit("ADMIN_PASSWORD debe ser única y tener al menos 12 caracteres.")


def ensure_schema_is_compatible() -> None:
    """Comprueba todas las columnas presentes antes de permitir create_all().

    SQLAlchemy create_all() crea tablas faltantes, pero NO añade columnas a
    tablas existentes. Detectamos incompatibilidades antes de escribir nada.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    mismatches = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        current_columns = {col["name"] for col in inspector.get_columns(table.name)}
        required_columns = {col.name for col in table.columns}
        missing = sorted(required_columns - current_columns)
        if missing:
            mismatches.append(f"{table.name}: faltan columnas {', '.join(missing)}")
    if mismatches:
        details = "\n".join(" - " + entry for entry in mismatches[:20])
        raise SystemExit(
            "La base Neon tiene un esquema anterior o incompatible. "
            "NO se ha eliminado ni alterado ninguna tabla.\n"
            + details
            + "\nUtiliza una base de datos nueva para V3 o prepara una migración "
              "revisada y respaldada antes de conectar tus datos existentes."
        )


def seed_reference_data(db) -> None:
    """Carga catálogos mínimos SIN cuentas, empresas ni productos ficticios."""
    from decimal import Decimal
    from app.models import (
        Category, Country, Currency, Port, Incoterm, CostConcept, DocumentType,
    )
    from seed import (
        CATEGORIES, COUNTRIES, CURRENCIES, PORTS, INCOTERMS,
        COST_CONCEPTS, DOCUMENT_TYPES, get_or_create,
    )

    countries = {}
    for iso, name in COUNTRIES:
        country, _ = get_or_create(db, Country, {"name": name}, iso_code=iso)
        countries[iso] = country
    for code, name, iso, port_type, city in PORTS:
        get_or_create(db, Port, {
            "country_id": countries[iso].id, "name": name,
            "port_type": port_type, "city": city,
        }, code=code)
    for code, name, symbol in CURRENCIES:
        get_or_create(db, Currency, {"name": name, "symbol": symbol}, code=code)
    for name, description in CATEGORIES:
        get_or_create(db, Category, {"description": description}, name=name)
    for code, name, description in INCOTERMS:
        get_or_create(db, Incoterm, {"name": name, "description": description}, code=code)
    for code, name, calculation_type, category, _rate in COST_CONCEPTS:
        # Nunca precargar tasas/tarifas de ejemplo como si estuviesen vigentes.
        get_or_create(db, CostConcept, {
            "name": name, "calculation_type": calculation_type,
            "category": category, "default_rate": Decimal("0"), "is_active": True,
        }, code=code)
    for code, name, applies_to, required, expires in DOCUMENT_TYPES:
        get_or_create(db, DocumentType, {
            "name": name, "applies_to": applies_to,
            "is_required": required, "requires_expiry": expires,
        }, code=code)
    db.commit()


def main() -> None:
    check_production_settings()
    ensure_schema_is_compatible()
    # Genera solamente las tablas que falten, sin eliminar existentes.
    init_database()
    from seed import create_admin
    with SessionLocal() as db:
        create_admin(db)
        db.commit()
        seed_reference_data(db)
    print("International Trade: base lista, administrador y catálogos mínimos inicializados.")
    print("No se crearon cuentas ni operaciones de demostración.")


if __name__ == "__main__":
    main()
