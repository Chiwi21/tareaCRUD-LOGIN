import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

APP_ENV = os.getenv("APP_ENV", "local")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")
if APP_ENV == "production":
    if len(SECRET_KEY) < 32 or SECRET_KEY == "dev-secret-key-cambiar-en-produccion":
        raise RuntimeError("En producción es obligatorio definir una SECRET_KEY segura.")
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("En producción es obligatorio definir DATABASE_URL para PostgreSQL.")
SESSION_MAX_AGE = 60 * 60 * 8
