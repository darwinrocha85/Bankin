# BankIn Backend — AGENTS.md

> Proyecto independiente. Abrir opencode con cwd en `Bankin/`, nunca en `Projects/`.
> Stack: Python 3.12, FastAPI, SQLAlchemy, SQLite en archivo (`bankin.db`).

## Cómo correr (bloques completos en `Projects/RUNBOOK.md` §1 instalar / §2 local)
- Instalar (una vez): `python -m venv venv` + `.\venv\Scripts\Activate.ps1` + `python -m pip install -r requirements.txt` + `Copy-Item .env.example .env` + `python seed_data.py` (seed opcional)
- Correr: `.\venv\Scripts\Activate.ps1` + `python -m uvicorn app.main:app --reload --port 8000`
- Swagger: `http://localhost:8000/docs` — validar ahí antes de tocar el frontend
- En Render las mismas claves del `.env` van en Dashboard → Environment.

## Arquitectura (hexagonal, obligatoria)
```
app/domain/            <- entidades + ports.py. CERO imports de fastapi/sqlalchemy.
app/application/       <- casos de uso. Solo dependen de los puertos.
app/adapters/inbound/api/   <- routers, schemas.py (DTOs), deps.py (wiring)
app/adapters/outbound/persistence/ <- SQLAlchemy, implementan los puertos
```
Regla de oro: las dependencias apuntan hacia `domain/`. Nuevo motor de BD =
nuevo adaptador que implemente `app/domain/ports.py`, dominio intacto.

## Reglas de negocio que no se rompen
- Tarjeta: `CREATED → ACTIVE → CANCELLED` (baja lógica, nunca DELETE físico).
- Transacción auditable: `PURCHASE` descuenta, `RECHARGE` aumenta. Anular revierte
  el balance; anular una recarga ya gastada falla con 400.
- Gerente: sin login real, `?manager_id=` + validación de `role=MANAGER` en servidor.
- `POST /transactions/purchase` + `POST /transactions/{id}/reverse` son el contrato
  con apps externas (guía: `docs/BANKIN-INTEGRATION.md`, canónico en este repo).
  Cambiar ese contrato = avisar a naveSpace y taller.

## No hacer
- No commitear `.env`, `*.db`, `venv/`, `__pycache__/` (ya en `.gitignore`).
- No agregar auth real / JWT / Postgres sin pedirlo explícito.
- No renombrar puertos ni routers existentes: el frontend y naveSpace dependen de ellos.
- No tocar CORS para un solo frontend sin revisar `ALLOWED_ORIGINS` y los demás consumidores.
