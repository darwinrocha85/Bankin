"""Configuración de la base de datos SQLite.

Usamos un archivo en disco (bankin.db), NO ":memory:", precisamente para que
los datos persistan entre reinicios del servidor -- igual que pediste.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = os.environ.get("BANKIN_DB_PATH", "bankin.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread=False porque FastAPI puede usar la conexión desde
# distintos hilos; SQLite lo soporta bien para un demo como este.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Crea las tablas que falten. Se llama al arrancar la app."""
    # Importar los modelos ORM aquí asegura que estén registrados en Base
    # antes de crear las tablas.
    from app.adapters.outbound.persistence import orm_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()


def _migrate_add_missing_columns() -> None:
    """create_all() solo crea tablas que falten, no columnas nuevas en una
    tabla que ya existía (por ejemplo, un bankin.db local de antes de que
    existiera la columna "note" en transactions). Este chequeo simple la
    agrega si hace falta, para no obligar a borrar el archivo .db a mano.
    En Render (disco efímero) esto no aplica -- ahí cada deploy arranca con
    una tabla nueva que ya incluye la columna.
    """
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(transactions)")}
        if "note" not in existing:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN note VARCHAR")
            conn.commit()


def get_session():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
