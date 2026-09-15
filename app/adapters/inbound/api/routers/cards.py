"""Rutas HTTP para Tarjetas. Rutas modernizadas respecto a la versión Java:

    GET  /card/{productId}/number   ->  POST   /cards                (emitir)
    POST /card/enroll               ->  POST   /cards/{card_id}/activate
    DELETE /card/{cardId}           ->  DELETE /cards/{card_id}
    POST /card/balance              ->  PUT    /cards/{card_id}/balance
    GET  /card/balance/{cardId}     ->  GET    /cards/{card_id}/balance
    GET  /card/cardCredits          ->  GET    /cards
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.inbound.api.deps import get_card_service
from app.adapters.inbound.api.schemas import BalanceOut, BalanceUpdate, CardCreate, CardOut
from app.application.card_service import CardNotFoundError, CardService, ClientNotFoundForCardError

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("", response_model=list[CardOut])
def list_cards(
    client_id: int | None = Query(
        default=None, description="Filtra las tarjetas de un cliente (para la vista de cliente)"
    ),
    service: CardService = Depends(get_card_service),
):
    if client_id is not None:
        return service.list_cards_for_client(client_id)
    return service.list_cards()


@router.post("", response_model=CardOut, status_code=201)
def issue_card(payload: CardCreate, service: CardService = Depends(get_card_service)):
    try:
        return service.issue_card(payload.client_id)
    except ClientNotFoundForCardError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{card_id}", response_model=CardOut)
def get_card(card_id: str, service: CardService = Depends(get_card_service)):
    try:
        return service.get_card(card_id)
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{card_id}/activate", response_model=CardOut)
def activate_card(card_id: str, service: CardService = Depends(get_card_service)):
    try:
        return service.activate_card(card_id)
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{card_id}", response_model=CardOut)
def cancel_card(card_id: str, service: CardService = Depends(get_card_service)):
    try:
        return service.cancel_card(card_id)
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{card_id}/balance", response_model=CardOut)
def update_balance(
    card_id: str,
    payload: BalanceUpdate,
    service: CardService = Depends(get_card_service),
):
    try:
        return service.update_balance(card_id, payload.balance)
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{card_id}/balance", response_model=BalanceOut)
def get_balance(card_id: str, service: CardService = Depends(get_card_service)):
    try:
        return {"balance": service.get_balance(card_id)}
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
