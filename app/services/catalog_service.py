from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.catalog_specs import CATALOG_SPECS, CatalogSpec
from app.repositories.protocols import CatalogRepository


class CatalogService:
    """CRUD genérico y validado para los catálogos declarados."""

    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    @property
    def specs(self) -> dict[str, CatalogSpec]:
        return CATALOG_SPECS

    def get_spec(self, key: str) -> CatalogSpec:
        spec = CATALOG_SPECS.get(key)
        if spec is None:
            raise KeyError("Catálogo no encontrado.")
        return spec

    def list(self, key: str, q: str = ""):
        spec = self.get_spec(key)
        return self.repository.list(spec, q)

    def get(self, key: str, entity_id: int):
        spec = self.get_spec(key)
        return self.repository.get(spec, entity_id)

    def counts(self) -> dict[str, int]:
        return {key: self.repository.count(spec) for key, spec in CATALOG_SPECS.items()}

    def options_for(self, spec: CatalogSpec) -> dict[str, list[tuple[str, str]]]:
        return {
            field.name: self.repository.options(field.options_source)
            for field in spec.fields
            if field.options_source
        }

    def values_from(self, spec: CatalogSpec, obj: Any | None) -> dict[str, Any]:
        if obj is None:
            return {"is_active": True} if any(f.name == "is_active" for f in spec.fields) else {}
        values: dict[str, Any] = {}
        for field in spec.fields:
            value = getattr(obj, field.name, None)
            if field.kind == "checkbox":
                values[field.name] = bool(value)
            elif field.kind == "decimal" and value is not None:
                values[field.name] = str(value)
            elif field.kind == "integer" and value is not None:
                values[field.name] = str(value)
            else:
                values[field.name] = "" if value is None else value
        return values

    def rows(self, key: str, q: str = "") -> list[dict[str, Any]]:
        spec = self.get_spec(key)
        objects = self.repository.list(spec, q)
        rows = []
        for obj in objects:
            values = []
            for attr, _label in spec.columns:
                values.append(self._display_value(obj, attr))
            rows.append({"id": obj.id, "values": values, "obj": obj})
        return rows

    def _display_value(self, obj: Any, attr: str) -> str:
        if attr.endswith("_id"):
            relationship_name = attr[:-3]
            related = getattr(obj, relationship_name, None)
            if related is None:
                return "—"
            return str(getattr(related, "name", None) or getattr(related, "code", None) or related)
        value = getattr(obj, attr, None)
        if value is None or value == "":
            return "—"
        if isinstance(value, bool):
            return "Sí" if value else "No"
        if isinstance(value, Decimal):
            return f"{value:,.2f}"
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def save(
        self, key: str, form_data: Any, entity_id: int | None = None
    ) -> tuple[Any | None, list[str], dict[str, Any]]:
        spec = self.get_spec(key)
        values: dict[str, Any] = {}
        errors: list[str] = []
        for field in spec.fields:
            raw = form_data.get(field.name)
            if field.kind == "checkbox":
                values[field.name] = raw is not None
                continue
            raw = (raw or "").strip() if isinstance(raw, str) else raw
            if field.kind == "select" or field.kind == "integer":
                if raw in (None, ""):
                    if field.required:
                        errors.append(f"{field.label} es obligatorio.")
                        values[field.name] = None
                    else:
                        values[field.name] = None
                    continue
                try:
                    values[field.name] = int(raw)
                except (TypeError, ValueError):
                    errors.append(f"{field.label} debe ser un número entero.")
                    values[field.name] = None
            elif field.kind == "decimal":
                if raw in (None, ""):
                    if field.required:
                        errors.append(f"{field.label} es obligatorio.")
                    values[field.name] = Decimal("0") if field.required else None
                    continue
                try:
                    values[field.name] = Decimal(str(raw))
                except (InvalidOperation, ValueError):
                    errors.append(f"{field.label} debe ser un número válido.")
                    values[field.name] = Decimal("0")
            else:
                if field.required and not raw:
                    errors.append(f"{field.label} es obligatorio.")
                values[field.name] = raw or None
        if errors:
            return None, errors, values
        try:
            obj = self.repository.save(spec, values, entity_id)
        except IntegrityError:
            return None, ["Ya existe un registro con esos datos. Revise los campos únicos."], values
        except ValueError as exc:
            return None, [str(exc)], values
        return obj, [], values

    def delete(self, key: str, entity_id: int) -> list[str]:
        try:
            self.repository.delete(self.get_spec(key), entity_id)
        except IntegrityError:
            return [
                "No se puede eliminar porque el registro está siendo usado por una operación, "
                "producto o documento."
            ]
        except ValueError as exc:
            return [str(exc)]
        return []

    def serialize(self, key: str, obj: Any) -> dict[str, Any]:
        spec = self.get_spec(key)
        return {
            "id": obj.id,
            **{field.name: self._json_value(getattr(obj, field.name, None)) for field in spec.fields},
        }

    def _json_value(self, value: Any):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, date):
            return value.isoformat()
        return value
