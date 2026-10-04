"""Casos de uso del Gerente: ver toda la información del banco.

Reglas acordadas para este demo: sin login real. En vez de eso, cada
endpoint de gerente recibe el id del cliente que está pidiendo la info
(manager_id) y este servicio verifica que ese cliente exista y tenga
role=MANAGER antes de devolver nada. Es una autorización simple basada en
el rol, sin sesiones ni tokens -- suficiente para demostrar el concepto.
"""
from __future__ import annotations

from app.domain.models import CardStatus, Role, TransactionStatus, TransactionType
from app.domain.ports import CardRepository, ClientRepository, TransactionRepository


class ManagerNotFoundError(Exception):
    """El manager_id no corresponde a ningún cliente."""


class NotAManagerError(Exception):
    """El cliente existe pero no tiene rol MANAGER."""


class ManagerService:
    def __init__(
        self,
        client_repository: ClientRepository,
        card_repository: CardRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._clients = client_repository
        self._cards = card_repository
        self._transactions = transaction_repository

    def require_manager(self, manager_id: int) -> None:
        """Verifica que manager_id sea un cliente existente con role=MANAGER.

        Público (sin "_") porque otros routers -- no solo el de gerente --
        también necesitan exigir este chequeo, por ejemplo anular una
        transacción (ver routers/transactions.py).
        """
        client = self._clients.find_by_id(manager_id)
        if client is None:
            raise ManagerNotFoundError(f"No existe el cliente {manager_id}")
        if client.role != Role.MANAGER:
            raise NotAManagerError(
                f"El cliente {manager_id} no tiene rol MANAGER, no puede ver esta info"
            )

    def get_bank_overview(self, manager_id: int) -> dict:
        self.require_manager(manager_id)

        clients = self._clients.find_all()
        cards = self._cards.find_all()
        transactions = self._transactions.find_all()

        cards_by_status = {status.value: 0 for status in CardStatus}
        cards_by_currency: dict[str, int] = {}
        balances_by_currency: dict[str, float] = {}
        for card in cards:
            cards_by_status[card.status.value] += 1
            cur = card.currency.value
            cards_by_currency[cur] = cards_by_currency.get(cur, 0) + 1
            if card.status == CardStatus.ACTIVE:
                balances_by_currency[cur] = balances_by_currency.get(cur, 0) + card.balance

        transactions_by_type = {t.value: 0 for t in TransactionType}
        for tx in transactions:
            transactions_by_type[tx.type.value] += 1

        total_balance_active = sum(
            card.balance for card in cards if card.status == CardStatus.ACTIVE
        )
        purchased_by_currency: dict[str, float] = {}
        recharged_by_currency: dict[str, float] = {}
        for tx in transactions:
            if tx.status != TransactionStatus.COMPLETED:
                continue
            cur = tx.currency.value
            if tx.type == TransactionType.PURCHASE:
                purchased_by_currency[cur] = purchased_by_currency.get(cur, 0) + tx.amount
            elif tx.type == TransactionType.RECHARGE:
                recharged_by_currency[cur] = recharged_by_currency.get(cur, 0) + tx.amount

        return {
            "total_clients": sum(1 for c in clients if c.role == Role.CLIENT),
            "total_managers": sum(1 for c in clients if c.role == Role.MANAGER),
            "total_cards": len(cards),
            "cards_by_status": cards_by_status,
            "cards_by_currency": cards_by_currency,
            "total_balance_in_active_cards": total_balance_active,
            "balances_by_currency": balances_by_currency,
            "total_transactions": len(transactions),
            "transactions_by_type": transactions_by_type,
            "total_purchased_amount": sum(purchased_by_currency.values()),
            "total_recharged_amount": sum(recharged_by_currency.values()),
            "purchased_by_currency": purchased_by_currency,
            "recharged_by_currency": recharged_by_currency,
        }

    def list_all_clients(self, manager_id: int):
        self.require_manager(manager_id)
        return self._clients.find_all()

    def list_all_cards(self, manager_id: int):
        self.require_manager(manager_id)
        return self._cards.find_all()

    def list_all_transactions(self, manager_id: int):
        self.require_manager(manager_id)
        return self._transactions.find_all()

    def get_client_overview(self, manager_id: int, client_id: int) -> dict:
        """Vista 360 de un cliente: sus datos, sus tarjetas y todas sus
        transacciones -- 'toda la info relacionada' que pediste que el
        gerente pueda ver.
        """
        self.require_manager(manager_id)

        client = self._clients.find_by_id(client_id)
        if client is None:
            raise ManagerNotFoundError(f"No existe el cliente {client_id}")

        cards = self._cards.find_by_client_id(client_id)
        transactions = []
        for card in cards:
            transactions.extend(self._transactions.find_by_card_id(card.card_id))

        return {"client": client, "cards": cards, "transactions": transactions}
