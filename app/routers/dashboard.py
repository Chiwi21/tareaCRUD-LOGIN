from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.constants import ROLE_ADMIN
from app.dependencies import get_dashboard_service
from app.models import User
from app.security import require_login
from app.services.dashboard_service import DashboardService
from app.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(
    request: Request,
    user: User = Depends(require_login),
    service: DashboardService = Depends(get_dashboard_service),
):
    scope_user_id = None if user.role == ROLE_ADMIN else user.id
    data = service.overview(scope_user_id)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, **data, "is_admin": user.role == ROLE_ADMIN},
    )
