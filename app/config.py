import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")
SESSION_MAX_AGE = 60 * 60 * 8
