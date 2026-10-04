# BankIn Backend — ROADMAP

Fases de evolución. Cada fase funcionó y se desplegó antes de empezar la siguiente.
Detalle de cada fase: `docs/PHASE_0X-*.md` (crear al archivar los `fase*.ps1` sueltos).

- [x] Fase 1 — Migración Java → Python + arquitectura hexagonal (clientes punta a punta)
- [x] Fase 2 — Tarjetas y transacciones (emitir/activar/cancelar, compra/recarga, anulación con reverso)
- [x] Fase 3 — Rol gerente (overview, vista 360, anulación exclusiva con `?manager_id=`)
- [x] Fase 4 — Despliegue (Render + `AUTO_SEED`, CORS con Firebase, `GET /health`)
- [x] Fase 5 — API de cobro externa (`POST /purchase` + `POST /{id}/reverse`, `X-Api-Key` opcional, `note` de origen)
- [x] Fase 6 — `BANKIN-INTEGRATION.md` canónico en `Bankin/docs/` (2026-09-21), raíz borrada, stub en `spacecraftSystem/`
- [x] Fase 7 — Multimoneda (2026-10-03): `Currency` COP/USD/EUR, 1 tarjeta por
  (cliente, moneda) con `409` en duplicada, conversión en purchase/recharge con
  tasa vigente y `rate_used` congelada (reversa exacta), tabla `exchange_rates`
  append-only con histórico (`GET /exchange-rates`, `/history`, `/convert`,
  `POST` solo gerente), overview con desglose por moneda. Esquema v2: el
  `bankin.db` v1 se borra y se regenera con `seed_data.py`.
- [ ] Fase 8 — Pendiente que pidas (ej: frontend multimoneda, idempotencia de
  cobro, Postgres): no empezar sin issue explícito
- [x] Fase 8 — Órdenes multitramo (2026-10-04): `payment_orders` + `payment_tranches`
  (precio base siempre EUR, tramos BankIn en cualquier moneda con conversión y
  `rate_to_eur` congelada, `PENDING→PARTIAL→PAID`, sobrepago 400,
  `idempotency_key` por tramo, `cancel` reversa tramos BankIn). Adyen como
  intención + confirmación stub (`adyen-intents`, `adyen-tranches/{id}/confirm`)
  hasta integrar la pasarela real. Tablas nuevas auto-creadas por `init_db`.
