"""Transacciones: compra/recarga en misma y distinta moneda, anulación exacta."""
import pytest

from app.application.exchange_rate_service import ExchangeRateNotFoundError
from app.application.transaction_service import (
    CardNotActiveError,
    InsufficientFundsError,
    InvalidAmountError,
    TransactionAlreadyAnnulledError,
    TransactionNotFoundError,
)
from app.domain.models import (
    Currency,
    TransactionStatus,
    TransactionType,
)


def test_purchase_same_currency(services, eur_card):
    tx = services["transactions"].purchase(eur_card.card_id, 100, note="test")
    assert tx.type == TransactionType.PURCHASE
    assert tx.amount == 100
    assert tx.currency == Currency.EUR
    assert tx.charge_amount == 100
    assert tx.charge_currency == Currency.EUR
    assert tx.rate_used is None
    assert services["cards"].get_balance(eur_card.card_id) == 400


def test_purchase_converts_with_current_rate(services, seeded_rates, client):
    cop = services["cards"].issue_card(client.id, Currency.COP)
    services["cards"].activate_card(cop.card_id)
    services["transactions"].recharge(cop.card_id, 1_000_000, Currency.COP)
    services["cards"].update_balance(cop.card_id, 1_000_000)
    tx = services["transactions"].purchase(cop.card_id, 10, note="ext", currency=Currency.USD)
    # tasa vigente USD->COP 4100
    assert tx.amount == pytest.approx(41000.0)
    assert tx.currency == Currency.COP
    assert tx.rate_used == pytest.approx(4100.0)
    assert services["cards"].get_balance(cop.card_id) == pytest.approx(1_000_000 - 41000.0)


def test_purchase_without_rate_fails(services, eur_card):
    with pytest.raises(ExchangeRateNotFoundError):
        services["transactions"].purchase(eur_card.card_id, 10, currency=Currency.USD)


def test_purchase_validations(services, eur_card, client):
    with pytest.raises(InvalidAmountError):
        services["transactions"].purchase(eur_card.card_id, 0)
    with pytest.raises(InsufficientFundsError):
        services["transactions"].purchase(eur_card.card_id, 10_000)
    created = services["cards"].issue_card(client.id, Currency.COP)
    with pytest.raises(CardNotActiveError):
        services["transactions"].purchase(created.card_id, 10)


def test_recharge_and_cancelled_card_rejected(services, eur_card, client):
    tx = services["transactions"].recharge(eur_card.card_id, 50, Currency.EUR)
    assert tx.type == TransactionType.RECHARGE
    assert services["cards"].get_balance(eur_card.card_id) == 550
    cancelled = services["cards"].issue_card(client.id, Currency.COP)
    services["cards"].activate_card(cancelled.card_id)
    services["cards"].cancel_card(cancelled.card_id)
    with pytest.raises(CardNotActiveError):
        services["transactions"].recharge(cancelled.card_id, 10)


def test_annul_purchase_refunds(services, eur_card):
    tx = services["transactions"].purchase(eur_card.card_id, 120)
    annulled = services["transactions"].annul(tx.id)
    assert annulled.status == TransactionStatus.ANNULLED
    assert services["cards"].get_balance(eur_card.card_id) == 500


def test_annul_uses_frozen_rate_not_current(services, seeded_rates, client, manager):
    cop = services["cards"].issue_card(client.id, Currency.COP)
    services["cards"].activate_card(cop.card_id)
    services["transactions"].recharge(cop.card_id, 1_000_000, Currency.COP)
    services["cards"].update_balance(cop.card_id, 1_000_000)
    before = services["cards"].get_balance(cop.card_id)
    tx = services["transactions"].purchase(cop.card_id, 10, currency=Currency.USD)
    assert tx.amount == pytest.approx(41000.0)
    # la tasa cambia después: la devolución debe usar la congelada
    services["rates"].create_rate(Currency.USD, Currency.COP, 5000.0, created_by=manager.id)
    services["transactions"].annul(tx.id)
    assert services["cards"].get_balance(cop.card_id) == pytest.approx(before)


def test_annul_recharge_spent_fails(services, eur_card):
    rec = services["transactions"].recharge(eur_card.card_id, 100, Currency.EUR)
    services["transactions"].purchase(eur_card.card_id, 550)
    with pytest.raises(InsufficientFundsError):
        services["transactions"].annul(rec.id)


def test_annul_twice_and_missing(services, eur_card):
    tx = services["transactions"].purchase(eur_card.card_id, 10)
    services["transactions"].annul(tx.id)
    with pytest.raises(TransactionAlreadyAnnulledError):
        services["transactions"].annul(tx.id)
    with pytest.raises(TransactionNotFoundError):
        services["transactions"].annul(999999)
