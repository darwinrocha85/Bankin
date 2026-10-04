"""Casos de uso relacionados con Transacciones: compra, recarga y anulación.

Multimoneda: cada tarjeta opera en su propia moneda. Si un cobro (o una
recarga) llega en una moneda distinta a la de la tarjeta, se convierte con
la tasa vigente (ExchangeRateService) y se descuenta/suma el monto ya
convertido. La tasa aplicada queda congelada en la transacción (`rate_used`),
así una anulación/reversa posterior devuelve exactamente lo que se movió,
aunque la tasa haya cambiado desde entonces.
"""
from __future__ import annotations

from datetime import datetime

from app.application.exchange_rate_service import ExchangeRateNotFoundError, ExchangeRateService
from app.domain.models import (
    CardStatus,
    Currency,
    Transaction,
    TransactionStatus,
    TransactionType,
)
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
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        card_repository: CardRepository,
        exchange_rate_service: ExchangeRateService | None = None,
    ) -> None:
        self._transactions = transaction_repository
        self._cards = card_repository
        self._rates = exchange_rate_service

    def _get_card_or_raise(self, card_id: str):
        card = self._cards.find_by_card_id(card_id)
        if card is None:
            raise CardNotFoundForTransactionError(f"No existe la tarjeta {card_id}")
        return card

    def _convert_to_card_currency(self, card, charge_amount: float, charge_currency: Currency | None):
        """Devuelve (monto_en_moneda_tarjeta, moneda_cobro, tasa_usada).

        Sin conversión (misma moneda o sin moneda indicada): tasa 1.0.
        """
        charge_currency = charge_currency or card.currency
        if charge_currency == card.currency:
            return charge_amount, charge_currency, None
        if self._rates is None:
            raise ExchangeRateNotFoundError(
                f"La tarjeta es {card.currency.value} pero el cobro vino en "
                f"{charge_currency.value} y no hay servicio de tasas configurado"
            )
        converted, resolved = self._rates.convert(charge_amount, charge_currency, card.currency)
        return converted, charge_currency, resolved.rate

    def purchase(
        self,
        card_id: str,
        amount: float,
        note: str | None = None,
        currency: Currency | None = None,
    ) -> Transaction:
        """Compra: descuenta saldo. `amount` viene expresado en `currency`
        (si se omite, se asume la moneda de la tarjeta). Con moneda distinta
        se aplica la tasa vigente y se descuenta el monto convertido."""
        if amount <= 0:
            raise InvalidAmountError("El monto de la compra debe ser mayor que cero")

        card = self._get_card_or_raise(card_id)
        if card.status != CardStatus.ACTIVE:
            raise CardNotActiveError(f"La tarjeta {card_id} no está activa (status={card.status.value})")

        debit, charge_currency, rate_used = self._convert_to_card_currency(card, amount, currency)
        if card.balance < debit:
            raise InsufficientFundsError(
                f"Saldo insuficiente: balance={card.balance} {card.currency.value}, "
                f"monto={debit:.2f} {card.currency.value}"
                + (f" (cobro original: {amount} {charge_currency.value})" if rate_used else "")
            )

        card.balance -= debit
        card.updated_at = datetime.utcnow()
        self._cards.save(card)

        transaction = Transaction(
            card_id=card_id,
            type=TransactionType.PURCHASE,
            amount=debit,
            currency=card.currency,
            charge_amount=amount,
            charge_currency=charge_currency,
            rate_used=rate_used,
            note=note,
        )
        return self._transactions.save(transaction)

    def recharge(
        self, card_id: str, amount: float, currency: Currency | None = None
    ) -> Transaction:
        """Recarga saldo a una tarjeta. Acepta moneda distinta con la misma
        regla de conversión que `purchase`; queda registrada como
        transacción auditable, no como cambio directo de balance.
        """
        if amount <= 0:
            raise InvalidAmountError("El monto de la recarga debe ser mayor que cero")

        card = self._get_card_or_raise(card_id)
        if card.status == CardStatus.CANCELLED:
            raise CardNotActiveError(f"La tarjeta {card_id} está cancelada, no se puede recargar")

        credit, charge_currency, rate_used = self._convert_to_card_currency(card, amount, currency)
        card.balance += credit
        card.updated_at = datetime.utcnow()
        self._cards.save(card)

        transaction = Transaction(
            card_id=card_id,
            type=TransactionType.RECHARGE,
            amount=credit,
            currency=card.currency,
            charge_amount=amount,
            charge_currency=charge_currency,
            rate_used=rate_used,
        )
        return self._transactions.save(transaction)

    def annul(self, transaction_id: int) -> Transaction:
        """Anula una transacción existente y revierte su efecto en el balance:
        una compra anulada devuelve el dinero, una recarga anulada lo retira.

        Multimoneda: se revierte `transaction.amount` (monto en moneda de la
        tarjeta, con la conversión ya aplicada y congelada en `rate_used`),
        así la devolución es exacta aunque la tasa vigente haya cambiado.
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
