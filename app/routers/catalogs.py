from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.catalog_specs import CATALOG_SPECS, CatalogSpec
from app.dependencies import get_catalog_service
from app.flash import flash
from app.models import User
from app.security import require_admin
from app.services.catalog_service import CatalogService
from app.templating import templates

router = APIRouter(tags=["catalogs"])


def _spec_or_404(key: str) -> CatalogSpec:
    spec = CATALOG_SPECS.get(key)
    if spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catálogo no encontrado")
    return spec


@router.get("/catalogs")
def catalogs_index(
    request: Request,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    return templates.TemplateResponse(
        request,
        "catalogs/index.html",
        {
            "user": user,
            "specs": CATALOG_SPECS.values(),
            "counts": service.counts(),
        },
    )


@router.get("/catalogs/{key}")
def catalog_list(
    request: Request,
    key: str,
    q: str = "",
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    return templates.TemplateResponse(
        request,
        "catalogs/list.html",
        {
            "user": user,
            "spec": spec,
            "rows": service.rows(key, q),
            "q": q,
        },
    )


@router.get("/catalogs/{key}/new")
def catalog_new_form(
    request: Request,
    key: str,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    return templates.TemplateResponse(
        request,
        "catalogs/form.html",
        {
            "user": user,
            "spec": spec,
            "values": service.values_from(spec, None),
            "options": service.options_for(spec),
            "errors": [],
            "is_edit": False,
            "action_url": f"/catalogs/{key}/new",
            "cancel_url": f"/catalogs/{key}",
        },
    )


@router.post("/catalogs/{key}/new")
async def catalog_create(
    request: Request,
    key: str,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    form = await request.form()
    obj, errors, values = service.save(key, form)
    if errors:
        return templates.TemplateResponse(
            request,
            "catalogs/form.html",
            {
                "user": user,
                "spec": spec,
                "values": values,
                "options": service.options_for(spec),
                "errors": errors,
                "is_edit": False,
                "action_url": f"/catalogs/{key}/new",
                "cancel_url": f"/catalogs/{key}",
                },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    flash(request, f"{spec.singular.capitalize()} creado correctamente.", "success")
    return RedirectResponse(f"/catalogs/{key}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/catalogs/{key}/{entity_id}/edit")
def catalog_edit_form(
    request: Request,
    key: str,
    entity_id: int,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    obj = service.get(key, entity_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return templates.TemplateResponse(
        request,
        "catalogs/form.html",
        {
            "user": user,
            "spec": spec,
            "values": service.values_from(spec, obj),
            "options": service.options_for(spec),
            "errors": [],
            "is_edit": True,
            "action_url": f"/catalogs/{key}/{entity_id}/edit",
            "cancel_url": f"/catalogs/{key}",
        },
    )


@router.post("/catalogs/{key}/{entity_id}/edit")
async def catalog_update(
    request: Request,
    key: str,
    entity_id: int,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    form = await request.form()
    obj, errors, values = service.save(key, form, entity_id)
    if errors:
        return templates.TemplateResponse(
            request,
            "catalogs/form.html",
            {
                "user": user,
                "spec": spec,
                "values": values,
                "options": service.options_for(spec),
                "errors": errors,
                "is_edit": True,
                "action_url": f"/catalogs/{key}/{entity_id}/edit",
                "cancel_url": f"/catalogs/{key}",
                },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    flash(request, f"{spec.singular.capitalize()} actualizado correctamente.", "success")
    return RedirectResponse(f"/catalogs/{key}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/catalogs/{key}/{entity_id}/delete")
def catalog_delete(
    request: Request,
    key: str,
    entity_id: int,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    errors = service.delete(key, entity_id)
    if errors:
        flash(request, errors[0], "error")
    else:
        flash(request, f"{spec.singular.capitalize()} eliminado correctamente.", "success")
    return RedirectResponse(f"/catalogs/{key}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/catalogs/{key}")
def api_catalog_list(
    key: str,
    q: str = "",
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    spec = _spec_or_404(key)
    return [service.serialize(key, obj) for obj in service.list(key, q)]


@router.get("/api/catalogs/{key}/{entity_id}")
def api_catalog_detail(
    key: str,
    entity_id: int,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    _spec_or_404(key)
    obj = service.get(key, entity_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return service.serialize(key, obj)


@router.post("/api/catalogs/{key}")
def api_catalog_create(
    key: str,
    payload: dict = Body(...),
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    _spec_or_404(key)
    obj, errors, _ = service.save(key, payload)
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    return service.serialize(key, obj)


@router.put("/api/catalogs/{key}/{entity_id}")
def api_catalog_update(
    key: str,
    entity_id: int,
    payload: dict = Body(...),
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    _spec_or_404(key)
    obj, errors, _ = service.save(key, payload, entity_id)
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    return service.serialize(key, obj)


@router.delete("/api/catalogs/{key}/{entity_id}")
def api_catalog_delete(
    key: str,
    entity_id: int,
    user: User = Depends(require_admin),
    service: CatalogService = Depends(get_catalog_service),
):
    _spec_or_404(key)
    errors = service.delete(key, entity_id)
    if errors:
        raise HTTPException(status_code=409, detail=errors)
    return {"detail": "Registro eliminado correctamente", "id": entity_id}
