"""Esquemas Pydantic: son los DTOs que entran/salen por HTTP.
Se mantienen separados del modelo de dominio para que la API pueda cambiar
de forma sin afectar al dominio, y viceversa.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.models import CardStatus, Role, TransactionStatus, TransactionType


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


class BalanceUpdate(BaseModel):
    balance: int


class BalanceOut(BaseModel):
    balance: int


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    card_id: str
    cardholder_name: str
    date_expires: str
    balance: int
    status: CardStatus
    created_at: datetime
    updated_at: datetime


class PurchaseCreate(BaseModel):
    card_id: str
    amount: float


class RechargeCreate(BaseModel):
    card_id: str
    amount: float


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: str
    type: TransactionType
    amount: float
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime


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
    total_balance_in_active_cards: float
    total_transactions: int
    transactions_by_type: dict[str, int]
    total_purchased_amount: float
    total_recharged_amount: float
