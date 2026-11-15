from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_audit_service
from app.models import User
from app.repositories.protocols import AuditFilters
from app.security import require_admin
from app.services.audit_service import AuditService
from app.templating import templates

router = APIRouter(tags=["audit"])


@router.get("/admin/audit")
def audit_list(
    request: Request,
    q: str = "",
    action: str = "",
    entity: str = "",
    user: User = Depends(require_admin),
    service: AuditService = Depends(get_audit_service),
):
    entries = service.list(AuditFilters(q=q, action=action, entity=entity))
    return templates.TemplateResponse(
        request,
        "audit/list.html",
        {"user": user, "entries": entries, "q": q, "action": action, "entity": entity},
    )


@router.get("/api/admin/audit")
def api_audit_list(
    q: str = "",
    action: str = "",
    entity: str = "",
    user: User = Depends(require_admin),
    service: AuditService = Depends(get_audit_service),
):
    entries = service.list(AuditFilters(q=q, action=action, entity=entity))
    return [
        {
            "id": entry.id,
            "user": entry.user.username if entry.user else None,
            "action": entry.action,
            "entity": entry.entity,
            "entity_id": entry.entity_id,
            "detail": entry.detail,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        for entry in entries
    ]
