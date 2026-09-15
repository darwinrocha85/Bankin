"""Casos de uso relacionados con Transacciones: compra, recarga y anulación.

A diferencia de la versión Java (deliberadamente incompleta: "purchase" no
tocaba el balance), aquí una compra descuenta saldo de verdad, una recarga
lo aumenta, y anular una transacción revierte su efecto sobre el balance.
"""
from __future__ import annotations

from datetime import datetime

from app.domain.models import CardStatus, Transaction, TransactionStatus, TransactionType
from app.domain.ports import CardRepository, TransactionRepository


class TransactionNotFoundError(Exception):
    pass


class CardNotFoundForTransactionError(Exception):
    pass


class CardNotActiveError(Exception):
    """La tarjeta existe pero no está ACTIVE (aún no fue activada, o fue cancelada)."""


class InvalidAmountError(Exception):
    """El monto debe ser mayor que cero."""


class InsufficientFundsError(Exception):
    """El balance de la tarjeta no alcanza para la compra."""


class TransactionAlreadyAnnulledError(Exception):
    pass


class TransactionService:
    def __init__(self, transaction_repository: TransactionRepository, card_repository: CardRepository) -> None:
        self._transactions = transaction_repository
        self._cards = card_repository

    def _get_card_or_raise(self, card_id: str):
        card = self._cards.find_by_card_id(card_id)
        if card is None:
            raise CardNotFoundForTransactionError(f"No existe la tarjeta {card_id}")
        return card

    def purchase(self, card_id: str, amount: float) -> Transaction:
        if amount <= 0:
            raise InvalidAmountError("El monto de la compra debe ser mayor que cero")

        card = self._get_card_or_raise(card_id)
        if card.status != CardStatus.ACTIVE:
            raise CardNotActiveError(f"La tarjeta {card_id} no está activa (status={card.status.value})")
        if card.balance < amount:
            raise InsufficientFundsError(
                f"Saldo insuficiente: balance={card.balance}, monto={amount}"
            )

        card.balance -= amount
        card.updated_at = datetime.utcnow()
        self._cards.save(card)

        transaction = Transaction(card_id=card_id, type=TransactionType.PURCHASE, amount=amount)
        return self._transactions.save(transaction)

    def recharge(self, card_id: str, amount: float) -> Transaction:
        """Recarga saldo a una tarjeta. Esto es lo que pediste: la tarjeta
        debe poder recargar saldo, y quedar registrado como una transacción
        más (con su fecha y su rastro de auditoría), no como un cambio
        directo de balance por detrás.
        """
        if amount <= 0:
            raise InvalidAmountError("El monto de la recarga debe ser mayor que cero")

        card = self._get_card_or_raise(card_id)
        if card.status == CardStatus.CANCELLED:
            raise CardNotActiveError(f"La tarjeta {card_id} está cancelada, no se puede recargar")

        card.balance += amount
        card.updated_at = datetime.utcnow()
        self._cards.save(card)

        transaction = Transaction(card_id=card_id, type=TransactionType.RECHARGE, amount=amount)
        return self._transactions.save(transaction)

    def annul(self, transaction_id: int) -> Transaction:
        """Anula una transacción existente y revierte su efecto en el balance:
        una compra anulada devuelve el dinero, una recarga anulada lo retira.
        """
        transaction = self._transactions.find_by_id(transaction_id)
        if transaction is None:
            raise TransactionNotFoundError(f"No existe la transacción {transaction_id}")
        if transaction.status == TransactionStatus.ANNULLED:
            raise TransactionAlreadyAnnulledError(f"La transacción {transaction_id} ya estaba anulada")

        card = self._get_card_or_raise(transaction.card_id)
        if transaction.type == TransactionType.PURCHASE:
            # Devolver el dinero de una compra siempre es seguro: nunca deja
            # el balance negativo.
            card.balance += transaction.amount
        else:  # RECHARGE
            # Retirar una recarga sí puede dejar el balance negativo si ese
            # dinero ya se gastó en compras posteriores. No lo permitimos:
            # hay que anular esas compras primero.
            if card.balance - transaction.amount < 0:
                raise InsufficientFundsError(
                    f"No se puede anular la recarga {transaction_id}: el saldo actual "
                    f"({card.balance}) ya no alcanza para retirar {transaction.amount} "
                    "-- probablemente ese dinero ya se gastó en otra compra"
                )
            card.balance -= transaction.amount
        card.updated_at = datetime.utcnow()
        self._cards.save(card)

        transaction.status = TransactionStatus.ANNULLED
        transaction.updated_at = datetime.utcnow()
        return self._transactions.save(transaction)

    def list_all(self) -> list[Transaction]:
        return self._transactions.find_all()

    def list_for_card(self, card_id: str) -> list[Transaction]:
        return self._transactions.find_by_card_id(card_id)

    def get(self, transaction_id: int) -> Transaction:
        transaction = self._transactions.find_by_id(transaction_id)
        if transaction is None:
            raise TransactionNotFoundError(f"No existe la transacción {transaction_id}")
        return transaction
