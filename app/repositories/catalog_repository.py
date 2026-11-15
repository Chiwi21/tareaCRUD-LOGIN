from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.catalog_specs import OPTION_SOURCES, CatalogSpec


class SqlAlchemyCatalogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, spec: CatalogSpec, q: str = ""):
        stmt = select(spec.model)
        if q and spec.search_fields:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(*(getattr(spec.model, field).ilike(like) for field in spec.search_fields))
            )
        stmt = stmt.order_by(spec.model.id)
        return self.db.scalars(stmt).all()

    def get(self, spec: CatalogSpec, entity_id: int) -> Any | None:
        return self.db.get(spec.model, entity_id)

    def save(
        self, spec: CatalogSpec, values: dict[str, Any], entity_id: int | None = None
    ) -> Any:
        obj = self.db.get(spec.model, entity_id) if entity_id is not None else spec.model()
        if obj is None:
            raise ValueError(f"{spec.singular.capitalize()} no encontrado.")
        for field, value in values.items():
            setattr(obj, field, value)
        if entity_id is None:
            self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, spec: CatalogSpec, entity_id: int) -> None:
        obj = self.db.get(spec.model, entity_id)
        if obj is None:
            raise ValueError(f"{spec.singular.capitalize()} no encontrado.")
        self.db.delete(obj)
        self.db.commit()

    def options(self, source: str) -> list[tuple[str, str]]:
        model, label_attr, order_attr = OPTION_SOURCES[source]
        rows = self.db.scalars(
            select(model).order_by(getattr(model, order_attr))
        ).all()
        return [(str(row.id), str(getattr(row, label_attr))) for row in rows]

    def count(self, spec: CatalogSpec) -> int:
        return self.db.scalar(select(func.count()).select_from(spec.model)) or 0
