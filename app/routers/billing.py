from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.dependencies import get_billing_service
from app.flash import flash
from app.models import User
from app.repositories.protocols import InvoiceFilters
from app.schemas import InvoiceCreate, InvoiceOut, PaymentCreate, PaymentOut
from app.security import require_admin
from app.services.billing_service import BillingService
from app.services.errors import NotFoundError, ValidationError
from app.templating import templates

router = APIRouter(tags=["billing"])


def _date_or_none(value: str | None):
    return date.fromisoformat(value) if value else None


def _invoice_out(invoice) -> InvoiceOut:
    return InvoiceOut(
        id=invoice.id,
        number=invoice.number,
        operation_id=invoice.operation_id,
        operation_code=invoice.operation.code if invoice.operation else "",
        currency=invoice.currency.code if invoice.currency else None,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        paid_amount=invoice.paid_amount,
        balance=invoice.balance,
        status=invoice.status,
        notes=invoice.notes,
        payments=[
            PaymentOut(
                id=payment.id,
                amount=payment.amount,
                payment_date=payment.payment_date,
                method=payment.method,
                reference=payment.reference,
                notes=payment.notes,
            )
            for payment in invoice.payments
        ],
    )


def _render_form(
    request: Request,
    user: User,
    service: BillingService,
    values: dict,
    errors: list[str],
):
    context = service.form_context()
    return templates.TemplateResponse(
        request,
        "invoices/form.html",
        {
            "user": user,
            "values": values,
            "errors": errors,
            "title": "Nueva factura",
            "action_url": "/invoices/new",
            "cancel_url": "/invoices",
            **context,
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


@router.get("/invoices")
def list_invoices(
    request: Request,
    q: str = "",
    status_filter: str = "",
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    invoices = service.list(
        InvoiceFilters(q=q, status=status_filter, operation_id=operation_id)
    )
    return templates.TemplateResponse(
        request,
        "invoices/list.html",
        {
            "user": user,
            "invoices": invoices,
            "q": q,
            "status_filter": status_filter,
            "operation_id": operation_id or "",
        },
    )


@router.get("/invoices/new")
def new_invoice_form(
    request: Request,
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    values = {
        "operation_id": operation_id or "",
        "issue_date": date.today().isoformat(),
        "due_date": "",
        "tax_amount": "0",
    }
    return _render_form(request, user, service, values, [])


@router.post("/invoices/new")
async def create_invoice(
    request: Request,
    operation_id: int = Form(...),
    currency_id: str = Form(""),
    issue_date: str = Form(...),
    due_date: str = Form(""),
    tax_amount: str = Form("0"),
    notes: str = Form(""),
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    values = {
        "operation_id": operation_id,
        "currency_id": currency_id,
        "issue_date": issue_date,
        "due_date": due_date,
        "tax_amount": tax_amount,
        "notes": notes,
    }
    try:
        data = InvoiceCreate(
            operation_id=operation_id,
            currency_id=int(currency_id) if currency_id else None,
            issue_date=date.fromisoformat(issue_date),
            due_date=_date_or_none(due_date),
            tax_amount=tax_amount or "0",
            notes=notes or None,
        )
        invoice = service.create(data, user.id)
    except (ValueError, PydanticValidationError):
        return _render_form(request, user, service, values, ["Revise las fechas y el impuesto."])
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors)
    flash(request, f"Factura {invoice.number} creada.", "success")
    return RedirectResponse(f"/invoices/{invoice.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/invoices/{invoice_id}")
def invoice_detail(
    request: Request,
    invoice_id: int,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    invoice = service.get(invoice_id)
    return templates.TemplateResponse(
        request,
        "invoices/detail.html",
        {"user": user, "invoice": invoice, "today": date.today()},
    )


@router.post("/invoices/{invoice_id}/payments")
def add_payment(
    request: Request,
    invoice_id: int,
    amount: str = Form(...),
    payment_date: str = Form(...),
    method: str = Form("TRANSFER"),
    reference: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    try:
        data = PaymentCreate(
            invoice_id=invoice_id,
            amount=amount,
            payment_date=date.fromisoformat(payment_date),
            method=method,
            reference=reference or None,
            notes=notes or None,
        )
        service.add_payment(data, user.id)
        flash(request, "Pago registrado correctamente.", "success")
    except (ValueError, PydanticValidationError):
        flash(request, "Revise el monto y la fecha del pago.", "error")
    except ValidationError as exc:
        flash(request, exc.errors[0], "error")
    return RedirectResponse(f"/invoices/{invoice_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/payments/{payment_id}/delete")
def delete_payment(
    request: Request,
    payment_id: int,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    # El repositorio conoce la factura; se obtiene antes de borrar para redirigir.
    try:
        service.delete_payment(payment_id, user.id)
        flash(request, "Pago eliminado.", "success")
    except (ValidationError, NotFoundError) as exc:
        flash(request, str(exc), "error")
    return RedirectResponse("/invoices", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/invoices/{invoice_id}/delete")
def delete_invoice(
    request: Request,
    invoice_id: int,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    service.delete_invoice(invoice_id, user.id)
    flash(request, "Factura eliminada.", "success")
    return RedirectResponse("/invoices", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/invoices", response_model=list[InvoiceOut])
def api_list_invoices(
    q: str = "",
    status_filter: str = "",
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    invoices = service.list(
        InvoiceFilters(q=q, status=status_filter, operation_id=operation_id)
    )
    return [_invoice_out(invoice) for invoice in invoices]


@router.get("/api/invoices/{invoice_id}", response_model=InvoiceOut)
def api_invoice_detail(
    invoice_id: int,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    return _invoice_out(service.get(invoice_id))


@router.post("/api/invoices", response_model=InvoiceOut)
def api_create_invoice(
    payload: InvoiceCreate,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    try:
        invoice = service.create(payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _invoice_out(invoice)


@router.post("/api/invoices/{invoice_id}/payments", response_model=PaymentOut)
def api_add_payment(
    invoice_id: int,
    payload: PaymentCreate,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    if payload.invoice_id != invoice_id:
        raise HTTPException(status_code=400, detail="La factura no coincide con la ruta.")
    try:
        payment = service.add_payment(payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return PaymentOut(
        id=payment.id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        method=payment.method,
        reference=payment.reference,
        notes=payment.notes,
    )


@router.delete("/api/invoices/{invoice_id}")
def api_delete_invoice(
    invoice_id: int,
    user: User = Depends(require_admin),
    service: BillingService = Depends(get_billing_service),
):
    try:
        service.delete_invoice(invoice_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Factura eliminada correctamente", "id": invoice_id}
