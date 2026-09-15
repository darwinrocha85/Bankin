"""Rutas HTTP para Clientes. Ruta modernizada: /clients (antes /card/person*
en la versión Java).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.inbound.api.deps import get_client_service
from app.adapters.inbound.api.schemas import ClientCreate, ClientOut, ClientUpdate
from app.application.client_service import ClientNotFoundError, ClientService

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(
    name: str | None = Query(default=None, description="Filtra por nombre exacto"),
    service: ClientService = Depends(get_client_service),
):
    if name:
        return service.find_by_name(name)
    return service.list_clients()


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, service: ClientService = Depends(get_client_service)):
    try:
        return service.get_client(client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=ClientOut, status_code=201)
def create_client(payload: ClientCreate, service: ClientService = Depends(get_client_service)):
    return service.create_client(payload.name, payload.username, payload.product_id, payload.role)


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    service: ClientService = Depends(get_client_service),
):
    try:
        return service.update_client(client_id, payload.name, payload.username, payload.product_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, service: ClientService = Depends(get_client_service)):
    try:
        service.delete_client(client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
