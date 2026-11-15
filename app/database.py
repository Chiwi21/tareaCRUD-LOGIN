import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BASE_DIR

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://") :]
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://") :]
else:
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def legacy_operations_table() -> bool:
    """True si la base todavía tiene el esquema antiguo de operaciones."""
    inspector = inspect(engine)
    if "operations" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("operations")}
    return "product" in columns and "code" not in columns


def init_database() -> None:
    """Crea las tablas y verifica que no se esté usando el esquema anterior."""
    from app import models  # noqa: F401  (registra los 22 modelos en Base.metadata)

    if legacy_operations_table():
        raise RuntimeError(
            "Se detectó el esquema antiguo de operaciones. "
            "Ejecute primero: python migrate_legacy.py"
        )
    Base.metadata.create_all(bind=engine)


def reset_database() -> None:
    """Elimina todas las tablas y las vuelve a crear (solo para desarrollo)."""
    from app import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
