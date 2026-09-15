"""Adaptador de salida: implementa el puerto TransactionRepository usando SQLite."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.orm_models import TransactionORM
from app.domain.models import Transaction, TransactionStatus, TransactionType
from app.domain.ports import TransactionRepository


def _to_domain(row: TransactionORM) -> Transaction:
    return Transaction(
        id=row.id,
        card_id=row.card_id,
        type=TransactionType(row.type),
        amount=row.amount,
        status=TransactionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, transaction: Transaction) -> Transaction:
        if transaction.id is None:
            row = TransactionORM(
                card_id=transaction.card_id,
                type=transaction.type.value,
                amount=transaction.amount,
                status=transaction.status.value,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )
            self._session.add(row)
        else:
            row = self._session.get(TransactionORM, transaction.id)
            row.status = transaction.status.value
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def find_all(self) -> list[Transaction]:
        rows = self._session.execute(select(TransactionORM)).scalars().all()
        return [_to_domain(row) for row in rows]

    def find_by_id(self, transaction_id: int) -> Transaction | None:
        row = self._session.get(TransactionORM, transaction_id)
        return _to_domain(row) if row else None

    def find_by_card_id(self, card_id: str) -> list[Transaction]:
        rows = (
            self._session.execute(select(TransactionORM).where(TransactionORM.card_id == card_id))
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]
