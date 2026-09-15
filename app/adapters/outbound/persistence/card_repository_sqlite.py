"""Adaptador de salida: implementa el puerto CardRepository usando SQLite."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.orm_models import CardORM
from app.domain.models import Card, CardStatus
from app.domain.ports import CardRepository


def _to_domain(row: CardORM) -> Card:
    return Card(
        id=row.id,
        client_id=row.client_id,
        card_id=row.card_id,
        cardholder_name=row.cardholder_name,
        date_expires=row.date_expires,
        balance=row.balance,
        status=CardStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqliteCardRepository(CardRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, card: Card) -> Card:
        if card.id is None:
            row = CardORM(
                client_id=card.client_id,
                card_id=card.card_id,
                cardholder_name=card.cardholder_name,
                date_expires=card.date_expires,
                balance=card.balance,
                status=card.status.value,
                created_at=card.created_at,
                updated_at=card.updated_at,
            )
            self._session.add(row)
        else:
            row = self._session.get(CardORM, card.id)
            row.client_id = card.client_id
            row.cardholder_name = card.cardholder_name
            row.date_expires = card.date_expires
            row.balance = card.balance
            row.status = card.status.value
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def find_all(self) -> list[Card]:
        rows = self._session.execute(select(CardORM)).scalars().all()
        return [_to_domain(row) for row in rows]

    def find_by_id(self, card_pk: int) -> Card | None:
        row = self._session.get(CardORM, card_pk)
        return _to_domain(row) if row else None

    def find_by_card_id(self, card_id: str) -> Card | None:
        row = self._session.execute(
            select(CardORM).where(CardORM.card_id == card_id)
        ).scalar_one_or_none()
        return _to_domain(row) if row else None

    def find_by_client_id(self, client_id: int) -> list[Card]:
        rows = (
            self._session.execute(select(CardORM).where(CardORM.client_id == client_id))
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]
