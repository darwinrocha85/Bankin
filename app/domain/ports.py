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

from app.domain.models import Card, Client, Transaction


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
