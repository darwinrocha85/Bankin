"""Tasas: validación, vigente, histórico append-only y fallback a inversa."""
import pytest

from app.application.exchange_rate_service import (
    ExchangeRateNotFoundError,
    InvalidRateError,
)
from app.domain.models import Currency


def test_create_rate_ok(services, manager):
    rate = services["rates"].create_rate(Currency.USD, Currency.COP, 4100.0, created_by=manager.id)
    assert rate.base_currency == Currency.USD
    assert rate.target_currency == Currency.COP
    assert rate.rate == 4100.0
    assert rate.created_by == manager.id


def test_create_rate_same_currency_rejected(services):
    with pytest.raises(InvalidRateError):
        services["rates"].create_rate(Currency.USD, Currency.USD, 1.0)


def test_create_rate_non_positive_rejected(services):
    with pytest.raises(InvalidRateError):
        services["rates"].create_rate(Currency.USD, Currency.COP, 0)


def test_latest_wins_and_history_is_kept(services, manager):
    services["rates"].create_rate(Currency.USD, Currency.COP, 4100.0, created_by=manager.id)
    services["rates"].create_rate(Currency.USD, Currency.COP, 4200.0, created_by=manager.id)
    assert services["rates"].get_rate(Currency.USD, Currency.COP).rate == 4200.0
    history = services["rates"].history(Currency.USD, Currency.COP)
    assert [r.rate for r in history] == [4200.0, 4100.0]


def test_missing_pair_raises(services):
    with pytest.raises(ExchangeRateNotFoundError):
        services["rates"].get_rate(Currency.USD, Currency.COP)


def test_inverse_pair_resolves(services, seeded_rates):
    resolved = services["rates"].get_rate(Currency.COP, Currency.USD)
    assert resolved.inverted is True
    assert resolved.rate == pytest.approx(1 / 4100.0)


def test_same_currency_is_one_without_row(services):
    resolved = services["rates"].get_rate(Currency.EUR, Currency.EUR)
    assert resolved.rate == 1.0


def test_convert_math(services, seeded_rates):
    converted, resolved = services["rates"].convert(10, Currency.USD, Currency.COP)
    assert converted == pytest.approx(41000.0)
    assert resolved.inverted is False


def test_current_table_has_one_row_per_pair(services, seeded_rates):
    table = {(r.base_currency, r.target_currency) for r in services["rates"].current_table()}
    assert table == {
        (Currency.USD, Currency.COP),
        (Currency.EUR, Currency.COP),
        (Currency.EUR, Currency.USD),
    }
