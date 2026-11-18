from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, SECRET_KEY, SESSION_MAX_AGE, APP_ENV
from app.database import init_database
from app.routers import (
    admin,
    alerts,
    audit,
    auth,
    billing,
    catalogs,
    costs,
    dashboard,
    documents,
    logistics,
    operations,
    portal,
    planning,
)
from app.templating import templates

init_database()

app = FastAPI(
    title="International Trade — Portal de comercio exterior",
    description=(
        "Portal de comercio exterior: operaciones, "
        "escenarios de costo, documentos, embarques, facturación y alertas."
    ),
    version="2.0.0",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=(APP_ENV == "production"),
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    is_api = request.url.path.startswith("/api")

    if exc.status_code == 401 and not is_api:
        return RedirectResponse("/login", status_code=303)

    if exc.status_code == 403 and not is_api:
        return templates.TemplateResponse(
            request,
            "errors/403.html",
            {"detail": exc.detail},
            status_code=403,
        )

    if exc.status_code == 404 and not is_api:
        return templates.TemplateResponse(
            request,
            "errors/404.html",
            {"detail": exc.detail},
            status_code=404,
        )

    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/")
def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok", "app": "International Trade"}


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(portal.router)
app.include_router(operations.router)
app.include_router(planning.router)
app.include_router(costs.router)
app.include_router(documents.router)
app.include_router(logistics.router)
app.include_router(billing.router)
app.include_router(alerts.router)
app.include_router(catalogs.router)
app.include_router(admin.router)
app.include_router(audit.router)
