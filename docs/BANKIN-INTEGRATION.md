# Cobrar entradas de naveSpace con BankIn

> Documento canónico. Vive en el repo `Bankin` (`docs/BANKIN-INTEGRATION.md`).
> Si lo ves copiado en otro lado, esa copia está desactualizada: esta es la que manda.

> Nota de contexto: BankIn ya tiene listo el endpoint de cobro y hoy lo usa
> como método de pago real. Esta hoja es la guía para que naveSpace (la
> Tienda de Entradas) lo llame al confirmar una compra, en vez de solo
> simular el pago.

## Qué hace falta llamar

```
POST {BANKIN_API_BASE}/transactions/purchase
Content-Type: application/json
X-Api-Key: {BANKIN_API_KEY}      (solo si BankIn tiene EXTERNAL_API_KEY configurada)

{
  "card_id": "1234567890123456",
  "amount": 49.90,
  "currency": "COP",
  "note": "naveSpace Tickets"
}
```

- `currency` es la moneda en la que viene el cobro. Si se omite, se asume
  la moneda de la tarjeta. **Si difiere de la moneda de la tarjeta**,
  BankIn convierte con la tasa vigente (`GET /exchange-rates`) y descuenta
  el monto convertido; la respuesta trae el detalle:
  `amount` (cargo real en moneda de la tarjeta), `currency`,
  `charge_amount` / `charge_currency` (lo pedido) y `rate_used` (tasa
  aplicada, congelada para que la reversa devuelva el monto exacto).

- **Local:** `BANKIN_API_BASE = http://localhost:8000`
- **Producción:** `BANKIN_API_BASE = https://bankinback.onrender.com`
- `note` identifica el origen del cargo en el panel de gerente de BankIn — mandar siempre `"naveSpace Tickets"` (o `"naveSpace Admin"` si algún día cobra desde el panel admin) para poder auditar qué vino de dónde.

### Respuesta (201)

```json
{
  "id": 42,
  "card_id": "1234567890123456",
  "type": "PURCHASE",
  "amount": 49.90,
  "currency": "COP",
  "charge_amount": 49.90,
  "charge_currency": "COP",
  "rate_used": null,
  "status": "COMPLETED",
  "note": "naveSpace Tickets",
  "created_at": "...",
  "updated_at": "..."
}
```

### Tasas de cambio (multimoneda)

Cada tarjeta opera en una sola moneda (`COP`, `USD`, `EUR`). Tabla vigente
y conversión, públicas (sin `manager_id`):

```
GET {BANKIN_API_BASE}/exchange-rates
GET {BANKIN_API_BASE}/exchange-rates/history?base_currency=USD&target_currency=COP
GET {BANKIN_API_BASE}/exchange-rates/convert?amount=10&base_currency=USD&target_currency=COP
```

Solo el gerente carga tasas (`?manager_id=`); cada carga crea una fila
nueva (histórico, nunca se edita):

```
POST {BANKIN_API_BASE}/exchange-rates?manager_id=1
{"base_currency": "USD", "target_currency": "COP", "rate": 4100}
```

### Errores a manejar

| Código | Cuándo | Qué hacer en naveSpace |
|--------|--------|--------------------------|
| `404`  | `card_id` no existe en BankIn | Mostrar "tarjeta no encontrada", no confirmar la entrada |
| `400`  | tarjeta no activa, saldo insuficiente o monto inválido | Mostrar el `detail` del error, liberar la reserva de la entrada |
| `401`  | falta o no coincide `X-Api-Key` | Error de configuración (no mostrar al comprador) — revisar `BANKIN_API_KEY` en naveSpace |

## Flujo recomendado

1. El comprador llega al checkout de naveSpace y **pone su número de tarjeta BankIn** (hoy ese campo no existe en el formulario — es lo primero que hay que agregar).
2. naveSpace reserva la entrada/función (como ya hace hoy).
3. naveSpace llama a `POST /transactions/purchase` con el `card_id` ingresado y el monto de la entrada.
4. Si responde `201`, confirma la entrada y guarda el `id` de la transacción de BankIn junto a la venta (para poder correlacionar/anular si hace falta).
5. Si responde `404`/`400`, libera la reserva y muestra el error al comprador. **No confirmar nunca una entrada si el cobro no devolvió 201.**

