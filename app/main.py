"""Punto de entrada de la aplicación FastAPI.

Ejecutar en local:  uvicorn app.main:app --reload
Documentación interactiva:  http://localhost:8000/docs

Configuración por entorno (variables de entorno; ver .env.example):

    ENVIRONMENT       "local" (default) o "production". Solo informativo,
                      se expone en GET /health para poder verificar rápido
                      contra qué entorno está corriendo el frontend.
    ALLOWED_ORIGINS   Orígenes adicionales permitidos por CORS, separados
                      por coma (por ejemplo la URL de Firebase Hosting).
                      Los orígenes de desarrollo local siempre están
                      permitidos, así que no hace falta incluirlos aquí.
    AUTO_SEED         "true" para poblar la base con datos de prueba al
                      arrancar si está vacía. Pensado para Render: el disco
                      del plan gratuito es efímero (se borra en cada
                      redeploy o reinicio), así que sin esto la app
                      arrancaría sin datos cada vez.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Carga variables desde un archivo .env si existe (uso local). En Render las
# variables de entorno se configuran desde su dashboard, no hace falta un
# .env ahí -- load_dotenv() simplemente no encuentra el archivo y no hace
# nada, sin error.
load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.adapters.inbound.api.routers import cards, clients, manager, transactions  # noqa: E402
from app.adapters.outbound.persistence.db import init_db  # noqa: E402

ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")

# Orígenes de desarrollo local: siempre permitidos, en cualquier entorno,
# para no tener que tocar variables de entorno solo para probar en local
# contra un backend ya desplegado.
#
# Va por regex (cualquier puerto en localhost/127.0.0.1) en vez de una lista
# fija con el puerto 5173 -- si tienes más de un proyecto Vite corriendo a
# la vez (naveSpace, el portafolio, BankIn...), el que arranca después cae
# en otro puerto (5174, 5175...) porque 5173 ya está ocupado, y con una
# lista fija ese preflight se rechazaba con 400.
LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1):\d+$"

# Orígenes adicionales (por ejemplo, la URL de Firebase Hosting una vez
# desplegado el frontend) vienen de una variable de entorno para no tener
# que tocar código cada vez que cambian.
_extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
EXTRA_ORIGINS = [origin.strip() for origin in _extra_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.environ.get("AUTO_SEED", "").lower() == "true":
        from seed_data import run_seed

        run_seed()
    yield


app = FastAPI(
    title="BankIn (Python)",
    description="Demo de banco migrada de Java/Spring Boot a Python, con arquitectura hexagonal.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=EXTRA_ORIGINS,
    allow_origin_regex=LOCAL_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router)
app.include_router(cards.router)
app.include_router(transactions.router)
app.include_router(manager.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "environment": ENVIRONMENT}
