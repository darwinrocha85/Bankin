"""Puebla la base de datos con datos de prueba: un gerente, varios clientes,
tarjetas en distintos estados y transacciones (compras, recargas, una
anulación). Útil para tener algo que ver de entrada en el frontend.

Uso local:
    python seed_data.py

Reutiliza los mismos casos de uso (application/) que usa la API, en vez de
insertar filas a mano -- así los datos quedan siempre en un estado
consistente con las reglas de negocio reales (balances correctos, etc.).

Si ya hay datos (detecta al gerente "gerente1"), no hace nada: así puedes
correrlo varias veces sin duplicar, y también se puede llamar de forma
segura desde el arranque de la app (ver app/main.py, AUTO_SEED) para
repoblar automáticamente en Render, donde el disco es efímero y se pierde
en cada redeploy.
"""
from __future__ import annotations

from app.adapters.outbound.persistence.card_repository_sqlite import SqliteCardRepository
from app.adapters.outbound.persistence.client_repository_sqlite import SqliteClientRepository
from app.adapters.outbound.persistence.db import SessionLocal, init_db
from app.adapters.outbound.persistence.transaction_repository_sqlite import (
    SqliteTransactionRepository,
)
from app.application.card_service import CardService
from app.application.client_service import ClientService
from app.application.transaction_service import TransactionService
from app.domain.models import Role


def run_seed(verbose: bool = True) -> bool:
    """Puebla la base si está vacía. Devuelve True si creó datos, False si
    ya había (y no hizo nada).
    """

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    session = SessionLocal()
    try:
        clients = ClientService(SqliteClientRepository(session))
        cards = CardService(SqliteCardRepository(session), SqliteClientRepository(session))
        transactions = TransactionService(
            SqliteTransactionRepository(session), SqliteCardRepository(session)
        )

        existing_manager = clients.find_by_name("Sebastian Jefe")
        if existing_manager:
            log("Ya hay datos de prueba (encontré a 'Sebastian Jefe'). No hago nada.")
            return False

        log("Creando gerente...")
        gerente = clients.create_client("Sebastian Jefe", "gerente1", 900001, role=Role.MANAGER)
        log(f"  -> gerente id={gerente.id} (usa este id como manager_id en el frontend)")

        clientes_demo = [
            ("Darwin Rocha", "darwin", 112790),
            ("Ana Perez", "ana", 112791),
            ("Luis Gomez", "luisg", 112792),
            ("Maria Torres", "mariat", 112793),
        ]

        creados = []
        for name, username, product_id in clientes_demo:
            c = clients.create_client(name, username, product_id)
            log(f"Cliente creado: {c.name} (id={c.id})")
            creados.append(c)

        # Darwin: tarjeta activa, con recargas y compras (deja historial rico)
        darwin = creados[0]
        card = cards.issue_card(darwin.id)
        cards.activate_card(card.card_id)
        transactions.recharge(card.card_id, 1000)
        transactions.purchase(card.card_id, 250)
        transactions.purchase(card.card_id, 80)
        log(f"  Tarjeta de {darwin.name}: {card.card_id} (ACTIVE, con movimientos)")

        # Ana: tarjeta activa, con una transacción anulada (para ver ese estado)
        ana = creados[1]
        card = cards.issue_card(ana.id)
        cards.activate_card(card.card_id)
        recarga = transactions.recharge(card.card_id, 500)
        transactions.annul(recarga.id)
        log(f"  Tarjeta de {ana.name}: {card.card_id} (ACTIVE, con una recarga anulada)")

        # Luis: tarjeta recién emitida, sin activar (para ver ese estado)
        luis = creados[2]
        card = cards.issue_card(luis.id)
        log(f"  Tarjeta de {luis.name}: {card.card_id} (CREATED, sin activar)")

        # Maria: tarjeta activa y luego cancelada (para ver ese estado)
        maria = creados[3]
        card = cards.issue_card(maria.id)
        cards.activate_card(card.card_id)
        cards.cancel_card(card.card_id)
        log(f"  Tarjeta de {maria.name}: {card.card_id} (CANCELLED)")

        log("\nListo. Datos de prueba creados.")
        log(f"manager_id para el frontend / Postman: {gerente.id}")
        return True
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    run_seed()