## Cancelar una venta ya cobrada

Si naveSpace cancela una entrada que ya se había cobrado (el comprador la
cancela, o falla algo después del cobro), puede reversar ese cargo
directamente, sin depender de que alguien lo haga desde el panel de
gerente de BankIn:

```
POST {BANKIN_API_BASE}/transactions/{id}/reverse
X-Api-Key: {BANKIN_API_KEY}      (solo si BankIn tiene EXTERNAL_API_KEY configurada)
```

- `{id}` es el `id` de la transacción que devolvió `/purchase` en su
  momento (por eso conviene guardarlo junto a la venta, ver paso 4 más
  arriba).
- No lleva body.
- Responde `200` con la transacción en estado `ANNULLED` y el dinero ya
  devuelto al balance de la tarjeta.
- `404` si ese id de transacción no existe, `400` si ya estaba anulada,
  `401` si falta/no coincide `X-Api-Key`.

Regla de negocio a tener en cuenta: esto reversa **por id de transacción**,
no por tarjeta ni por monto -- así que solo puede reversar exactamente el
cargo que generó esa compra, no "el último cobro de esa tarjeta".

## Configuración necesaria en naveSpace

- `BANKIN_API_BASE` — URL del backend de BankIn (local o Render).
- `BANKIN_API_KEY` — mismo valor que `EXTERNAL_API_KEY` en el backend de BankIn (solo hace falta si esa variable está configurada ahí; si no, se puede omitir). Se usa tanto para `/purchase` como para `/transactions/{id}/reverse` y para `/payment-orders/*`.

## Órdenes multitramo (precio base en EUR)

La entrada solo se confirma cuando la orden llega a `PAID`. Cada tramo se
convierte a EUR con la tasa vigente y queda congelado (`rate_to_eur`).

```
POST {BANKIN_API_BASE}/payment-orders
{"reference": "MUS-AB12CD34", "total_eur": 50.0, "note": "naveSpace Tickets"}
→ 201 {id, reference, total_eur, paid_eur: 0, remaining_eur: 50, status: PENDING}

POST {BANKIN_API_BASE}/payment-orders/{id}/pay
{"card_id": "1234", "amount": 20, "currency": "EUR",
 "idempotency_key": "intento-1", "note": "naveSpace Tickets"}
→ 200 {paid_eur: 20, remaining_eur: 30, status: PARTIAL, tranches: [...]}

POST {BANKIN_API_BASE}/payment-orders/{id}/pay
{"card_id": "5678", "amount": 20, "currency": "USD"}   # se convierte a EUR
→ 200 {paid_eur: 38, remaining_eur: 12, status: PARTIAL}

POST {BANKIN_API_BASE}/payment-orders/{id}/cancel   # reversa TODOS los tramos BankIn,
                                                    # incluso si la orden ya está PAID (= devolución total)
```

- Un tramo que supere el restante falla con `400` (sobrepago). Reintentos con
  la misma `idempotency_key` devuelven el tramo sin recobrar.
- Adyen (en proceso, aún sin cobro real): `POST /payment-orders/{id}/adyen-intents`
  registra la intención (no suma a `paid_eur`) y
  `POST /payment-orders/adyen-tranches/{tranche_id}/confirm` la confirma
  (stub del webhook; suma a `paid_eur`).

## Fuera de alcance por ahora

- BankIn no valida un CVV/expiración real: solo verifica que la tarjeta exista, esté activa y tenga saldo. No es un flujo de pago real, es el demo.
- No hay idempotencia: si naveSpace reintenta la misma compra por un timeout, puede generar un doble cobro. Si se reintenta, primero conviene revisar `GET /transactions/card/{card_id}` para confirmar si ya se registró.
