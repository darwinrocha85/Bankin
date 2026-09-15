"""Rutas HTTP para el Gerente. No existían en la versión Java.

Sin login real, como acordamos: cada request pasa `manager_id` (el id del
Cliente que dice ser el gerente) como query param, y el servicio verifica
que ese cliente exista y tenga role=MANAGER antes de responder. Si no,
devuelve 403 (existe pero no es gerente) o 404 (no existe ese cliente).

Para crear el primer gerente: POST /clients con "role": "MANAGER" en el
body (ver ClientCreate).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.inbound.api.deps import get_manager_service
from app.adapters.inbound.api.schemas import (
    BankOverviewOut,
    CardOut,
    ClientOut,
    ClientOverviewOut,
    TransactionOut,
)
from app.application.manager_service import ManagerNotFoundError, ManagerService, NotAManagerError

router = APIRouter(prefix="/manager", tags=["manager"])


def _handle_auth_errors(exc: Exception):
    if isinstance(exc, ManagerNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, NotAManagerError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    raise exc


@router.get("/overview", response_model=BankOverviewOut)
def bank_overview(
    manager_id: int = Query(..., description="Id del cliente que actúa como gerente"),
    service: ManagerService = Depends(get_manager_service),
):
    try:
        return service.get_bank_overview(manager_id)
    except (ManagerNotFoundError, NotAManagerError) as exc:
        _handle_auth_errors(exc)


@router.get("/clients", response_model=list[ClientOut])
def all_clients(
    manager_id: int = Query(...),
    service: ManagerService = Depends(get_manager_service),
):
    try:
        return service.list_all_clients(manager_id)
    except (ManagerNotFoundError, NotAManagerError) as exc:
        _handle_auth_errors(exc)


@router.get("/clients/{client_id}", response_model=ClientOverviewOut)
def client_overview(
    client_id: int,
    manager_id: int = Query(...),
    service: ManagerService = Depends(get_manager_service),
):
    """Vista 360 de un cliente: sus datos, todas sus tarjetas y todas sus
    transacciones -- la info completa que el gerente puede ver.
    """
    try:
        return service.get_client_overview(manager_id, client_id)
    except (ManagerNotFoundError, NotAManagerError) as exc:
        _handle_auth_errors(exc)


@router.get("/cards", response_model=list[CardOut])
def all_cards(
    manager_id: int = Query(...),
    service: ManagerService = Depends(get_manager_service),
):
    try:
        return service.list_all_cards(manager_id)
    except (ManagerNotFoundError, NotAManagerError) as exc:
        _handle_auth_errors(exc)


@router.get("/transactions", response_model=list[TransactionOut])
def all_transactions(
    manager_id: int = Query(...),
    service: ManagerService = Depends(get_manager_service),
):
    try:
        return service.list_all_transactions(manager_id)
    except (ManagerNotFoundError, NotAManagerError) as exc:
        _handle_auth_errors(exc)
