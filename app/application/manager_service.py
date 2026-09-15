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

    def _require_manager(self, manager_id: int) -> None:
        client = self._clients.find_by_id(manager_id)
        if client is None:
            raise ManagerNotFoundError(f"No existe el cliente {manager_id}")
        if client.role != Role.MANAGER:
            raise NotAManagerError(
                f"El cliente {manager_id} no tiene rol MANAGER, no puede ver esta info"
            )

    def get_bank_overview(self, manager_id: int) -> dict:
        self._require_manager(manager_id)

        clients = self._clients.find_all()
        cards = self._cards.find_all()
        transactions = self._transactions.find_all()

        cards_by_status = {status.value: 0 for status in CardStatus}
        for card in cards:
            cards_by_status[card.status.value] += 1

        transactions_by_type = {t.value: 0 for t in TransactionType}
        for tx in transactions:
            transactions_by_type[tx.type.value] += 1

        total_balance_active = sum(
            card.balance for card in cards if card.status == CardStatus.ACTIVE
        )
        total_purchased = sum(
            tx.amount
            for tx in transactions
            if tx.type == TransactionType.PURCHASE and tx.status == TransactionStatus.COMPLETED
        )
        total_recharged = sum(
            tx.amount
            for tx in transactions
            if tx.type == TransactionType.RECHARGE and tx.status == TransactionStatus.COMPLETED
        )

        return {
            "total_clients": sum(1 for c in clients if c.role == Role.CLIENT),
            "total_managers": sum(1 for c in clients if c.role == Role.MANAGER),
            "total_cards": len(cards),
            "cards_by_status": cards_by_status,
            "total_balance_in_active_cards": total_balance_active,
            "total_transactions": len(transactions),
            "transactions_by_type": transactions_by_type,
            "total_purchased_amount": total_purchased,
            "total_recharged_amount": total_recharged,
        }

    def list_all_clients(self, manager_id: int):
        self._require_manager(manager_id)
        return self._clients.find_all()

    def list_all_cards(self, manager_id: int):
        self._require_manager(manager_id)
        return self._cards.find_all()

    def list_all_transactions(self, manager_id: int):
        self._require_manager(manager_id)
        return self._transactions.find_all()

    def get_client_overview(self, manager_id: int, client_id: int) -> dict:
        """Vista 360 de un cliente: sus datos, sus tarjetas y todas sus
        transacciones -- 'toda la info relacionada' que pediste que el
        gerente pueda ver.
        """
        self._require_manager(manager_id)

        client = self._clients.find_by_id(client_id)
        if client is None:
            raise ManagerNotFoundError(f"No existe el cliente {client_id}")

        cards = self._cards.find_by_client_id(client_id)
        transactions = []
        for card in cards:
            transactions.extend(self._transactions.find_by_card_id(card.card_id))

        return {"client": client, "cards": cards, "transactions": transactions}
