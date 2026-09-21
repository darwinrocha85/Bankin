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
  "note": "naveSpace Tickets"
}
```

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
  "status": "COMPLETED",
  "note": "naveSpace Tickets",
  "created_at": "...",
  "updated_at": "..."
}
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
- `BANKIN_API_KEY` — mismo valor que `EXTERNAL_API_KEY` en el backend de BankIn (solo hace falta si esa variable está configurada ahí; si no, se puede omitir). Se usa tanto para `/purchase` como para `/transactions/{id}/reverse`.

## Fuera de alcance por ahora

- BankIn no valida un CVV/expiración real: solo verifica que la tarjeta exista, esté activa y tenga saldo. No es un flujo de pago real, es el demo.
- No hay idempotencia: si naveSpace reintenta la misma compra por un timeout, puede generar un doble cobro. Si se reintenta, primero conviene revisar `GET /transactions/card/{card_id}` para confirmar si ya se registró.
