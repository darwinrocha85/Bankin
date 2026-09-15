"""Rutas HTTP para Transacciones.

Incluye la recarga de saldo que pediste (POST /transactions/recharge),
además de compra y anulación. Rutas modernizadas respecto a Java:

    POST /transaction/purchase           -> POST   /transactions/purchase
    (no existía en Java)                 -> POST   /transactions/recharge   (NUEVO)
    POST /transaction/anulation          -> POST   /transactions/{id}/annul
    GET  /transaction/all                -> GET    /transactions
    GET  /transaction/{transactionId}    -> GET    /transactions/{id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_transaction_service
from app.adapters.inbound.api.schemas import PurchaseCreate, RechargeCreate, TransactionOut
from app.application.transaction_service import (
    CardNotActiveError,
    CardNotFoundForTransactionError,
    InsufficientFundsError,
    InvalidAmountError,
    TransactionAlreadyAnnulledError,
    TransactionNotFoundError,
    TransactionService,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(service: TransactionService = Depends(get_transaction_service)):
    return service.list_all()


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, service: TransactionService = Depends(get_transaction_service)):
    try:
        return service.get(transaction_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/card/{card_id}", response_model=list[TransactionOut])
def list_transactions_for_card(card_id: str, service: TransactionService = Depends(get_transaction_service)):
    return service.list_for_card(card_id)


@router.post("/purchase", response_model=TransactionOut, status_code=201)
def purchase(payload: PurchaseCreate, service: TransactionService = Depends(get_transaction_service)):
    try:
        return service.purchase(payload.card_id, payload.amount)
    except CardNotFoundForTransactionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (CardNotActiveError, InsufficientFundsError, InvalidAmountError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recharge", response_model=TransactionOut, status_code=201)
def recharge(payload: RechargeCreate, service: TransactionService = Depends(get_transaction_service)):
    """Recarga saldo a una tarjeta. Queda registrada como transacción, con
    su fecha y su rastro de auditoría -- así la tarjeta puede recargar saldo
    de una forma que se puede consultar y, si hace falta, anular.
    """
    try:
        return service.recharge(payload.card_id, payload.amount)
    except CardNotFoundForTransactionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (CardNotActiveError, InvalidAmountError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{transaction_id}/annul", response_model=TransactionOut)
def annul(transaction_id: int, service: TransactionService = Depends(get_transaction_service)):
    try:
        return service.annul(transaction_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TransactionAlreadyAnnulledError, InsufficientFundsError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
