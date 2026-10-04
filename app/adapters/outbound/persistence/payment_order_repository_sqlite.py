"""Adaptador de salida: órdenes de pago multitramo en SQLite."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.orm_models import PaymentOrderORM, PaymentTrancheORM
from app.domain.models import (
    Currency,
    PaymentOrder,
    PaymentOrderStatus,
    PaymentProvider,
    PaymentTranche,
)
from app.domain.ports import PaymentOrderRepository


def _order_to_domain(row: PaymentOrderORM) -> PaymentOrder:
    return PaymentOrder(
        id=row.id,
        reference=row.reference,
        total_eur=row.total_eur,
        paid_eur=row.paid_eur,
        status=PaymentOrderStatus(row.status),
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _tranche_to_domain(row: PaymentTrancheORM) -> PaymentTranche:
    return PaymentTranche(
        id=row.id,
        order_id=row.order_id,
        provider=PaymentProvider(row.provider),
        charge_amount=row.charge_amount,
        charge_currency=Currency(row.charge_currency),
        converted_eur=row.converted_eur,
        rate_to_eur=row.rate_to_eur,
        confirmed=bool(row.confirmed),
        card_id=row.card_id,
        bankin_transaction_id=row.bankin_transaction_id,
        adyen_reference=row.adyen_reference,
        note=row.note,
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
    )


class SqlitePaymentOrderRepository(PaymentOrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_order(self, order: PaymentOrder) -> PaymentOrder:
        if order.id is None:
            row = PaymentOrderORM(
                reference=order.reference,
                total_eur=order.total_eur,
                paid_eur=order.paid_eur,
                status=order.status.value,
                note=order.note,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
            self._session.add(row)
        else:
            row = self._session.get(PaymentOrderORM, order.id)
            row.paid_eur = order.paid_eur
            row.status = order.status.value
            row.note = order.note
            row.updated_at = order.updated_at
        self._session.commit()
        self._session.refresh(row)
        return _order_to_domain(row)

    def find_order_by_id(self, order_id: int) -> PaymentOrder | None:
        row = self._session.get(PaymentOrderORM, order_id)
        return _order_to_domain(row) if row else None

    def find_order_by_reference(self, reference: str) -> PaymentOrder | None:
        row = (
            self._session.execute(
                select(PaymentOrderORM).where(PaymentOrderORM.reference == reference)
            )
            .scalars()
            .first()
        )
        return _order_to_domain(row) if row else None

    def save_tranche(self, tranche: PaymentTranche) -> PaymentTranche:
        row = PaymentTrancheORM(
            order_id=tranche.order_id,
            provider=tranche.provider.value,
            charge_amount=tranche.charge_amount,
            charge_currency=tranche.charge_currency.value,
            converted_eur=tranche.converted_eur,
            rate_to_eur=tranche.rate_to_eur,
            confirmed=int(tranche.confirmed),
            card_id=tranche.card_id,
            bankin_transaction_id=tranche.bankin_transaction_id,
            adyen_reference=tranche.adyen_reference,
            note=tranche.note,
            idempotency_key=tranche.idempotency_key,
            created_at=tranche.created_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _tranche_to_domain(row)

    def find_tranches_by_order(self, order_id: int) -> list[PaymentTranche]:
        rows = (
            self._session.execute(
                select(PaymentTrancheORM)
                .where(PaymentTrancheORM.order_id == order_id)
                .order_by(PaymentTrancheORM.id)
            )
            .scalars()
            .all()
        )
        return [_tranche_to_domain(r) for r in rows]

    def find_tranche_by_id(self, tranche_id: int) -> PaymentTranche | None:
        row = self._session.get(PaymentTrancheORM, tranche_id)
        return _tranche_to_domain(row) if row else None

    def find_tranche_by_idempotency(self, order_id: int, key: str) -> PaymentTranche | None:
        row = (
            self._session.execute(
                select(PaymentTrancheORM).where(
                    PaymentTrancheORM.order_id == order_id,
                    PaymentTrancheORM.idempotency_key == key,
                )
            )
            .scalars()
            .first()
        )
        return _tranche_to_domain(row) if row else None

    def mark_tranche_confirmed(self, tranche_id: int) -> PaymentTranche | None:
        row = self._session.get(PaymentTrancheORM, tranche_id)
        if row is None:
            return None
        row.confirmed = 1
        self._session.commit()
        self._session.refresh(row)
        return _tranche_to_domain(row)
