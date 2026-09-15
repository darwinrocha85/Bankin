"""Rutas HTTP para Transacciones.

Incluye la recarga de saldo que pediste (POST /transactions/recharge),
además de compra y anulación. Rutas modernizadas respecto a Java:

    POST /transaction/purchase           -> POST   /transactions/purchase
    (no existía en Java)                 -> POST   /transactions/recharge   (NUEVO)
    POST /transaction/anulation          -> POST   /transactions/{id}/annul
    GET  /transaction/all                -> GET    /transactions
    GET  /transaction/{transactionId}    -> GET    /transactions/{id}

Tres reglas nuevas:
- POST /transactions/purchase es el endpoint de "cobro" pensado para que lo
  llamen OTRAS apps (dada una tarjeta y un monto, genera un cargo). Está
  protegido opcionalmente con X-Api-Key (ver security.py).
- POST /transactions/{id}/annul solo lo puede hacer el gerente: recibe
  manager_id igual que las rutas de /manager/* y valida el rol. Pensado
  para el panel de BankIn, no para que lo dispare otra app.
- POST /transactions/{id}/reverse es el equivalente pensado para OTRAS
  apps (igual que purchase): reversa una transacción dado su id, sin pedir
  manager_id, protegido opcionalmente con la misma X-Api-Key. Reutiliza
  exactamente la misma lógica de anulación que /annul (mismo método
  `TransactionService.annul`) -- son dos puertas de entrada distintas al
  mismo caso de uso, no dos implementaciones separadas.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.inbound.api.deps import get_manager_service, get_transaction_service
from app.adapters.inbound.api.schemas import PurchaseCreate, RechargeCreate, TransactionOut
from app.adapters.inbound.api.security import require_api_key
from app.application.manager_service import ManagerNotFoundError, ManagerService, NotAManagerError
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


@router.post(
    "/purchase",
    response_model=TransactionOut,
    status_code=201,
    dependencies=[Depends(require_api_key)],
)
def purchase(payload: PurchaseCreate, service: TransactionService = Depends(get_transaction_service)):
    try:
        return service.purchase(payload.card_id, payload.amount, payload.note)
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
def annul(
    transaction_id: int,
    manager_id: int = Query(
        ..., description="Id del cliente que actúa como gerente; solo el gerente puede anular"
    ),
    service: TransactionService = Depends(get_transaction_service),
    manager_service: ManagerService = Depends(get_manager_service),
):
    try:
        manager_service.require_manager(manager_id)
    except ManagerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotAManagerError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        return service.annul(transaction_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TransactionAlreadyAnnulledError, InsufficientFundsError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{transaction_id}/reverse",
    response_model=TransactionOut,
    dependencies=[Depends(require_api_key)],
)
def reverse(transaction_id: int, service: TransactionService = Depends(get_transaction_service)):
    """Reversa una transacción por su id -- pensado para que lo llame OTRA
    app (ej. naveSpace, al cancelar una entrada que ya se había cobrado),
    no el panel de BankIn (para eso está /annul, con gerente). Reutiliza la
    misma regla de negocio que /annul: una compra revertida devuelve el
    dinero, una recarga revertida lo retira (y falla si ese dinero ya se
    gastó en una compra posterior).
    """
    try:
        return service.annul(transaction_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TransactionAlreadyAnnulledError, InsufficientFundsError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
