"""Casos de uso de Tasas de cambio.

El gerente carga tasas por par dirigido (base -> target): cuántas unidades
de `target` vale 1 unidad de `base`. Cada carga crea una fila nueva
(histórico inmutable); la vigente es la más reciente.

Si un cobro necesita el par inverso al cargado (ej. hay USD->COP pero se
pide COP->USD), se resuelve por inversión (1/rate) y se informa con
`inverted=True`, para no obligar al gerente a cargar los 6 pares a mano.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import Currency, ExchangeRate
from app.domain.ports import ExchangeRateRepository


class InvalidRateError(Exception):
    """La tasa debe ser mayor que cero / el par debe ser válido."""


class ExchangeRateNotFoundError(Exception):
    """No hay tasa vigente para ese par (ni directa ni inversa)."""


@dataclass
class ResolvedRate:
    rate: float
    """Unidades de moneda-tarjeta por 1 unidad de moneda-cobro."""
    inverted: bool = False
    source: ExchangeRate | None = None
    """Fila de la que salió (la inversa, si `inverted`)."""


class ExchangeRateService:
    def __init__(self, rate_repository: ExchangeRateRepository) -> None:
        self._rates = rate_repository

    def create_rate(
        self, base: Currency, target: Currency, rate: float, created_by: int | None = None
    ) -> ExchangeRate:
        if base == target:
            raise InvalidRateError(
                f"La tasa debe ser entre monedas distintas (recibí {base.value}->{target.value})"
            )
        if rate <= 0:
            raise InvalidRateError("La tasa debe ser mayor que cero")
        return self._rates.save(
            ExchangeRate(base_currency=base, target_currency=target, rate=rate, created_by=created_by)
        )

    def get_rate(self, base: Currency, target: Currency) -> ResolvedRate:
        """Tasa vigente base->target. Igual moneda = 1.0 sin fila."""
        if base == target:
            return ResolvedRate(rate=1.0)
        direct = self._rates.find_latest(base, target)
        if direct is not None:
            return ResolvedRate(rate=direct.rate, source=direct)
        inverse = self._rates.find_latest(target, base)
        if inverse is not None and inverse.rate > 0:
            return ResolvedRate(rate=1.0 / inverse.rate, inverted=True, source=inverse)
        raise ExchangeRateNotFoundError(
            f"No hay tasa vigente para {base.value}->{target.value} "
            f"(ni su inversa {target.value}->{base.value}); el gerente debe cargarla"
        )

    def convert(self, amount: float, base: Currency, target: Currency) -> tuple[float, ResolvedRate]:
        """Convierte `amount` de `base` a `target`. Devuelve (monto, tasa usada)."""
        resolved = self.get_rate(base, target)
        return amount * resolved.rate, resolved

    def current_table(self) -> list[ExchangeRate]:
        return self._rates.find_all_latest()

    def history(
        self, base: Currency | None = None, target: Currency | None = None, limit: int = 100
    ) -> list[ExchangeRate]:
        return self._rates.find_history(base, target, limit)
