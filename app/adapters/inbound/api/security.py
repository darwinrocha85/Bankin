"""Protección simple para endpoints pensados para ser llamados desde OTRAS
apps (no solo desde este frontend) -- por ejemplo POST /transactions/purchase,
el endpoint de "cobro" (dada una tarjeta y un monto, genera un cargo).

Si la variable de entorno EXTERNAL_API_KEY no está configurada, no se exige
ningún header -- así el demo sigue funcionando local sin configurar nada
extra. En cuanto defines EXTERNAL_API_KEY (en tu .env local o en las
variables de entorno de Render), el endpoint protegido empieza a exigir el
header `X-Api-Key` con ese mismo valor.

Nota para producción real: esta clave viaja igual en el bundle del frontend
(ver src/api.ts), así que cualquiera que abra las devtools del navegador
puede verla -- no es un mecanismo de seguridad real para un cliente web
público, solo una barrera simple contra quien no conozca la URL/clave (por
ejemplo, para llamadas servidor-a-servidor desde otra app). Para un banco de
verdad hace falta autenticación de usuario + autorización por token, no esto.
"""
from __future__ import annotations

import os

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("EXTERNAL_API_KEY", "").strip()
    if not expected:
        # No configurada: no se exige (modo demo/local sin fricción).
        return
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="X-Api-Key inválida o ausente")
