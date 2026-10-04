"""Fixtures compartidas: cada test crea su propio SQLite temporal y los
servicios cableados (casos de uso + repositorios SQLite reales), con un
gerente, un cliente y tasas de cambio de base.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.persistence import orm_models  # noqa: F401 (registra tablas)
from app.adapters.outbound.persistence.card_repository_sqlite import SqliteCardRepository
from app.adapters.outbound.persistence.client_repository_sqlite import SqliteClientRepository
from app.adapters.outbound.persistence.db import Base
from app.adapters.outbound.persistence.exchange_rate_repository_sqlite import (
    SqliteExchangeRateRepository,
)
from app.adapters.outbound.persistence.payment_order_repository_sqlite import (
    SqlitePaymentOrderRepository,
)
from app.adapters.outbound.persistence.transaction_repository_sqlite import (
    SqliteTransactionRepository,
)
from app.application.card_service import CardService
from app.application.client_service import ClientService
from app.application.exchange_rate_service import ExchangeRateService
from app.application.manager_service import ManagerService
from app.application.payment_order_service import PaymentOrderService
from app.application.transaction_service import TransactionService
from app.domain.models import Currency, Role


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def services(session):
    clients = ClientService(SqliteClientRepository(session))
    cards = CardService(SqliteCardRepository(session), SqliteClientRepository(session))
    rates = ExchangeRateService(SqliteExchangeRateRepository(session))
    transactions = TransactionService(
        SqliteTransactionRepository(session), SqliteCardRepository(session), rates
    )
    orders = PaymentOrderService(
        SqlitePaymentOrderRepository(session), transactions, rates
    )
    manager = ManagerService(
        SqliteClientRepository(session),
        SqliteCardRepository(session),
        SqliteTransactionRepository(session),
    )
    return {
        "clients": clients,
        "cards": cards,
        "rates": rates,
        "transactions": transactions,
        "orders": orders,
        "manager": manager,
    }


@pytest.fixture()
def manager(services):
    return services["clients"].create_client(
        "Jefe Test", "jefe1", 900001, role=Role.MANAGER
    )


@pytest.fixture()
def client(services):
    return services["clients"].create_client("Ana Test", "ana1", 112791)


@pytest.fixture()
def eur_card(services, client):
    """Tarjeta EUR activa con 500 de saldo exactos."""
    card = services["cards"].issue_card(client.id, Currency.EUR)
    services["cards"].activate_card(card.card_id)
    services["transactions"].recharge(card.card_id, 500, Currency.EUR)
    services["cards"].update_balance(card.card_id, 500)
    return services["cards"].get_card(card.card_id)


@pytest.fixture()
def seeded_rates(services, manager):
    services["rates"].create_rate(Currency.USD, Currency.COP, 4100.0, created_by=manager.id)
    services["rates"].create_rate(Currency.EUR, Currency.COP, 4450.0, created_by=manager.id)
    services["rates"].create_rate(Currency.EUR, Currency.USD, 1.09, created_by=manager.id)
