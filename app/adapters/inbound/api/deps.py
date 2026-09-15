"""Wiring de dependencias: aquí es donde se conectan los adaptadores
concretos (SQLite) con los casos de uso (ClientService), y FastAPI los
inyecta en cada request. Es el único punto "consciente" de qué adaptador
concreto estamos usando.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.card_repository_sqlite import (
    SqliteCardRepository,
)
from app.adapters.outbound.persistence.client_repository_sqlite import (
    SqliteClientRepository,
)
from app.adapters.outbound.persistence.db import get_session
from app.adapters.outbound.persistence.transaction_repository_sqlite import (
    SqliteTransactionRepository,
)
from app.application.card_service import CardService
from app.application.client_service import ClientService
from app.application.manager_service import ManagerService
from app.application.transaction_service import TransactionService


def get_client_service(session: Session = Depends(get_session)) -> ClientService:
    repository = SqliteClientRepository(session)
    return ClientService(repository)


def get_card_service(session: Session = Depends(get_session)) -> CardService:
    card_repository = SqliteCardRepository(session)
    client_repository = SqliteClientRepository(session)
    return CardService(card_repository, client_repository)


def get_transaction_service(session: Session = Depends(get_session)) -> TransactionService:
    transaction_repository = SqliteTransactionRepository(session)
    card_repository = SqliteCardRepository(session)
    return TransactionService(transaction_repository, card_repository)


def get_manager_service(session: Session = Depends(get_session)) -> ManagerService:
    client_repository = SqliteClientRepository(session)
    card_repository = SqliteCardRepository(session)
    transaction_repository = SqliteTransactionRepository(session)
    return ManagerService(client_repository, card_repository, transaction_repository)
