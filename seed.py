"""Script de inicialización del sistema.

Crea las tablas de la base de datos y el usuario administrador inicial.
El administrador no puede registrarse públicamente: se crea con este seed
y su contraseña se almacena únicamente como hash (bcrypt).

Uso:
    python seed.py
"""

import os

from app.constants import ROLE_ADMIN
from app.database import Base, SessionLocal, engine, ensure_operation_user_column
from app.models import User
from app.security import hash_password

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def main() -> None:
    if not ADMIN_USERNAME.strip():
        raise SystemExit("ADMIN_USERNAME no puede estar vacío.")
    if len(ADMIN_PASSWORD) < 6:
        raise SystemExit("ADMIN_PASSWORD debe tener al menos 6 caracteres.")

    Base.metadata.create_all(bind=engine)
    ensure_operation_user_column()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if existing is not None:
            print(f"El administrador '{ADMIN_USERNAME}' ya existe. No se realizaron cambios.")
            return

        admin = User(
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=ROLE_ADMIN,
        )
        db.add(admin)
        db.commit()

        print("Base de datos inicializada correctamente.")
        print(f"Usuario administrador creado: {ADMIN_USERNAME}")
        print("La contraseña se almacenó como hash bcrypt.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
