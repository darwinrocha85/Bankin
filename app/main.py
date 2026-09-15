"""Punto de entrada de la aplicación FastAPI.

Ejecutar con:  uvicorn app.main:app --reload
Documentación interactiva en:  http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.inbound.api.routers import cards, clients, manager, transactions
from app.adapters.outbound.persistence.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="BankIn (Python)",
    description="Demo de banco migrada de Java/Spring Boot a Python, con arquitectura hexagonal.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(clients.router)
app.include_router(cards.router)
app.include_router(transactions.router)
app.include_router(manager.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
