"""Puebla la base de datos con datos de prueba multimoneda.

Crea un gerente, varios clientes con tarjetas en distintas monedas (cada
cliente elige cuáles: máx. una tarjeta por moneda), algunas transacciones
(compras, recargas, una anulación, una compra con conversión de moneda) y
las tasas de cambio iniciales cargadas por el gerente.

Uso local:
    python seed_data.py

Si ya hay datos (detecta al gerente "gerente1"), no hace nada.
"""
from __future__ import annotations

from app.adapters.outbound.persistence.card_repository_sqlite import SqliteCardRepository
from app.adapters.outbound.persistence.client_repository_sqlite import SqliteClientRepository
from app.adapters.outbound.persistence.db import SessionLocal, init_db
from app.adapters.outbound.persistence.exchange_rate_repository_sqlite import (
    SqliteExchangeRateRepository,
)
from app.adapters.outbound.persistence.transaction_repository_sqlite import (
    SqliteTransactionRepository,
)
from app.application.card_service import CardService
from app.application.client_service import ClientService
from app.application.exchange_rate_service import ExchangeRateService
from app.application.transaction_service import TransactionService
from app.domain.models import Currency, Role


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
        rates = ExchangeRateService(SqliteExchangeRateRepository(session))
        transactions = TransactionService(
            SqliteTransactionRepository(session),
            SqliteCardRepository(session),
            rates,
        )

        existing_manager = clients.find_by_name("Sebastian Jefe")
        if existing_manager:
            log("Ya hay datos de prueba (encontré a 'Sebastian Jefe'). No hago nada.")
            return False

        log("Creando gerente...")
        gerente = clients.create_client("Sebastian Jefe", "gerente1", 900001, role=Role.MANAGER)
        log(f"  -> gerente id={gerente.id} (usa este id como manager_id en el frontend)")

        # Tasas iniciales (base -> target: 1 unidad de base = rate de target)
        rates.create_rate(Currency.USD, Currency.COP, 4100.0, created_by=gerente.id)
        rates.create_rate(Currency.EUR, Currency.COP, 4450.0, created_by=gerente.id)
        rates.create_rate(Currency.EUR, Currency.USD, 1.09, created_by=gerente.id)
        log("  Tasas iniciales: USD->COP 4100, EUR->COP 4450, EUR->USD 1.09")

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

        # Darwin: tarjetas COP + USD activas, con movimientos (incl. compra
        # en USD contra la tarjeta COP, para ver la conversión)
        darwin = creados[0]
        cop = cards.issue_card(darwin.id, Currency.COP)
        cards.activate_card(cop.card_id)
        usd = cards.issue_card(darwin.id, Currency.USD)
        cards.activate_card(usd.card_id)
        transactions.recharge(cop.card_id, 1_000_000)
        transactions.purchase(cop.card_id, 250_000)
        transactions.purchase(cop.card_id, 50, currency=Currency.USD)  # conversión
        transactions.recharge(usd.card_id, 500)
        transactions.purchase(usd.card_id, 80)
        log(f"  Tarjetas de {darwin.name}: COP + USD (ACTIVE, con movimientos)")

        # Ana: tarjeta EUR activa, con una transacción anulada
        ana = creados[1]
        eur = cards.issue_card(ana.id, Currency.EUR)
        cards.activate_card(eur.card_id)
        recarga = transactions.recharge(eur.card_id, 500)
        transactions.annul(recarga.id)
        log(f"  Tarjeta de {ana.name}: EUR (ACTIVE, con una recarga anulada)")

        # Luis: tarjeta COP recién emitida, sin activar
        luis = creados[2]
        card = cards.issue_card(luis.id, Currency.COP)
        log(f"  Tarjeta de {luis.name}: COP (CREATED, sin activar)")

        # Maria: tarjeta COP activa y luego cancelada
        maria = creados[3]
        card = cards.issue_card(maria.id, Currency.COP)
        cards.activate_card(card.card_id)
        cards.cancel_card(card.card_id)
        log(f"  Tarjeta de {maria.name}: COP (CANCELLED)")

        log("\nListo. Datos de prueba creados.")
        log(f"manager_id para el frontend / Postman: {gerente.id}")
        return True
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    run_seed()
