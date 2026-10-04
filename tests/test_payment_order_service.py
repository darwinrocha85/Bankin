"""Órdenes multitramo: parcial/PAID, idempotencia, sobrepago y cancelación total."""
import pytest

from app.application.payment_order_service import (
    DuplicateReferenceError,
    OverpaymentError,
    PaymentOrderNotFoundError,
    PaymentOrderSettledError,
)
from app.domain.models import Currency


def _paid_order(services, eur_card, total=100.0, currency=Currency.EUR, ref="REF-1"):
    order = services["orders"].create_order(ref, total, note="test")
    order, _ = services["orders"].pay_with_bankin(
        order.id, eur_card.card_id, total, currency, note="test", idempotency_key=ref + "-k1"
    )
    return order


def test_create_order_validations(services):
    with pytest.raises(ValueError):
        services["orders"].create_order("", 10)
    with pytest.raises(ValueError):
        services["orders"].create_order("R", 0)
    services["orders"].create_order("DUP", 10)
    with pytest.raises(DuplicateReferenceError):
        services["orders"].create_order("DUP", 10)
    with pytest.raises(PaymentOrderNotFoundError):
        services["orders"].get_order(999999)


def test_pay_partial_then_paid(services, eur_card):
    order = services["orders"].create_order("P1", 100.0)
    order, t1 = services["orders"].pay_with_bankin(
        order.id, eur_card.card_id, 60, Currency.EUR, idempotency_key="P1-a"
    )
    assert order.status.value == "PARTIAL"
    assert order.paid_eur == 60
    order, t2 = services["orders"].pay_with_bankin(
        order.id, eur_card.card_id, 40, Currency.EUR, idempotency_key="P1-b"
    )
    assert order.status.value == "PAID"
    assert order.paid_eur == 100
    assert len(services["orders"].list_tranches(order.id)) == 2
    assert t1.bankin_transaction_id != t2.bankin_transaction_id


def test_idempotency_key_returns_same_tranche(services, eur_card):
    order = services["orders"].create_order("P2", 100.0)
    order, first = services["orders"].pay_with_bankin(
        order.id, eur_card.card_id, 60, Currency.EUR, idempotency_key="same"
    )
    order, second = services["orders"].pay_with_bankin(
        order.id, eur_card.card_id, 60, Currency.EUR, idempotency_key="same"
    )
    assert first.id == second.id
    assert len(services["orders"].list_tranches(order.id)) == 1
    assert services["cards"].get_balance(eur_card.card_id) == 500 - 60


def test_overpayment_rejected(services, eur_card):
    order = services["orders"].create_order("P3", 100.0)
    with pytest.raises(OverpaymentError):
        services["orders"].pay_with_bankin(order.id, eur_card.card_id, 101, Currency.EUR)


def test_pay_on_settled_order_rejected(services, eur_card):
    order = _paid_order(services, eur_card, ref="P4")
    with pytest.raises(PaymentOrderSettledError):
        services["orders"].pay_with_bankin(order.id, eur_card.card_id, 10, Currency.EUR)


def test_cancel_partial_reverses_tranches(services, eur_card):
    order = services["orders"].create_order("P5", 100.0)
    order, _ = services["orders"].pay_with_bankin(
        order.id, eur_card.card_id, 60, Currency.EUR, idempotency_key="P5-a"
    )
    order = services["orders"].cancel_order(order.id)
    assert order.status.value == "CANCELLED"
    assert order.paid_eur == 0
    assert services["cards"].get_balance(eur_card.card_id) == 500


def test_cancel_paid_order_refunds_everything(services, eur_card):
    # Caso naveSpace: cancelar una entrada ya cobrada devuelve todo.
    order = _paid_order(services, eur_card, ref="P6")
    assert order.status.value == "PAID"
    order = services["orders"].cancel_order(order.id)
    assert order.status.value == "CANCELLED"
    assert order.paid_eur == 0
    assert services["cards"].get_balance(eur_card.card_id) == 500


def test_cancel_is_idempotent(services, eur_card):
    order = _paid_order(services, eur_card, ref="P7")
    first = services["orders"].cancel_order(order.id)
    second = services["orders"].cancel_order(order.id)
    assert second.status.value == "CANCELLED"
    assert services["cards"].get_balance(eur_card.card_id) == 500
    assert first.id == second.id


def test_cancel_missing_order(services):
    with pytest.raises(PaymentOrderNotFoundError):
        services["orders"].cancel_order(999999)
