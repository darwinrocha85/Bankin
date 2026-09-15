"""Adaptador de salida: implementa el puerto ClientRepository usando SQLite
(a través de SQLAlchemy). Aquí es el único lugar del proyecto que sabe
traducir entre el modelo de dominio (Client) y la tabla (ClientORM).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.orm_models import ClientORM
from app.domain.models import Client, Role
from app.domain.ports import ClientRepository


def _to_domain(row: ClientORM) -> Client:
    return Client(
        id=row.id,
        name=row.name,
        username=row.username,
        product_id=row.product_id,
        role=Role(row.role),
        created_at=row.created_at,
    )


class SqliteClientRepository(ClientRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, client: Client) -> Client:
        if client.id is None:
            row = ClientORM(
                name=client.name,
                username=client.username,
                product_id=client.product_id,
                role=client.role.value,
                created_at=client.created_at,
            )
            self._session.add(row)
        else:
            row = self._session.get(ClientORM, client.id)
            row.name = client.name
            row.username = client.username
            row.product_id = client.product_id
            row.role = client.role.value
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def find_all(self) -> list[Client]:
        rows = self._session.execute(select(ClientORM)).scalars().all()
        return [_to_domain(row) for row in rows]

    def find_by_id(self, client_id: int) -> Client | None:
        row = self._session.get(ClientORM, client_id)
        return _to_domain(row) if row else None

    def find_by_name(self, name: str) -> list[Client]:
        rows = (
            self._session.execute(select(ClientORM).where(ClientORM.name == name))
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]

    def find_by_product_id(self, product_id: int) -> list[Client]:
        rows = (
            self._session.execute(
                select(ClientORM).where(ClientORM.product_id == product_id)
            )
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]

    def delete_by_id(self, client_id: int) -> None:
        row = self._session.get(ClientORM, client_id)
        if row is not None:
            self._session.delete(row)
            self._session.commit()
