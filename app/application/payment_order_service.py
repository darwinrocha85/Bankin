"""Órdenes de pago multitramo con precio base siempre en EUR.

Regla de oro: la orden solo pasa a PAID cuando paid_eur cubre total_eur.
Cada tramo se convierte a EUR con la tasa vigente y queda congelado
(rate_to_eur), igual que `rate_used` en las transacciones.

Dos proveedores:
- BANKIN (banco propio): cobra de verdad vía TransactionService.purchase.
- ADYEN (en proceso): el tramo se registra como intención sin confirmar
  (no suma a paid_eur) hasta que el webhook lo confirme.
"""
from __future__ import annotations

from datetime import datetime

from app.application.exchange_rate_service import ExchangeRateService
from app.application.transaction_service import TransactionService
from app.domain.models import (
    Currency,
    PaymentOrder,
    PaymentOrderStatus,
    PaymentProvider,
    PaymentTranche,
)
from app.domain.ports import PaymentOrderRepository

_EPS = 0.005  # tolerancia de céntimos al comparar EUR


class PaymentOrderNotFoundError(Exception):
    pass


class PaymentOrderSettledError(Exception):
    """La orden ya está PAID o CANCELLED: no acepta más tramos."""


class DuplicateReferenceError(Exception):
    pass


class OverpaymentError(Exception):
    """El tramo en EUR supera el restante de la orden."""


class TrancheNotFoundError(Exception):
    pass


class TrancheAlreadyConfirmedError(Exception):
    pass


def _round2(value: float) -> float:
    return round(value + 1e-9, 2)


