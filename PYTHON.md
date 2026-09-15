# BankIn (Python)

Migración progresiva del demo BankIn de Java/Spring Boot a Python, usando
**arquitectura hexagonal** (puertos y adaptadores) con **FastAPI** y
**SQLite**.

Este es el resultado de la **iteración 1**: el módulo de **Clientes**
funcionando de punta a punta (dominio, casos de uso, persistencia SQLite y
API REST). Las siguientes iteraciones añadirán Tarjetas, Transacciones y la
vista de Gerente.

## Por qué SQLite (y no H2)

H2 es una base embebida específica de Java; no existe en el mundo Python.
El equivalente natural aquí es **SQLite en archivo** (`bankin.db`, no
`:memory:`), así que los datos persisten entre reinicios del servidor. Si
en el futuro se necesita algo más "real" (Postgres, por ejemplo), solo hay
que escribir un nuevo adaptador que implemente los mismos puertos definidos
en `app/domain/ports.py` — el dominio y los casos de uso no cambian.

## Estructura (arquitectura hexagonal)

```
app/
  domain/               <- Núcleo: entidades y puertos (interfaces). Sin
                           dependencias de frameworks.
    models.py           <- Client, Role (CLIENT / MANAGER)
    ports.py             <- ClientRepository (contrato abstracto)

  application/           <- Casos de uso. Dependen solo de los puertos.
    client_service.py

  adapters/
    inbound/api/          <- Adaptador de entrada: FastAPI
      routers/clients.py  <- Rutas HTTP /clients
      schemas.py           <- DTOs (Pydantic)
      deps.py               <- Wiring (conecta adaptador SQLite con los casos de uso)

    outbound/persistence/ <- Adaptador de salida: SQLite vía SQLAlchemy
      db.py
      orm_models.py
      client_repository_sqlite.py   <- Implementa el puerto ClientRepository

  main.py                <- Arranque de la app FastAPI
```

La regla de oro de la arquitectura hexagonal: las flechas de dependencia
siempre apuntan hacia `domain/`. Los adaptadores (API, base de datos)
dependen del dominio; el dominio no sabe que existen.

## Cómo correrlo

```bash
python -m venv venv
venv\Scripts\activate        # en Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Documentación interactiva (Swagger) en http://localhost:8000/docs

## Endpoints actuales

| Método | Ruta            | Descripción                              |
|--------|-----------------|-------------------------------------------|
| GET    | /clients        | Lista todos los clientes (filtro `?name=`)|
| GET    | /clients/{id}   | Obtiene un cliente por id                 |
| POST   | /clients        | Crea un cliente                           |
| PUT    | /clients/{id}   | Actualiza un cliente                      |
| DELETE | /clients/{id}   | Elimina un cliente                        |
| GET    | /health         | Health check                              |

Nota: las rutas se modernizaron respecto a la colección Postman original de
Java (`/card/person*` -> `/clients`). Habrá que actualizar/crear una nueva
colección Postman más adelante.

## Próximas iteraciones

1. Módulo de Tarjetas (`/cards`) — creación, activación (`enroll`), balance.
2. Módulo de Transacciones (`/transactions`) — compra y anulación, con
   descuento/reintegro real del balance de la tarjeta (en Java esto estaba
   incompleto a propósito).
3. Vista de Gerente (`/manager/...`) — endpoints que agregan info de todos
   los clientes, tarjetas y transacciones, usando el campo `role` del
   Cliente para distinguir CLIENTE de GERENTE (sin login real, según lo
   acordado).
4. Cuando el módulo Python cubra toda la funcionalidad de Java, se retira
   el proyecto Java (`src/`, `pom.xml`, etc.).
