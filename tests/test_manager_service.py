"""Gerente: autorización por rol y overview con desglose por moneda."""
import pytest

from app.application.manager_service import (
    ManagerNotFoundError,
    NotAManagerError,
)
from app.domain.models import Currency, Role


def test_require_manager_ok(services, manager):
    services["manager"].require_manager(manager.id)


def test_require_manager_missing_and_not_manager(services, client):
    with pytest.raises(ManagerNotFoundError):
        services["manager"].require_manager(999999)
    with pytest.raises(NotAManagerError):
        services["manager"].require_manager(client.id)


def test_overview_counts_and_currency_breakdown(services, manager, client, eur_card):
    services["clients"].create_client("Otro", "otro1", 5, role=Role.MANAGER)
    overview = services["manager"].get_bank_overview(manager.id)
    assert overview["total_managers"] == 2
    assert overview["total_clients"] == 1
    assert overview["total_cards"] == 1
    # eur_card: recarga 500 EUR en el seed del fixture
    assert overview["balances_by_currency"] == {"EUR": 500}
    assert overview["cards_by_currency"] == {"EUR": 1}
    assert overview["recharged_by_currency"] == {"EUR": 500}
    assert overview["purchased_by_currency"] == {}


def test_overview_requires_manager(services, client):
    with pytest.raises(NotAManagerError):
        services["manager"].get_bank_overview(client.id)


def test_purchase_in_other_currency_counts_in_card_currency(
    services, manager, client, seeded_rates
):
    cop = services["cards"].issue_card(client.id, Currency.COP)
    services["cards"].activate_card(cop.card_id)
    services["transactions"].recharge(cop.card_id, 1_000_000, Currency.COP)
    services["transactions"].purchase(cop.card_id, 10, currency=Currency.USD)
    overview = services["manager"].get_bank_overview(manager.id)
    assert overview["purchased_by_currency"] == {"COP": pytest.approx(41000.0)}
