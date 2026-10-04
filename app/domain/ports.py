"""Puertos (interfaces) que la capa de aplicación necesita para funcionar.

Un "puerto" es un contrato abstracto. La capa de aplicación (casos de uso)
depende de estos puertos, no de una base de datos concreta. Luego, en
adapters/outbound, hay una implementación real (SQLite) que "encaja" en
este puerto -- de ahí el nombre "arquitectura hexagonal" (ports & adapters).

Cambiar de SQLite a Postgres en el futuro solo significa escribir un nuevo
adaptador que implemente estos mismos puertos; el dominio y los casos de
uso no se tocan.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import (
    Card,
    Client,
    Currency,
    ExchangeRate,
    PaymentOrder,
    PaymentTranche,
    Transaction,
)


class ClientRepository(ABC):
    """Puerto de salida para persistir y consultar Clientes."""

    @abstractmethod
    def save(self, client: Client) -> Client:
        """Crea o actualiza un cliente y devuelve la versión guardada (con id)."""

    @abstractmethod
    def find_all(self) -> list[Client]:
        ...

    @abstractmethod
    def find_by_id(self, client_id: int) -> Client | None:
        ...

    @abstractmethod
    def find_by_name(self, name: str) -> list[Client]:
        ...

    @abstractmethod
    def find_by_product_id(self, product_id: int) -> list[Client]:
        ...

    @abstractmethod
    def delete_by_id(self, client_id: int) -> None:
        ...


class CardRepository(ABC):
    """Puerto de salida para persistir y consultar Tarjetas."""

    @abstractmethod
    def save(self, card: Card) -> Card:
        """Crea o actualiza una tarjeta y devuelve la versión guardada (con id)."""

    @abstractmethod
    def find_all(self) -> list[Card]:
        ...

    @abstractmethod
    def find_by_id(self, card_pk: int) -> Card | None:
        ...

    @abstractmethod
    def find_by_card_id(self, card_id: str) -> Card | None:
        ...

    @abstractmethod
    def find_by_client_id(self, client_id: int) -> list[Card]:
        ...

    @abstractmethod
    def find_by_client_and_currency(self, client_id: int, currency: Currency) -> Card | None:
        """Una tarjeta de un cliente en una moneda dada (máx. una por moneda)."""


class ExchangeRateRepository(ABC):
    """Puerto de salida para las tasas de cambio.

    Las tasas son append-only: `save` siempre crea una fila nueva (el
    histórico se conserva); la vigente de cada par es la más reciente.
    """

    @abstractmethod
    def save(self, rate: ExchangeRate) -> ExchangeRate:
        ...

    @abstractmethod
    def find_latest(self, base: Currency, target: Currency) -> ExchangeRate | None:
        """Tasa vigente del par base->target, o None si nunca se cargó."""

    @abstractmethod
    def find_history(
        self,
        base: Currency | None = None,
        target: Currency | None = None,
        limit: int = 100,
    ) -> list[ExchangeRate]:
        """Histórico (más recientes primero), opcionalmente filtrado por par."""

    @abstractmethod
    def find_all_latest(self) -> list[ExchangeRate]:
        """Una fila por par (base, target): la más reciente de cada uno."""


class TransactionRepository(ABC):
    """Puerto de salida para persistir y consultar Transacciones."""

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        """Crea o actualiza una transacción y devuelve la versión guardada (con id)."""

    @abstractmethod
    def find_all(self) -> list[Transaction]:
        ...

    @abstractmethod
    def find_by_id(self, transaction_id: int) -> Transaction | None:
        ...

    @abstractmethod
    def find_by_card_id(self, card_id: str) -> list[Transaction]:
        ...


class PaymentOrderRepository(ABC):
    """Puerto de salida para órdenes de pago multitramo (ledger en EUR)."""

    @abstractmethod
    def save_order(self, order: PaymentOrder) -> PaymentOrder:
        ...

    @abstractmethod
    def find_order_by_id(self, order_id: int) -> PaymentOrder | None:
        ...

    @abstractmethod
    def find_order_by_reference(self, reference: str) -> PaymentOrder | None:
        ...

    @abstractmethod
    def save_tranche(self, tranche: PaymentTranche) -> PaymentTranche:
        ...

    @abstractmethod
    def find_tranches_by_order(self, order_id: int) -> list[PaymentTranche]:
        ...

    @abstractmethod
    def find_tranche_by_id(self, tranche_id: int) -> PaymentTranche | None:
        ...

    @abstractmethod
    def find_tranche_by_idempotency(self, order_id: int, key: str) -> PaymentTranche | None:
        """Replay idempotente: misma key dentro de la orden devuelve el tramo."""

