"""Rutas HTTP para Tasas de cambio.

- GET /exchange-rates: tabla vigente (una fila por par), pública para que
  las apps externas puedan consultar antes de cobrar.
- GET /exchange-rates/history: histórico (más recientes primero),
  filtrable por par. Público.
- GET /exchange-rates/convert: convierte un monto con la tasa vigente
  (útil para cotizar antes de cobrar). Público.
- POST /exchange-rates: carga una tasa nueva. Solo gerente
  (`?manager_id=`), igual que el resto de rutas de gerente. Cada carga
  crea una fila nueva: el histórico se conserva, nunca se edita.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.adapters.inbound.api.deps import get_exchange_rate_service, get_manager_service
from app.adapters.inbound.api.schemas import ConvertOut, ExchangeRateCreate, ExchangeRateOut
from app.application.exchange_rate_service import (
    ExchangeRateNotFoundError,
    ExchangeRateService,
    InvalidRateError,
)
from app.application.manager_service import ManagerNotFoundError, ManagerService, NotAManagerError
from app.domain.models import Currency

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("", response_model=list[ExchangeRateOut])
def current_table(service: ExchangeRateService = Depends(get_exchange_rate_service)):
    return service.current_table()


@router.get("/history", response_model=list[ExchangeRateOut])
def history(
    base_currency: Currency | None = Query(default=None, description="Filtra por moneda base"),
    target_currency: Currency | None = Query(default=None, description="Filtra por moneda destino"),
    limit: int = Query(default=100, ge=1, le=1000),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
):
    return service.history(base_currency, target_currency, limit)


@router.get("/convert", response_model=ConvertOut)
def convert(
    amount: float = Query(..., gt=0),
    base_currency: Currency = Query(...),
    target_currency: Currency = Query(...),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
):
    try:
        converted, resolved = service.convert(amount, base_currency, target_currency)
    except ExchangeRateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "amount": amount,
        "base_currency": base_currency,
        "target_currency": target_currency,
        "converted_amount": converted,
        "rate_used": resolved.rate,
        "inverted": resolved.inverted,
    }


@router.post("", response_model=ExchangeRateOut, status_code=201)
def create_rate(
    payload: ExchangeRateCreate,
    manager_id: int = Query(..., description="Id del cliente que actúa como gerente"),
    service: ExchangeRateService = Depends(get_exchange_rate_service),
    manager_service: ManagerService = Depends(get_manager_service),
):
    try:
        manager_service.require_manager(manager_id)
    except ManagerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotAManagerError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        return service.create_rate(
            payload.base_currency, payload.target_currency, payload.rate, created_by=manager_id
        )
    except InvalidRateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
