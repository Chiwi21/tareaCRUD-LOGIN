from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import require_admin
from app.templating import templates

router = APIRouter(tags=["admin"])


def get_user_or_404(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return target


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "person_type": user.person_type,
        "full_name": user.full_name,
        "cedula": user.cedula,
        "ruc": user.ruc,
        "razon_social": user.razon_social,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/admin/users")
def list_users(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse(request, "admin/users.html", {"user": user, "users": users})


@router.get("/admin/users/{user_id}")
def user_detail(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    return templates.TemplateResponse(request, "admin/user_detail.html", {"user": user, "target": target})


@router.post("/admin/users/{user_id}/delete")
def delete_user_html(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    if target.id == user.id:
        users = db.query(User).order_by(User.id).all()
        return templates.TemplateResponse(
            request,
            "admin/users.html",
            {
                "user": user,
                "users": users,
                "error": "No puede eliminar su propia cuenta de administrador.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    db.delete(target)
    db.commit()
    return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/admin/users")
def api_list_users(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [serialize_user(u) for u in users]


@router.get("/api/admin/users/{user_id}")
def api_user_detail(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    return serialize_user(target)


@router.delete("/api/admin/users/{user_id}")
def api_delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = get_user_or_404(db, user_id)
    if target.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta de administrador.",
        )
    db.delete(target)
    db.commit()
    return {"detail": "Usuario eliminado correctamente", "id": user_id}
