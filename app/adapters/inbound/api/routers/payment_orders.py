"""Órdenes de pago multitramo: precio base en EUR, tramos en cualquier moneda.

- BankIn (banco propio): cobra de verdad cada tramo.
- Adyen (en proceso): registra la intención y la confirma el webhook (stub).
La orden solo pasa a PAID cuando paid_eur cubre total_eur.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_payment_order_service
from app.adapters.inbound.api.schemas import (
    AdyenIntentCreate,
    BankinTranchePay,
    PaymentOrderCreate,
    PaymentOrderOut,
    PaymentTrancheOut,
)
from app.adapters.inbound.api.security import require_api_key
from app.application.exchange_rate_service import ExchangeRateNotFoundError
from app.application.payment_order_service import (
    DuplicateReferenceError,
    OverpaymentError,
    PaymentOrderNotFoundError,
    PaymentOrderService,
    PaymentOrderSettledError,
    TrancheAlreadyConfirmedError,
    TrancheNotFoundError,
)
from app.application.transaction_service import (
    CardNotActiveError,
    CardNotFoundForTransactionError,
    InsufficientFundsError,
    InvalidAmountError,
)

router = APIRouter(prefix="/payment-orders", tags=["payment-orders"])


def _to_out(order, tranches) -> dict:
    return {
        "id": order.id,
        "reference": order.reference,
        "total_eur": order.total_eur,
        "paid_eur": order.paid_eur,
        "remaining_eur": round(order.total_eur - order.paid_eur, 2),
        "status": order.status,
        "note": order.note,
        "tranches": [PaymentTrancheOut.model_validate(t).model_dump() for t in tranches],
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


@router.post("", response_model=PaymentOrderOut, status_code=201,
             dependencies=[Depends(require_api_key)])
def create_order(payload: PaymentOrderCreate,
                 service: PaymentOrderService = Depends(get_payment_order_service)):
    try:
        order = service.create_order(payload.reference, payload.total_eur, payload.note)
    except DuplicateReferenceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(order, [])


@router.get("/{order_id}", response_model=PaymentOrderOut)
def get_order(order_id: int, service: PaymentOrderService = Depends(get_payment_order_service)):
    try:
        order = service.get_order(order_id)
        return _to_out(order, service.list_tranches(order_id))
    except PaymentOrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{order_id}/pay", response_model=PaymentOrderOut,
             dependencies=[Depends(require_api_key)])
def pay_bankin(order_id: int, payload: BankinTranchePay,
               service: PaymentOrderService = Depends(get_payment_order_service)):
    try:
        order, _ = service.pay_with_bankin(
            order_id, payload.card_id, payload.amount,
            payload.currency, payload.note, payload.idempotency_key)
        return _to_out(order, service.list_tranches(order_id))
    except PaymentOrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CardNotFoundForTransactionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PaymentOrderSettledError, OverpaymentError, InvalidAmountError,
            CardNotActiveError, InsufficientFundsError,
            ExchangeRateNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/adyen-intents", response_model=PaymentOrderOut,
             dependencies=[Depends(require_api_key)])
def adyen_intent(order_id: int, payload: AdyenIntentCreate,
                 service: PaymentOrderService = Depends(get_payment_order_service)):
    """Intención Adyen (en proceso): no cobra ni suma a paid_eur todavía."""
    try:
        order, _ = service.register_adyen_intent(
            order_id, payload.amount, payload.currency,
            payload.adyen_reference, payload.note, payload.idempotency_key)
        return _to_out(order, service.list_tranches(order_id))
    except PaymentOrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PaymentOrderSettledError, OverpaymentError,
            ExchangeRateNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adyen-tranches/{tranche_id}/confirm", response_model=PaymentOrderOut,
             dependencies=[Depends(require_api_key)])
def adyen_confirm(tranche_id: int,
                  service: PaymentOrderService = Depends(get_payment_order_service)):
    """Stub del webhook Adyen: confirma la intención y suma a paid_eur."""
    try:
        order, _ = service.confirm_adyen_tranche(tranche_id)
        return _to_out(order, service.list_tranches(order.id))
    except TrancheNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TrancheAlreadyConfirmedError, PaymentOrderSettledError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{order_id}/cancel", response_model=PaymentOrderOut,
             dependencies=[Depends(require_api_key)])
def cancel_order(order_id: int,
                 service: PaymentOrderService = Depends(get_payment_order_service)):
    try:
        order = service.cancel_order(order_id)
        return _to_out(order, service.list_tranches(order_id))
    except PaymentOrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PaymentOrderSettledError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
