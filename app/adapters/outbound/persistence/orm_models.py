"""Modelos ORM (tablas SQLAlchemy). Viven separados del dominio a propósito:
el dominio (app/domain/models.py) no debe saber nada de columnas ni tablas.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.outbound.persistence.db import Base


class ClientORM(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="CLIENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CardORM(Base):
    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("client_id", "currency", name="uq_cards_client_currency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    card_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    cardholder_name: Mapped[str] = mapped_column(String, nullable=False)
    date_expires: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="COP")
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class TransactionORM(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.card_id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="COP")
    charge_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    charge_currency: Mapped[str] = mapped_column(String, nullable=False, default="COP")
    rate_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="COMPLETED")
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ExchangeRateORM(Base):
    """Tabla append-only de tasas: cada carga del gerente es una fila nueva."""

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String, nullable=False)
    target_currency: Mapped[str] = mapped_column(String, nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentOrderORM(Base):
    """Ledger multitramo: precio base siempre en EUR."""

    __tablename__ = "payment_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    total_eur: Mapped[float] = mapped_column(Float, nullable=False)
    paid_eur: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PaymentTrancheORM(Base):
    """Cada pago parcial: BankIn confirmado al cobrar, Adyen al webhook."""

    __tablename__ = "payment_tranches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("payment_orders.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    charge_amount: Mapped[float] = mapped_column(Float, nullable=False)
    charge_currency: Mapped[str] = mapped_column(String, nullable=False)
    converted_eur: Mapped[float] = mapped_column(Float, nullable=False)
    rate_to_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)
    card_id: Mapped[str | None] = mapped_column(String, nullable=True)
    bankin_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adyen_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
