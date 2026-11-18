"""Pantallas informativas y servicios de primera etapa del portal."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from app.core.import_estimator import calculate_import_costs
from app.content.glossary import GLOSSARY
from app.database import get_db
from app.flash import flash
from app.models import SupportTicket, User
from app.security import require_admin, require_login
from app.templating import templates

router = APIRouter(tags=["international-trade-portal"])

DEFAULT_COSTS = {
    "budget": "10000", "quantity": "1000", "unit_price": "5",
    "origin_charges":"0", "freight":"1000", "insurance_pct":"1",
    "insurance_amount":"", "duty_pct":"10", "fodinfa_pct":"0.5",
    "vat_pct":"15", "ice":"0", "isd":"0", "destination_charges":"200",
    "broker":"150", "delivery":"100", "other":"50",
}

@router.get("/herramientas/calculadora")
def calculator_page(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(request, "portal/calculator.html", {
        "user": user, "values": DEFAULT_COSTS, "result": calculate_import_costs(DEFAULT_COSTS), "is_example": True,
    })

@router.post("/herramientas/calculadora")
async def calculator_result(request: Request, user: User = Depends(require_login)):
    form = await request.form()
    values = {key: str(form.get(key, '' if key == 'insurance_amount' else '0')) for key in DEFAULT_COSTS}
    try:
        result = calculate_import_costs(values)
        error = None
    except ValueError as exc:
        result = None
        error = str(exc)
    return templates.TemplateResponse(request, "portal/calculator.html", {
        "user": user, "values": values, "result": result, "error": error, "is_example":False,
    }, status_code=400 if error else 200)

@router.get("/informacion")
def information(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(request, "portal/information.html", {"user": user, "glossary": GLOSSARY})

@router.get("/ayuda")
def help_page(request: Request, user: User = Depends(require_login), db: Session = Depends(get_db)):
    tickets = db.query(SupportTicket).filter(SupportTicket.user_id == user.id).order_by(SupportTicket.id.desc()).limit(10).all()
    return templates.TemplateResponse(request, "portal/help.html", {"user": user, "tickets": tickets, "values": {}})

@router.post("/ayuda")
def help_submit(
    request: Request, subject: str = Form(...), message: str = Form(...),
    user: User = Depends(require_login), db: Session = Depends(get_db),
):
    subject, message = subject.strip(), message.strip()
    errors = []
    if not 4 <= len(subject) <= 120:
        errors.append("El asunto debe contener entre 4 y 120 caracteres.")
    if not 10 <= len(message) <= 3000:
        errors.append("El mensaje debe contener entre 10 y 3.000 caracteres.")
    if errors:
        tickets = db.query(SupportTicket).filter(SupportTicket.user_id == user.id).order_by(SupportTicket.id.desc()).limit(10).all()
        return templates.TemplateResponse(request, "portal/help.html", {
            "user": user, "tickets": tickets, "errors": errors,
            "values": {"subject": subject, "message": message},
        }, status_code=status.HTTP_400_BAD_REQUEST)
    db.add(SupportTicket(user_id=user.id, subject=subject, message=message))
    db.commit()
    flash(request, "Solicitud registrada. Se guardó en el centro de soporte del portal.", "success")
    return RedirectResponse("/ayuda", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin/soporte")
def support_inbox(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tickets = db.query(SupportTicket).options(joinedload(SupportTicket.user)).order_by(SupportTicket.id.desc()).limit(200).all()
    return templates.TemplateResponse(request, "portal/support_admin.html", {"user": user, "tickets": tickets})
