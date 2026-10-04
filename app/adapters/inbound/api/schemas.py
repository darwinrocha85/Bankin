"""Esquemas Pydantic: son los DTOs que entran/salen por HTTP.
Se mantienen separados del modelo de dominio para que la API pueda cambiar
de forma sin afectar al dominio, y viceversa.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import CardStatus, Currency, Role, TransactionStatus, TransactionType
from app.domain.models import PaymentOrderStatus, PaymentProvider


class ClientCreate(BaseModel):
    name: str
    username: str
    product_id: int
    role: Role = Role.CLIENT


class ClientUpdate(BaseModel):
    name: str
    username: str
    product_id: int


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    product_id: int
    role: Role
    created_at: datetime


class CardCreate(BaseModel):
    client_id: int
    currency: Currency = Currency.COP


class BalanceUpdate(BaseModel):
    balance: float


class BalanceOut(BaseModel):
    balance: float
    currency: Currency


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    card_id: str
    cardholder_name: str
    date_expires: str
    currency: Currency
    balance: float
    status: CardStatus
    created_at: datetime
    updated_at: datetime


class PurchaseCreate(BaseModel):
    card_id: str
    amount: float
    currency: Currency | None = Field(
        default=None,
        description=(
            "Moneda en la que viene el cobro. Si se omite, se asume la moneda "
            "de la tarjeta. Si difiere, se convierte con la tasa vigente y se "
            "descuenta el monto convertido."
        ),
    )
    note: str | None = Field(
        default=None,
        description=(
            "Identifica desde dónde se hizo el cobro (ej. \"App POS Tienda X\"). "
            "Pensado para que cada app externa que llame a este endpoint mande "
            "su propio nombre, así el gerente puede ver el origen de cada cargo."
        ),
    )


class RechargeCreate(BaseModel):
    card_id: str
    amount: float
    currency: Currency | None = Field(
        default=None,
        description="Moneda de la recarga. Si difiere de la tarjeta, se convierte.",
    )


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: str
    type: TransactionType
    amount: float
    currency: Currency
    charge_amount: float
    charge_currency: Currency
    rate_used: float | None = None
    status: TransactionStatus
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class ExchangeRateCreate(BaseModel):
    base_currency: Currency = Field(description="1 unidad de esta moneda vale `rate` de `target_currency`.")
    target_currency: Currency
    rate: float = Field(gt=0, description="Debe ser mayor que cero.")


class ExchangeRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    base_currency: Currency
    target_currency: Currency
    rate: float
    created_by: int | None = None
    created_at: datetime


class ConvertOut(BaseModel):
    amount: float
    base_currency: Currency
    target_currency: Currency
    converted_amount: float
    rate_used: float
    inverted: bool = Field(
        description="True si se resolvió invirtiendo el par cargado por el gerente."
    )


class ClientOverviewOut(BaseModel):
    """Vista 360 de un cliente para el gerente: sus datos, sus tarjetas y
    todas sus transacciones."""

    client: ClientOut
    cards: list[CardOut]
    transactions: list[TransactionOut]


class BankOverviewOut(BaseModel):
    """Resumen global del banco para el dashboard del gerente."""

    total_clients: int
    total_managers: int
    total_cards: int
    cards_by_status: dict[str, int]
    cards_by_currency: dict[str, int] = {}
    total_balance_in_active_cards: float
    balances_by_currency: dict[str, float] = {}
    total_transactions: int
    transactions_by_type: dict[str, int]
    total_purchased_amount: float
    total_recharged_amount: float
    purchased_by_currency: dict[str, float] = {}
    recharged_by_currency: dict[str, float] = {}


class PaymentOrderCreate(BaseModel):
    reference: str = Field(description="Referencia única del comercio (ej. código de reserva).")
    total_eur: float = Field(gt=0, description="Precio base de la orden, siempre en EUR.")
    note: str | None = Field(default=None, description="Origen del cobro (ej. naveSpace Tickets).")


class BankinTranchePay(BaseModel):
    card_id: str
    amount: float = Field(gt=0)
    currency: Currency | None = Field(
        default=None, description="Moneda del tramo. Si se omite, EUR. Se convierte a EUR."
    )
    note: str | None = None
    idempotency_key: str | None = Field(
        default=None, description="Reintentos con la misma key devuelven el tramo sin recobrar."
    )


class AdyenIntentCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: Currency | None = Field(default=None, description="Moneda del intento. Si se omite, EUR.")
    adyen_reference: str | None = Field(default=None, description="Referencia del pago en Adyen.")
    note: str | None = None
    idempotency_key: str | None = None


class PaymentTrancheOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    provider: PaymentProvider
    charge_amount: float
    charge_currency: Currency
    converted_eur: float
    rate_to_eur: float | None = None
    confirmed: bool
    card_id: str | None = None
    bankin_transaction_id: int | None = None
    adyen_reference: str | None = None
    note: str | None = None
    idempotency_key: str | None = None
    created_at: datetime


class PaymentOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    total_eur: float
    paid_eur: float
    remaining_eur: float
    status: PaymentOrderStatus
    note: str | None = None
    tranches: list[PaymentTrancheOut] = []
    created_at: datetime
    updated_at: datetime
