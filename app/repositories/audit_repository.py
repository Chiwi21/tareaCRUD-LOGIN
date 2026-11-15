from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import AuditLog, User
from app.repositories.protocols import AuditFilters


class SqlAlchemyAuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        user_id: int | None,
        action: str,
        entity: str,
        entity_id: int | None = None,
        detail: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list(self, filters: AuditFilters | None = None, limit: int = 200):
        stmt = select(AuditLog).options(joinedload(AuditLog.user))
        if filters:
            if filters.q:
                like = f"%{filters.q.strip()}%"
                stmt = stmt.where(
                    or_(
                        AuditLog.detail.ilike(like),
                        AuditLog.entity.ilike(like),
                        AuditLog.user.has(User.username.ilike(like)),
                    )
                )
            if filters.action:
                stmt = stmt.where(AuditLog.action == filters.action)
            if filters.entity:
                stmt = stmt.where(AuditLog.entity == filters.entity)
        return self.db.scalars(
            stmt.order_by(AuditLog.id.desc()).limit(limit)
        ).unique().all()
