# BankIn

Demo de banco construida en **Python** con **arquitectura hexagonal** (puertos
y adaptadores), **FastAPI** y **SQLite**.

> Este proyecto empezó como un ejemplo en Java/Spring Boot y se migró
> progresivamente a Python. Ya no queda código Java en el repo.

## Por qué SQLite (y no H2)

H2 es una base embebida específica de Java; no existe en el mundo Python.
El equivalente natural aquí es **SQLite en archivo** (`bankin.db`, no
`:memory:`), así que los datos persisten entre reinicios del servidor.

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

## Cómo correrlo

```bash
python -m venv venv
venv\Scripts\activate        # en Windows (si PowerShell bloquea el script,
                              # corre antes: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Documentación interactiva (Swagger) en http://localhost:8000/docs

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
| GET    | /cards                     | Lista todas                       |
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
