# BankIn

Demo de banco construida en **Python** con **arquitectura hexagonal** (puertos
y adaptadores), **FastAPI** y **SQLite**. Tiene un frontend en React aparte,
en la carpeta hermana `Bankin-frontend`.

> Este proyecto empezó como un ejemplo en Java/Spring Boot y se migró
> progresivamente a Python. Ya no queda código Java en el repo.

## Por qué SQLite (y no H2)

H2 es una base embebida específica de Java; no existe en el mundo Python.
El equivalente natural aquí es **SQLite en archivo** (`bankin.db`, no
`:memory:`), así que los datos persisten entre reinicios del servidor.

⚠️ **Excepción importante en Render** (ver la sección de despliegue más
abajo): el disco del plan gratuito de Render es efímero, así que ahí
`bankin.db` sí se pierde en cada redeploy — se soluciona con `AUTO_SEED`.

## Arquitectura hexagonal

```
app/
  domain/                 <- Núcleo: entidades y puertos (interfaces).
                              Sin dependencias de frameworks.
    models.py              <- Client, Role, Card, CardStatus, Transaction, TransactionType
    ports.py                <- ClientRepository, CardRepository, TransactionRepository

  application/             <- Casos de uso. Dependen solo de los puertos.
    client_service.py
    card_service.py
    transaction_service.py
    manager_service.py

  adapters/
    inbound/api/            <- Adaptador de entrada: FastAPI
      routers/               <- clients.py, cards.py, transactions.py, manager.py
      schemas.py               <- DTOs (Pydantic)
      deps.py                   <- Wiring (conecta SQLite con los casos de uso)

    outbound/persistence/   <- Adaptador de salida: SQLite vía SQLAlchemy
      db.py
      orm_models.py
      *_repository_sqlite.py  <- Implementan los puertos de arriba

  main.py                  <- Arranque de la app FastAPI
```

La regla de oro: las flechas de dependencia siempre apuntan hacia `domain/`.
Los adaptadores (API, base de datos) dependen del dominio; el dominio no
sabe que existen.

## Cómo correrlo en local

```bash
python -m venv venv
venv\Scripts\activate        # en Windows (si PowerShell bloquea el script,
                              # corre antes: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
pip install -r requirements.txt
python seed_data.py          # opcional: crea datos de prueba
uvicorn app.main:app --reload
```

Documentación interactiva (Swagger) en http://localhost:8000/docs

## Configuración por entorno

El backend sabe si está en local o desplegado a través de variables de
entorno (ver `.env.example`). En local, si existe un archivo `.env` en esta
carpeta, se carga automáticamente (copia `.env.example` a `.env` para
personalizarlo). En Render, estas mismas variables se configuran desde su
dashboard (Settings → Environment) — ahí no hace falta un archivo `.env`.

| Variable          | Para qué sirve                                                                 | Default   |
|--------------------|--------------------------------------------------------------------------------|-----------|
| `ENVIRONMENT`      | "local" o "production". Solo informativo, se ve en `GET /health`.              | `local`   |
| `ALLOWED_ORIGINS`  | Orígenes extra para CORS, separados por coma (la URL de Firebase Hosting).     | (vacío)   |
| `AUTO_SEED`        | "true" para poblar la base con datos de prueba al arrancar si está vacía.      | `false`   |
| `BANKIN_DB_PATH`   | Ruta del archivo SQLite.                                                       | `bankin.db` |

Los orígenes de desarrollo local (`localhost:5173`) siempre están permitidos
por CORS, en cualquier entorno, así que no hace falta agregarlos a mano.

## Despliegue en Render

1. En el dashboard de Render, crea un **Web Service** apuntando a este repo
   (o usa el `render.yaml` incluido con "New → Blueprint").
2. Configuración (si lo haces a mano en vez de con el blueprint):
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     (Render inyecta `$PORT`; hay que escuchar en `0.0.0.0`, no en
     `127.0.0.1`, para que sea accesible desde fuera del contenedor)
