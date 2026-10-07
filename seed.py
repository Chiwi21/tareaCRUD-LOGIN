"""Script de inicialización del sistema.

Crea las tablas de la base de datos y el usuario administrador inicial.
El administrador no puede registrarse públicamente: se crea con este seed
y su contraseña se almacena únicamente como hash (bcrypt).

Uso:
    python seed.py
"""

from app.constants import ROLE_ADMIN
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def main() -> None:
    Base.metadata.create_all(bind=engine)

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
        db.refresh(admin)

        print("Base de datos inicializada correctamente.")
        print(f"Usuario administrador creado: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        print(f"Hash almacenado (nunca la contraseña en texto plano): {admin.password_hash}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
