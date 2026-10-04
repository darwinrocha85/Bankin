"""Modelos de dominio (capa de negocio, sin dependencias de frameworks).

Esta capa no sabe nada de FastAPI, SQLAlchemy ni SQLite: son objetos Python
puros. Eso es lo que permite que la arquitectura sea "hexagonal": el dominio
queda en el centro y los adaptadores (API, base de datos) dependen de él,
nunca al revés.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    """Rol de una persona dentro del banco.

    CLIENT: un cliente normal, solo ve su propia información.
    MANAGER: un gerente, puede ver la información de todos los clientes.
    """

    CLIENT = "CLIENT"
    MANAGER = "MANAGER"


@dataclass
class Client:
    """Un cliente (o gerente) del banco. Equivale a la entidad Person de Java."""

    name: str
    username: str
    product_id: int
    role: Role = Role.CLIENT
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class CardStatus(str, Enum):
    """Estado de una tarjeta. Equivale a los enteros 0/1/2 de la versión Java
    (CREATED=0, ACTIVE=1, CANCELLED=2), pero con nombres legibles.
    """

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class Currency(str, Enum):
    """Monedas soportadas por BankIn.

    Cada tarjeta opera en UNA sola moneda y los saldos son independientes
    entre sí: un cliente puede tener hasta una tarjeta por moneda.
    """

    COP = "COP"
    USD = "USD"
    EUR = "EUR"


@dataclass
class Card:
    """Una tarjeta de crédito. Equivale a la entidad CardCredit de Java.

    A diferencia de la versión Java (que solo guardaba el nombre del titular
    suelto), aquí la tarjeta queda enlazada de verdad a un Cliente mediante
    client_id -- necesario para que el gerente pueda ver toda la info
    relacionada de cada cliente.
    """

    client_id: int
    card_id: str
    cardholder_name: str
    date_expires: str
    currency: Currency = Currency.COP
    """Moneda de la tarjeta. El balance siempre está expresado en esta
    moneda y es independiente del balance de las otras tarjetas del
    mismo cliente."""
    balance: float = 0
    status: CardStatus = CardStatus.CREATED
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class TransactionType(str, Enum):
    """Tipo de movimiento sobre una tarjeta.

    PURCHASE: una compra, resta saldo.
    RECHARGE: una recarga de saldo (lo que pediste), suma saldo.

    En la versión Java, "purchase" existía pero nunca tocaba el balance de
    la tarjeta (estaba deliberadamente incompleto), y no existía recarga en
    absoluto. Aquí ambas mueven el saldo de verdad.
    """

    PURCHASE = "PURCHASE"
    RECHARGE = "RECHARGE"


class TransactionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    ANNULLED = "ANNULLED"


class PaymentOrderStatus(str, Enum):
    """Estado de una orden de pago multitramo (precio base siempre en EUR).

    PENDING: creada, sin ningún tramo cobrado.
    PARTIAL: al menos un tramo confirmado, aún falta saldo (remaining > 0).
    PAID: paid_eur cubre total_eur. Solo aquí el comercio confirma la entrega.
    CANCELLED: cancelada; los tramos BankIn se reversan, los de Adyen se descartan.
    """

    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentProvider(str, Enum):
    """Origen de cada tramo.

    BANKIN: banco propio, cobro real vía TransactionService.purchase.
    ADYEN: pasarela externa, aún en proceso de integración: el tramo se
        registra como intención (no suma a paid_eur) hasta que el webhook
        lo confirme (confirm_adyen_tranche).
    """

    BANKIN = "BANKIN"
    ADYEN = "ADYEN"


@dataclass
class Transaction:
    """Un movimiento (compra o recarga) sobre una tarjeta.
    Equivale a la entidad Transaction de Java, mejorada: ahora sí afecta
    el balance de la tarjeta, y una anulación lo revierte correctamente.
    """

    card_id: str
    type: TransactionType
    amount: float
    """Monto en la moneda de la tarjeta: es lo que realmente se descuenta
    (PURCHASE) o se suma (RECHARGE) al balance, y lo que una anulación/
    reversa revierte. Si el cobro vino en otra moneda, este monto ya trae
    la conversión aplicada."""
    currency: Currency = Currency.COP
    """Moneda de la tarjeta al momento de la transacción (denominación
    de `amount`)."""
    charge_amount: float = 0
    """Monto original pedido por quien cobra, en `charge_currency`."""
    charge_currency: Currency = Currency.COP
    """Moneda en la que se pidió el cobro. Si es igual a `currency`,
    no hubo conversión."""
    rate_used: float | None = None
    """Tasa aplicada (unidades de moneda-tarjeta por 1 unidad de
    moneda-cobro). None/1.0 cuando no hubo conversión: la tasa queda
    congelada aquí para que una devolución posterior revierta el monto
    exacto aunque la tasa vigente haya cambiado."""
    status: TransactionStatus = TransactionStatus.COMPLETED
    note: str | None = None
    """Quién hizo la compra: identifica la app de origen (ej. "App POS
    Tienda X"). Pensado sobre todo para POST /transactions/purchase, el
    endpoint de cobro llamado desde otras apps -- así el gerente puede ver
    de dónde vino cada cargo."""
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExchangeRate:
    """Una tasa de cambio cargada por el gerente: cuántas unidades de
    `target_currency` vale 1 unidad de `base_currency`.

    Las tasas son inmutables y se guardan como histórico: cada carga crea
    una fila nueva, nunca se edita una existente. La tasa "vigente" para
    un par es la fila más reciente.
    """

    base_currency: Currency
    target_currency: Currency
    rate: float
    created_by: int | None = None
    """manager_id que cargó la tasa (auditoría, opcional)."""
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PaymentOrder:
    """Orden de cobro multitramo con precio base en EUR.

    El ticket/reserva del comercio solo se confirma cuando status == PAID.
    paid_eur es la suma de los tramos confirmados (BankIn al cobrar, Adyen
    al confirmarse el webhook), cada uno convertido a EUR con tasa congelada.
    """

    reference: str
    total_eur: float
    paid_eur: float = 0
    status: PaymentOrderStatus = PaymentOrderStatus.PENDING
    note: str | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PaymentTranche:
    """Un pago parcial dentro de una orden.

    converted_eur: valor del tramo en EUR con la tasa congelada al cobrar.
    Solo suma a paid_eur si confirmed (BankIn nace confirmado; Adyen nace
    sin confirmar hasta el webhook). rate_to_eur: EUR por 1 unidad de
    charge_currency (None si ya era EUR).
    """

    order_id: int
    provider: PaymentProvider
    charge_amount: float
    charge_currency: Currency
    converted_eur: float
    rate_to_eur: float | None = None
    confirmed: bool = True
    card_id: str | None = None
    bankin_transaction_id: int | None = None
    adyen_reference: str | None = None
    note: str | None = None
    idempotency_key: str | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