3. Variables de entorno en Render (Settings → Environment):
   - `ENVIRONMENT=production`
   - `AUTO_SEED=true` (ver el aviso del disco efímero abajo)
   - `ALLOWED_ORIGINS=https://tu-proyecto.web.app,https://tu-proyecto.firebaseapp.com`
     (rellena esto con la URL real una vez que despliegues el frontend en
     Firebase Hosting; Firebase te da ambos dominios)

### ⚠️ El disco de Render (plan gratuito) es efímero

El plan gratuito de Render no tiene disco persistente garantizado: el
archivo `bankin.db` puede perderse en cada redeploy o reinicio del
servicio. Para un demo, la solución simple es `AUTO_SEED=true`: al
arrancar, si la base está vacía, se vuelve a poblar sola con
`seed_data.py` (revisa esa lógica en `app/main.py`, función `lifespan`).

Si en algún momento necesitas que los datos sí persistan de verdad entre
despliegues (más allá de un demo), las opciones son un **Persistent Disk**
de Render (de pago) montado en la ruta de `BANKIN_DB_PATH`, o migrar a un
**Postgres gestionado** (Render ofrece un plan gratuito) escribiendo un
nuevo adaptador que implemente los mismos puertos de `app/domain/ports.py`
— el dominio y los casos de uso no cambiarían.

## Dominio

- **Cliente**: puede tener rol `CLIENT` o `MANAGER`.
- **Tarjeta**: pertenece a un cliente (`client_id`), tiene estado
  `CREATED` → `ACTIVE` → `CANCELLED`.
- **Transacción**: `PURCHASE` (compra, descuenta saldo) o `RECHARGE`
  (recarga, aumenta saldo). Puede anularse, lo que revierte su efecto en
  el balance (con validaciones: no se puede anular una recarga si ese
  dinero ya se gastó).
- **Gerente**: puede ver toda la información del banco (todos los
  clientes, tarjetas y transacciones), no solo la suya. Sin login real:
  cada endpoint de gerente recibe `?manager_id=<id>` y se valida que ese
  cliente tenga `role=MANAGER`.

## Endpoints

### Clientes
| Método | Ruta            | Descripción                                |
|--------|-----------------|---------------------------------------------|
| GET    | /clients        | Lista todos (filtro `?name=`)                |
| GET    | /clients/{id}   | Obtiene uno                                  |
| POST   | /clients        | Crea uno (opcional `"role": "MANAGER"`)      |
| PUT    | /clients/{id}   | Actualiza                                    |
| DELETE | /clients/{id}   | Elimina                                      |

### Tarjetas
| Método | Ruta                       | Descripción                     |
|--------|----------------------------|-----------------------------------|
| GET    | /cards                     | Lista todas (filtro `?client_id=`)|
| POST   | /cards                     | Emite una tarjeta (`client_id`)   |
| GET    | /cards/{card_id}           | Obtiene una                       |
| POST   | /cards/{card_id}/activate  | Activa                            |
| DELETE | /cards/{card_id}           | Cancela (baja lógica)             |
| PUT    | /cards/{card_id}/balance   | Fija el balance manualmente       |
| GET    | /cards/{card_id}/balance   | Consulta el balance               |

### Transacciones
| Método | Ruta                          | Descripción                    |
|--------|-------------------------------|-----------------------------------|
| GET    | /transactions                 | Lista todas                       |
| GET    | /transactions/{id}            | Obtiene una                       |
| GET    | /transactions/card/{card_id}  | Historial de una tarjeta          |
| POST   | /transactions/purchase        | Compra (descuenta saldo)          |
| POST   | /transactions/recharge        | Recarga saldo                     |
| POST   | /transactions/{id}/annul      | Anula (revierte el balance)       |

### Gerente
| Método | Ruta                       | Descripción                           |
|--------|----------------------------|------------------------------------------|
| GET    | /manager/overview          | Dashboard con totales del banco          |
| GET    | /manager/clients           | Todos los clientes                       |
| GET    | /manager/clients/{id}      | Vista 360 de un cliente (datos+tarjetas+transacciones) |
| GET    | /manager/cards             | Todas las tarjetas del banco              |
| GET    | /manager/transactions      | Todas las transacciones del banco         |

Todas las rutas de gerente requieren `?manager_id=<id de un cliente con role=MANAGER>`.
