from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, SECRET_KEY, SESSION_MAX_AGE
from app.controllers import (
    admin_controller,
    auth_controller,
    dashboard_controller,
    operation_controller,
)
from app.database import Base, engine
from app.templating import templates

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Import/Export - Tarea 3 CRUD/Login")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
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

    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/")
def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/login", status_code=303)


app.include_router(auth_controller.router)
app.include_router(dashboard_controller.router)
app.include_router(operation_controller.router)
app.include_router(admin_controller.router)
