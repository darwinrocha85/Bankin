"""Casos de uso relacionados con Tarjetas.

Reproduce (y mejora un poco) la lógica que estaba en
CardCreditRestController.java: emitir una tarjeta para un cliente, activarla
(enroll), cancelarla, y consultar/actualizar su balance.
"""
from __future__ import annotations

import random
from datetime import datetime

from app.domain.models import Card, CardStatus
from app.domain.ports import CardRepository, ClientRepository


class CardNotFoundError(Exception):
    pass


class ClientNotFoundForCardError(Exception):
    pass


def _generate_card_id(product_id: int) -> str:
    """Genera un número de tarjeta: product_id + dígitos aleatorios,
    igual que hacía la versión Java (CardCreditRestController.getCardCreditCreated).
    """
    random_digits = str(random.randint(0, 10**10 - 1)).zfill(10)
    return f"{product_id}{random_digits}"


def _expiry_in_3_years() -> str:
    """Devuelve la fecha de expiración en formato MM/YYYY, 3 años a futuro."""
    now = datetime.utcnow()
    year = now.year + 3
    return f"{now.month}/{year}"


class CardService:
    def __init__(self, card_repository: CardRepository, client_repository: ClientRepository) -> None:
        self._cards = card_repository
        self._clients = client_repository

    def issue_card(self, client_id: int) -> Card:
        """Emite una tarjeta nueva para un cliente existente. Equivale a
        GET /card/{productId}/number en Java (aquí, más correctamente, es un POST).
        """
        client = self._clients.find_by_id(client_id)
        if client is None:
            raise ClientNotFoundForCardError(f"No existe el cliente {client_id}")

        card = Card(
            client_id=client.id,
            card_id=_generate_card_id(client.product_id),
            cardholder_name=client.name,
            date_expires=_expiry_in_3_years(),
            balance=100,  # balance inicial, igual que en la versión Java
            status=CardStatus.CREATED,
        )
        return self._cards.save(card)

    def list_cards(self) -> list[Card]:
        return self._cards.find_all()

    def list_cards_for_client(self, client_id: int) -> list[Card]:
        return self._cards.find_by_client_id(client_id)

    def get_card(self, card_id: str) -> Card:
        card = self._cards.find_by_card_id(card_id)
        if card is None:
            raise CardNotFoundError(f"No existe la tarjeta {card_id}")
        return card

    def activate_card(self, card_id: str) -> Card:
        """Equivale a POST /card/enroll: activa una tarjeta creada."""
        card = self.get_card(card_id)
        card.status = CardStatus.ACTIVE
        card.updated_at = datetime.utcnow()
        return self._cards.save(card)

    def cancel_card(self, card_id: str) -> Card:
        """Equivale a DELETE /card/{cardId}: en Java esto no borraba la fila,
        solo marcaba status=2. Mantenemos ese comportamiento (baja lógica).
        """
        card = self.get_card(card_id)
        card.status = CardStatus.CANCELLED
        card.updated_at = datetime.utcnow()
        return self._cards.save(card)

    def update_balance(self, card_id: str, balance: int) -> Card:
        card = self.get_card(card_id)
        card.balance = balance
        card.updated_at = datetime.utcnow()
        return self._cards.save(card)

    def get_balance(self, card_id: str) -> int:
        return self.get_card(card_id).balance
