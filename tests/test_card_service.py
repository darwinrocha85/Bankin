"""Tarjetas: emisión multimoneda (1 por moneda), ciclo de estados y balance."""
import pytest

from app.application.card_service import (
    CardAlreadyExistsError,
    CardNotFoundError,
    ClientNotFoundForCardError,
)
from app.domain.models import CardStatus, Currency


def test_issue_card_defaults_to_cop(services, client):
    card = services["cards"].issue_card(client.id)
    assert card.currency == Currency.COP
    assert card.status == CardStatus.CREATED
    assert card.balance == 100
    assert card.cardholder_name == client.name


def test_issue_card_in_each_currency(services, client):
    for currency in (Currency.COP, Currency.USD, Currency.EUR):
        card = services["cards"].issue_card(client.id, currency)
        assert card.currency == currency
    assert len(services["cards"].list_cards_for_client(client.id)) == 3


def test_issue_duplicate_currency_fails_with_409_semantics(services, client):
    services["cards"].issue_card(client.id, Currency.EUR)
    with pytest.raises(CardAlreadyExistsError):
        services["cards"].issue_card(client.id, Currency.EUR)


def test_issue_card_for_missing_client(services):
    with pytest.raises(ClientNotFoundForCardError):
        services["cards"].issue_card(9999, Currency.COP)


def test_activate_cancel_lifecycle(services, client):
    card = services["cards"].issue_card(client.id, Currency.USD)
    assert services["cards"].activate_card(card.card_id).status == CardStatus.ACTIVE
    assert services["cards"].cancel_card(card.card_id).status == CardStatus.CANCELLED


def test_get_missing_card(services):
    with pytest.raises(CardNotFoundError):
        services["cards"].get_card("no-existe")


def test_update_and_get_balance(services, eur_card):
    services["cards"].update_balance(eur_card.card_id, 777.5)
    assert services["cards"].get_balance(eur_card.card_id) == 777.5
