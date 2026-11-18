"""Migra la base del esquema anterior (Tarea 3) al esquema TradeLab.

El esquema antiguo guardaba un solo producto por operación en columnas de
texto. La migración conserva usuarios y operaciones, crea un producto legado
por cada nombre de producto y deja la operación con su ítem correspondiente.

Uso local:
    python migrate_legacy.py

En Render el comando de arranque lo ejecuta antes del seed. Es seguro volver a
ejecutarlo: si detecta el esquema nuevo, no borra nada.
"""

from __future__ import annotations

import os

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import inspect, text

from app.constants import (
    OPERATION_STATUSES,
    OPERATION_TYPES,
    STATUS_PENDING,
)
from app.database import Base, SessionLocal, engine
from app.models import (
    Category,
    Operation,
    OperationItem,
    OperationStatusHistory,
    Product,
    User,
)


def is_legacy_schema() -> bool:
    inspector = inspect(engine)
    if "operations" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("operations")}
    return "product" in columns and "code" not in columns


def read_legacy_rows() -> tuple[list[dict], list[dict]]:
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    operation_columns = {column["name"] for column in inspector.get_columns("operations")}

    user_fields = [
        field
        for field in (
            "id",
            "username",
            "password_hash",
            "role",
            "person_type",
            "full_name",
            "cedula",
            "ruc",
            "razon_social",
            "created_at",
        )
        if field in user_columns
    ]
    operation_fields = [
        field
        for field in (
            "id",
            "type",
            "product",
            "quantity",
            "country",
            "date",
            "status",
            "created_at",
            "user_id",
        )
        if field in operation_columns
    ]

    with engine.connect() as connection:
        users = [
            dict(row._mapping)
            for row in connection.execute(
                text(f"SELECT {', '.join(user_fields)} FROM users ORDER BY id")
            )
        ]
        operations = [
            dict(row._mapping)
            for row in connection.execute(
                text(f"SELECT {', '.join(operation_fields)} FROM operations ORDER BY id")
            )
        ]
    return users, operations


def parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def parse_date(value) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return date.today()


def migrate() -> None:
    if os.getenv("APP_ENV") == "production":
        raise SystemExit(
            "Migración heredada bloqueada en producción: este procedimiento puede "
            "reconstruir tablas. Realiza primero un respaldo y una migración "
            "revisada manualmente."
        )
    if not is_legacy_schema():
        print("No se detectó el esquema anterior. Nada que migrar.")
        from app.database import init_database

        init_database()
        return

    users, operations = read_legacy_rows()
    print(f"Esquema anterior detectado: {len(users)} usuarios, {len(operations)} operaciones.")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user_map: dict[int, int] = {}
        for row in users:
            user = User(
                username=row["username"],
                password_hash=row["password_hash"],
                role=row["role"],
                person_type=row.get("person_type"),
                full_name=row.get("full_name"),
                cedula=row.get("cedula"),
                ruc=row.get("ruc"),
                razon_social=row.get("razon_social"),
                is_active=True,
                created_at=parse_datetime(row.get("created_at")) or datetime.now(),
            )
            db.add(user)
            db.flush()
            user_map[row["id"]] = user.id
        print(f"Usuarios migrados: {len(user_map)}")

        category = Category(
            name="Catálogo legado",
            description="Productos importados desde el esquema anterior de la Tarea 3.",
        )
        db.add(category)
        db.flush()

        product_cache: dict[str, Product] = {}
        for index, row in enumerate(operations, start=1):
            product_name = str(row.get("product") or "Producto legado").strip()
            if product_name not in product_cache:
                product = Product(
                    sku=f"LEG-{len(product_cache) + 1:03d}",
                    name=product_name[:150],
                    category_id=category.id,
                    unit="UND",
                    unit_price=Decimal("0"),
                    weight_kg=Decimal("0"),
                    is_active=True,
                )
                db.add(product)
                db.flush()
                product_cache[product_name] = product

            operation_date = parse_date(row.get("date"))
            type_ = row.get("type") if row.get("type") in OPERATION_TYPES else "IMPORT"
            status = row.get("status") if row.get("status") in OPERATION_STATUSES else STATUS_PENDING
            created_at = parse_datetime(row.get("created_at")) or datetime.now()

            operation = Operation(
                code=f"OP-{operation_date.year}-{int(row['id']):04d}",
                user_id=user_map.get(row.get("user_id")) if row.get("user_id") else None,
                type=type_,
                status=status,
                operation_date=operation_date,
                notes=(
                    "Operación migrada del esquema anterior. "
                    f"País original: {row.get('country') or '—'}."
                ),
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(operation)
            db.flush()

            quantity = Decimal(str(row.get("quantity") or 1))
            db.add(
                OperationItem(
                    operation_id=operation.id,
                    product_id=product_cache[product_name].id,
                    description=f"Migrado: {product_name}",
                    quantity=quantity,
                    unit_price=Decimal("0"),
                    subtotal=Decimal("0"),
                )
            )
            db.add(
                OperationStatusHistory(
                    operation_id=operation.id,
                    from_status=None,
                    to_status=status,
                    changed_by_id=operation.user_id,
                    note="Operación migrada del esquema anterior",
                    created_at=created_at,
                )
            )
            print(f"  Operación migrada: {operation.code} · {product_name} · {quantity} UND")

        db.commit()
        print("Migración completada. Ejecute ahora: python seed.py")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
