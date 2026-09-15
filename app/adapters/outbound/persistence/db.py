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


def get_session():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
