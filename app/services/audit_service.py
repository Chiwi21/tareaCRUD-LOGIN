from __future__ import annotations

from app.repositories.protocols import AuditFilters, AuditRepository


class AuditService:
    """Registra acciones administrativas sin acoplar los routers a SQLAlchemy."""

    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def log(
        self,
        user_id: int | None,
        action: str,
        entity: str,
        entity_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        try:
            self.repository.log(user_id, action, entity, entity_id, detail)
        except Exception:
            # La auditoría nunca debe tumbar la operación principal.
            pass

    def list(self, filters: AuditFilters | None = None, limit: int = 200):
        return self.repository.list(filters, limit)
