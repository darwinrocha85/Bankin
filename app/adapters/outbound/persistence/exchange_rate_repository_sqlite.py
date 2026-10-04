"""Adaptador de salida: implementa el puerto ExchangeRateRepository en SQLite.

La tabla es append-only: cada `save` inserta una fila nueva (histórico).
"""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.orm_models import ExchangeRateORM
from app.domain.models import Currency, ExchangeRate
from app.domain.ports import ExchangeRateRepository


def _to_domain(row: ExchangeRateORM) -> ExchangeRate:
    return ExchangeRate(
        id=row.id,
        base_currency=Currency(row.base_currency),
        target_currency=Currency(row.target_currency),
        rate=row.rate,
        created_by=row.created_by,
        created_at=row.created_at,
    )


class SqliteExchangeRateRepository(ExchangeRateRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, rate: ExchangeRate) -> ExchangeRate:
        row = ExchangeRateORM(
            base_currency=rate.base_currency.value,
            target_currency=rate.target_currency.value,
            rate=rate.rate,
            created_by=rate.created_by,
            created_at=rate.created_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def find_latest(self, base: Currency, target: Currency) -> ExchangeRate | None:
        row = self._session.execute(
            select(ExchangeRateORM)
            .where(
                ExchangeRateORM.base_currency == base.value,
                ExchangeRateORM.target_currency == target.value,
            )
            .order_by(desc(ExchangeRateORM.id))
            .limit(1)
        ).scalar_one_or_none()
        return _to_domain(row) if row else None

    def find_history(
        self,
        base: Currency | None = None,
        target: Currency | None = None,
        limit: int = 100,
    ) -> list[ExchangeRate]:
        stmt = select(ExchangeRateORM).order_by(desc(ExchangeRateORM.id))
        if base is not None:
            stmt = stmt.where(ExchangeRateORM.base_currency == base.value)
        if target is not None:
            stmt = stmt.where(ExchangeRateORM.target_currency == target.value)
        rows = self._session.execute(stmt.limit(limit)).scalars().all()
        return [_to_domain(row) for row in rows]

    def find_all_latest(self) -> list[ExchangeRate]:
        """La más reciente por par. Implementación simple en Python (pocos
        pares posibles: 3 monedas -> 6 pares dirigidos)."""
        rows = (
            self._session.execute(select(ExchangeRateORM).order_by(desc(ExchangeRateORM.id)))
            .scalars()
            .all()
        )
        seen: dict[tuple[str, str], ExchangeRateORM] = {}
        for row in rows:  # ya vienen de más reciente a más vieja
            key = (row.base_currency, row.target_currency)
            if key not in seen:
                seen[key] = row
        return [_to_domain(row) for row in seen.values()]