class PaymentOrderService:
    def __init__(
        self,
        orders: PaymentOrderRepository,
        transactions: TransactionService,
        rates: ExchangeRateService,
    ) -> None:
        self._orders = orders
        self._transactions = transactions
        self._rates = rates

    # ---- creación ----

    def create_order(self, reference: str, total_eur: float, note: str | None = None) -> PaymentOrder:
        if not reference or not reference.strip():
            raise ValueError("reference es requerido")
        if total_eur <= 0:
            raise ValueError("total_eur debe ser mayor que cero")
        if self._orders.find_order_by_reference(reference.strip()) is not None:
            raise DuplicateReferenceError(f"Ya existe la orden {reference.strip()}")
        return self._orders.save_order(
            PaymentOrder(reference=reference.strip(), total_eur=_round2(total_eur), note=note)
        )

    def get_order(self, order_id: int) -> PaymentOrder:
        order = self._orders.find_order_by_id(order_id)
        if order is None:
            raise PaymentOrderNotFoundError(f"No existe la orden {order_id}")
        return order

    def list_tranches(self, order_id: int) -> list[PaymentTranche]:
        self.get_order(order_id)
        return self._orders.find_tranches_by_order(order_id)

    @staticmethod
    def remaining_eur(order: PaymentOrder) -> float:
        return _round2(order.total_eur - order.paid_eur)

    # ---- tramo BankIn (cobro real) ----

    def pay_with_bankin(
        self,
        order_id: int,
        card_id: str,
        amount: float,
        currency: Currency | None = None,
        note: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[PaymentOrder, PaymentTranche]:
        order = self.get_order(order_id)
        if amount <= 0:
            raise ValueError("amount debe ser mayor que cero")
        if idempotency_key:
            existing = self._orders.find_tranche_by_idempotency(order_id, idempotency_key)
            if existing is not None:
                return order, existing
        if order.status in (PaymentOrderStatus.PAID, PaymentOrderStatus.CANCELLED):
            raise PaymentOrderSettledError(f"La orden {order_id} ya está {order.status.value}")

        charge_currency = currency or Currency.EUR
        converted, resolved = self._rates.convert(amount, charge_currency, Currency.EUR)
        eur_value = _round2(converted)
        rate_to_eur = None if charge_currency == Currency.EUR else resolved.rate
        if eur_value - self.remaining_eur(order) > _EPS:
            raise OverpaymentError(
                f"El tramo vale {eur_value:.2f} EUR pero solo restan "
                f"{self.remaining_eur(order):.2f} EUR de la orden {order_id}"
            )

        # Cobro real: si falla (404/400), la orden queda intacta.
        tx = self._transactions.purchase(card_id, amount, note, currency)

        tranche = self._orders.save_tranche(
            PaymentTranche(
                order_id=order.id,
                provider=PaymentProvider.BANKIN,
                charge_amount=amount,
                charge_currency=charge_currency,
                converted_eur=eur_value,
                rate_to_eur=rate_to_eur,
                confirmed=True,
                card_id=card_id,
                bankin_transaction_id=tx.id,
                note=note,
                idempotency_key=idempotency_key,
            )
        )
        return self._apply_confirmed(order, eur_value), tranche

    # ---- tramo Adyen (en proceso: intención + confirmación) ----

    def register_adyen_intent(
        self,
        order_id: int,
        amount: float,
        currency: Currency | None = None,
        adyen_reference: str | None = None,
        note: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[PaymentOrder, PaymentTranche]:
        """Registra la intención sin sumar a paid_eur (aún sin webhook)."""
        order = self.get_order(order_id)
        if amount <= 0:
            raise ValueError("amount debe ser mayor que cero")
        if idempotency_key:
            existing = self._orders.find_tranche_by_idempotency(order_id, idempotency_key)
            if existing is not None:
                return order, existing
        if order.status in (PaymentOrderStatus.PAID, PaymentOrderStatus.CANCELLED):
            raise PaymentOrderSettledError(f"La orden {order_id} ya está {order.status.value}")

        charge_currency = currency or Currency.EUR
        converted, resolved = self._rates.convert(amount, charge_currency, Currency.EUR)
        eur_value = _round2(converted)
        if eur_value - self.remaining_eur(order) > _EPS:
            raise OverpaymentError(
                f"La intención Adyen vale {eur_value:.2f} EUR pero solo restan "
                f"{self.remaining_eur(order):.2f} EUR de la orden {order_id}"
            )
        tranche = self._orders.save_tranche(
            PaymentTranche(
                order_id=order.id,
                provider=PaymentProvider.ADYEN,
                charge_amount=amount,
                charge_currency=charge_currency,
                converted_eur=eur_value,
                rate_to_eur=None if charge_currency == Currency.EUR else resolved.rate,
                confirmed=False,
                adyen_reference=adyen_reference,
                note=note,
                idempotency_key=idempotency_key,
            )
        )
        return order, tranche

    def confirm_adyen_tranche(self, tranche_id: int) -> tuple[PaymentOrder, PaymentTranche]:
        """Webhook (stub): confirma la intención Adyen y suma a paid_eur."""
        tranche = self._orders.find_tranche_by_id(tranche_id)
        if tranche is None or tranche.provider != PaymentProvider.ADYEN:
            raise TrancheNotFoundError(f"No existe tramo Adyen {tranche_id}")
        if tranche.confirmed:
            raise TrancheAlreadyConfirmedError(f"El tramo {tranche_id} ya estaba confirmado")
        order = self.get_order(tranche.order_id)
        if order.status == PaymentOrderStatus.CANCELLED:
            raise PaymentOrderSettledError(f"La orden {order.id} está CANCELLED")
        repo = self._orders
        if hasattr(repo, "mark_tranche_confirmed"):
            tranche = repo.mark_tranche_confirmed(tranche_id)  # type: ignore[union-attr]
        else:
            tranche.confirmed = True
        return self._apply_confirmed(order, tranche.converted_eur), tranche

    # ---- cancelación ----

    def cancel_order(self, order_id: int) -> PaymentOrder:
        order = self.get_order(order_id)
        if order.status == PaymentOrderStatus.CANCELLED:
            return order
        # Cancelar una orden PAID es una devolución total: se anulan todos los
        # tramos BankIn (best-effort) y la orden queda en CANCELLED con paid 0.
        # Es el caso de naveSpace al cancelar una entrada ya cobrada.
        for tranche in self._orders.find_tranches_by_order(order_id):
            if tranche.provider == PaymentProvider.BANKIN and tranche.bankin_transaction_id:
                try:
                    self._transactions.annul(tranche.bankin_transaction_id)
                except Exception:
                    continue  # best-effort: la orden se cancela igual
        order.paid_eur = 0
        order.status = PaymentOrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        return self._orders.save_order(order)

    # ---- interno ----

    def _apply_confirmed(self, order: PaymentOrder, eur_value: float) -> PaymentOrder:
        order.paid_eur = _round2(order.paid_eur + eur_value)
        remaining = self.remaining_eur(order)
        order.status = PaymentOrderStatus.PAID if remaining <= _EPS else PaymentOrderStatus.PARTIAL
        order.updated_at = datetime.utcnow()
        return self._orders.save_order(order)
