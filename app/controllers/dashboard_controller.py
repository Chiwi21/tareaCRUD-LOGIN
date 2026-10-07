from fastapi import APIRouter, Depends, Request

from app.models import User
from app.security import require_login
from app.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})
