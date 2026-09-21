# BankIn Backend — ROADMAP

Fases de evolución. Cada fase funcionó y se desplegó antes de empezar la siguiente.
Detalle de cada fase: `docs/PHASE_0X-*.md` (crear al archivar los `fase*.ps1` sueltos).

- [x] Fase 1 — Migración Java → Python + arquitectura hexagonal (clientes punta a punta)
- [x] Fase 2 — Tarjetas y transacciones (emitir/activar/cancelar, compra/recarga, anulación con reverso)
- [x] Fase 3 — Rol gerente (overview, vista 360, anulación exclusiva con `?manager_id=`)
- [x] Fase 4 — Despliegue (Render + `AUTO_SEED`, CORS con Firebase, `GET /health`)
- [x] Fase 5 — API de cobro externa (`POST /purchase` + `POST /{id}/reverse`, `X-Api-Key` opcional, `note` de origen)
- [x] Fase 6 — `BANKIN-INTEGRATION.md` canónico en `Bankin/docs/` (2026-09-21), raíz borrada, stub en `spacecraftSystem/`
- [ ] Fase 7 — Pendiente que pidas (ej: idempotencia de cobro, Postgres): no empezar sin issue explícito
