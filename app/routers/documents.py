from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError as PydanticValidationError

from app.dependencies import get_document_service
from app.flash import flash
from app.models import User
from app.repositories.protocols import DocumentFilters
from app.schemas import DocumentCreate, DocumentOut, DocumentUpdate
from app.security import require_admin
from app.services.document_service import DocumentService
from app.services.errors import NotFoundError, ValidationError
from app.templating import templates

router = APIRouter(tags=["documents"])


def _date_or_none(value: str | None):
    return date.fromisoformat(value) if value else None


def _document_out(document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        operation_id=document.operation_id,
        document_type_id=document.document_type_id,
        document_type_name=document.document_type.name if document.document_type else "",
        name=document.name,
        status=document.status,
        file_url=document.file_url,
        issue_date=document.issue_date,
        expiry_date=document.expiry_date,
        notes=document.notes,
    )


def _render_form(
    request: Request,
    user: User,
    service: DocumentService,
    values: dict,
    errors: list[str],
    document=None,
):
    context = service.form_context()
    return templates.TemplateResponse(
        request,
        "documents/form.html",
        {
            "user": user,
            "values": values,
            "errors": errors,
            "document": document,
            "is_edit": document is not None,
            "title": "Editar documento" if document else "Nuevo documento",
            "action_url": f"/documents/{document.id}/edit" if document else "/documents/new",
            "cancel_url": f"/operations/{document.operation_id}" if document else "/documents",
            **context,
        },
        status_code=status.HTTP_400_BAD_REQUEST if errors else status.HTTP_200_OK,
    )


@router.get("/documents")
def list_documents(
    request: Request,
    q: str = "",
    status_filter: str = "",
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    documents = service.list(
        DocumentFilters(q=q, status=status_filter, operation_id=operation_id)
    )
    return templates.TemplateResponse(
        request,
        "documents/list.html",
        {
            "user": user,
            "documents": documents,
            "q": q,
            "status_filter": status_filter,
            "operation_id": operation_id or "",
        },
    )


@router.get("/documents/new")
def new_document_form(
    request: Request,
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    values = {
        "operation_id": operation_id or "",
        "status": "PENDING",
        "issue_date": date.today().isoformat(),
        "expiry_date": "",
    }
    return _render_form(request, user, service, values, [])


@router.post("/documents/new")
async def create_document(
    request: Request,
    operation_id: int = Form(...),
    document_type_id: int = Form(...),
    name: str = Form(...),
    status_value: str = Form("PENDING", alias="status"),
    file_url: str = Form(""),
    issue_date: str = Form(""),
    expiry_date: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    form = await request.form()
    values = {
        "operation_id": operation_id,
        "document_type_id": document_type_id,
        "name": name,
        "status": status_value,
        "file_url": file_url,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "notes": notes,
    }
    try:
        data = DocumentCreate(
            operation_id=operation_id,
            document_type_id=document_type_id,
            name=name,
            status=status_value,
            file_url=file_url or None,
            issue_date=_date_or_none(issue_date),
            expiry_date=_date_or_none(expiry_date),
            notes=notes or None,
        )
        service.create(data, user.id)
    except (ValueError, PydanticValidationError):
        return _render_form(request, user, service, values, ["Revise las fechas y los datos."])
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors)
    flash(request, "Documento registrado correctamente.", "success")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/documents/{document_id}/edit")
def edit_document_form(
    request: Request,
    document_id: int,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    document = service.get(document_id)
    values = {
        "operation_id": document.operation_id,
        "document_type_id": document.document_type_id,
        "name": document.name,
        "status": document.status,
        "file_url": document.file_url or "",
        "issue_date": document.issue_date.isoformat() if document.issue_date else "",
        "expiry_date": document.expiry_date.isoformat() if document.expiry_date else "",
        "notes": document.notes or "",
    }
    return _render_form(request, user, service, values, [], document)


@router.post("/documents/{document_id}/edit")
async def update_document(
    request: Request,
    document_id: int,
    document_type_id: int = Form(...),
    name: str = Form(...),
    status_value: str = Form(..., alias="status"),
    file_url: str = Form(""),
    issue_date: str = Form(""),
    expiry_date: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    document = service.get(document_id)
    values = {
        "operation_id": document.operation_id,
        "document_type_id": document_type_id,
        "name": name,
        "status": status_value,
        "file_url": file_url,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "notes": notes,
    }
    try:
        data = DocumentUpdate(
            document_type_id=document_type_id,
            name=name,
            status=status_value,
            file_url=file_url or None,
            issue_date=_date_or_none(issue_date),
            expiry_date=_date_or_none(expiry_date),
            notes=notes or None,
        )
        service.update(document_id, data, user.id)
    except (ValueError, PydanticValidationError):
        return _render_form(request, user, service, values, ["Revise las fechas y los datos."], document)
    except ValidationError as exc:
        return _render_form(request, user, service, values, exc.errors, document)
    flash(request, "Documento actualizado correctamente.", "success")
    return RedirectResponse(f"/operations/{document.operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/documents/{document_id}/delete")
def delete_document(
    request: Request,
    document_id: int,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    document = service.get(document_id)
    operation_id = document.operation_id
    service.delete(document_id, user.id)
    flash(request, "Documento eliminado.", "success")
    return RedirectResponse(f"/operations/{operation_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/documents", response_model=list[DocumentOut])
def api_list_documents(
    q: str = "",
    status_filter: str = "",
    operation_id: int | None = None,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    documents = service.list(
        DocumentFilters(q=q, status=status_filter, operation_id=operation_id)
    )
    return [_document_out(document) for document in documents]


@router.get("/api/documents/{document_id}", response_model=DocumentOut)
def api_document_detail(
    document_id: int,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    return _document_out(service.get(document_id))


@router.post("/api/documents", response_model=DocumentOut)
def api_create_document(
    payload: DocumentCreate,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    try:
        document = service.create(payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _document_out(document)


@router.put("/api/documents/{document_id}", response_model=DocumentOut)
def api_update_document(
    document_id: int,
    payload: DocumentUpdate,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    try:
        document = service.update(document_id, payload, user.id)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors) from exc
    return _document_out(document)


@router.delete("/api/documents/{document_id}")
def api_delete_document(
    document_id: int,
    user: User = Depends(require_admin),
    service: DocumentService = Depends(get_document_service),
):
    try:
        service.delete(document_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Documento eliminado correctamente", "id": document_id}
