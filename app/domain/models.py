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
    balance: int = 0
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


@dataclass
class Transaction:
    """Un movimiento (compra o recarga) sobre una tarjeta.
    Equivale a la entidad Transaction de Java, mejorada: ahora sí afecta
    el balance de la tarjeta, y una anulación lo revierte correctamente.
    """

    card_id: str
    type: TransactionType
    amount: float
    status: TransactionStatus = TransactionStatus.COMPLETED
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
