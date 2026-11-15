from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.dependencies import get_alert_service
from app.flash import flash
from app.models import User
from app.repositories.protocols import AlertFilters
from app.schemas import AlertOut
from app.security import require_admin
from app.services.alert_service import AlertService
from app.templating import templates

router = APIRouter(tags=["alerts"])


def _alert_out(alert) -> AlertOut:
    return AlertOut(
        id=alert.id,
        operation_id=alert.operation_id,
        operation_code=alert.operation.code if alert.operation else None,
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        message=alert.message,
        status=alert.status,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )


@router.get("/alerts")
def list_alerts(
    request: Request,
    status_filter: str = Query("OPEN", alias="status"),
    severity: str = "",
    user: User = Depends(require_admin),
    service: AlertService = Depends(get_alert_service),
):
    alerts = service.list(AlertFilters(status=status_filter, severity=severity))
    return templates.TemplateResponse(
        request,
        "alerts/list.html",
        {
            "user": user,
            "alerts": alerts,
            "status_filter": status_filter,
            "severity": severity,
            "open_count": service.open_count(),
        },
    )


@router.post("/alerts/generate")
def generate_alerts(
    request: Request,
    user: User = Depends(require_admin),
    service: AlertService = Depends(get_alert_service),
):
    count = service.generate_all()
    flash(request, f"Se evaluaron las reglas y se generaron {count} alertas.", "success")
    return RedirectResponse("/alerts", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    request: Request,
    alert_id: int,
    user: User = Depends(require_admin),
    service: AlertService = Depends(get_alert_service),
):
    try:
        service.resolve(alert_id, user.id)
        flash(request, "Alerta marcada como resuelta.", "success")
    except ValueError as exc:
        flash(request, str(exc), "error")
    return RedirectResponse("/alerts", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/alerts", response_model=list[AlertOut])
def api_list_alerts(
    status_filter: str = Query("OPEN", alias="status"),
    severity: str = "",
    user: User = Depends(require_admin),
    service: AlertService = Depends(get_alert_service),
):
    alerts = service.list(AlertFilters(status=status_filter, severity=severity))
    return [_alert_out(alert) for alert in alerts]


@router.post("/api/alerts/generate")
def api_generate_alerts(
    user: User = Depends(require_admin),
    service: AlertService = Depends(get_alert_service),
):
    return {"generated": service.generate_all()}


@router.post("/api/alerts/{alert_id}/resolve", response_model=AlertOut)
def api_resolve_alert(
    alert_id: int,
    user: User = Depends(require_admin),
    service: AlertService = Depends(get_alert_service),
):
    try:
        alert = service.resolve(alert_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _alert_out(alert)
