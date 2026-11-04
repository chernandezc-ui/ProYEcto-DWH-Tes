"""
circuit_breaker.py
==================
Lógica centralizada del circuit breaker de calidad para los Facts.

Antes: thresholds (`LIMITE_WARNING`, `LIMITE_ERROR`, `LIMITE_CRITICO`) duplicados
en cada subclase de BaseFactProcessor + lógica de evaluación duplicada en
_base_processor.py. Refactor: thresholds en `UMBRALES_*` (por dominio) +
función pura `evaluar()` con contrato único.

Mantiene retro-compatibilidad: las subclases que sobrescriben `LIMITE_*`
siguen funcionando porque `BaseFactProcessor.evaluar_circuit_breaker()` usa
los atributos de instancia.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError


# ── Defaults globales (idénticos a los antiguos en BaseFactProcessor) ────
UMBRAL_WARNING_DEFAULT  = 1.0
UMBRAL_ERROR_DEFAULT    = 2.0
UMBRAL_CRITICO_DEFAULT  = 5.0
MIN_MUESTRA_BREAKER     = 50

NivelBloqueo = Literal['CRITICO', 'ERROR', 'WARNING', None]


@dataclass(frozen=True)
class UmbralesCircuitBreaker:
    """Configuración inmutable de un circuit breaker."""
    warning: float = UMBRAL_WARNING_DEFAULT
    error: float = UMBRAL_ERROR_DEFAULT
    critico: float = UMBRAL_CRITICO_DEFAULT
    min_muestra: int = MIN_MUESTRA_BREAKER

    def __post_init__(self):
        # Validación de coherencia: warning <= error <= critico
        if not (self.warning <= self.error <= self.critico):
            raise ValueError(
                f'Umbrales incoherentes: warning={self.warning}, '
                f'error={self.error}, critico={self.critico}. '
                'Requerido: warning <= error <= critico.'
            )
        if self.min_muestra < 1:
            raise ValueError(f'min_muestra invalido: {self.min_muestra}')


@dataclass(frozen=True)
class ResultadoCircuitBreaker:
    """Resultado de evaluar un circuit breaker."""
    nivel: NivelBloqueo
    porcentaje_rechazo: float
    total_leidos: int
    rechazados: int
    mensaje: str | None = None


def evaluar(
    total_leidos: int,
    rechazados: int,
    *,
    umbrales: UmbralesCircuitBreaker | None = None,
    tabla: str = '(sin nombre)',
) -> ResultadoCircuitBreaker:
    """
    Evalúa el porcentaje de rechazo contra los umbrales. NO lanza excepciones —
    devuelve el resultado para que el caller decida (logging + raise).

    Si la muestra es menor a `min_muestra`, no aplica el breaker (devuelve nivel=None).
    """
    umbrales = umbrales or UmbralesCircuitBreaker()
    porcentaje = (rechazados / total_leidos * 100) if total_leidos > 0 else 0.0

    if total_leidos < umbrales.min_muestra:
        return ResultadoCircuitBreaker(
            nivel=None, porcentaje_rechazo=porcentaje,
            total_leidos=total_leidos, rechazados=rechazados,
            mensaje=f'Muestra insuficiente ({total_leidos} < {umbrales.min_muestra}), breaker no aplica.',
        )

    if porcentaje >= umbrales.critico:
        return ResultadoCircuitBreaker(
            nivel='CRITICO', porcentaje_rechazo=porcentaje,
            total_leidos=total_leidos, rechazados=rechazados,
            mensaje=(
                f'Circuit breaker CRITICO en {tabla}: '
                f'{porcentaje:.1f}% de rechazo ({rechazados}/{total_leidos}). '
                f'Umbral critico: {umbrales.critico}%.'
            ),
        )
    if porcentaje >= umbrales.error:
        return ResultadoCircuitBreaker(
            nivel='ERROR', porcentaje_rechazo=porcentaje,
            total_leidos=total_leidos, rechazados=rechazados,
            mensaje=(
                f'Circuit breaker ERROR en {tabla}: '
                f'{porcentaje:.1f}% de rechazo ({rechazados}/{total_leidos}). '
                f'Umbral de error: {umbrales.error}%.'
            ),
        )
    if porcentaje >= umbrales.warning:
        return ResultadoCircuitBreaker(
            nivel='WARNING', porcentaje_rechazo=porcentaje,
            total_leidos=total_leidos, rechazados=rechazados,
            mensaje=(
                f'Circuit breaker WARNING en {tabla}: '
                f'{porcentaje:.1f}% de rechazo >= {umbrales.warning}% — '
                f'continua, pero revisar calidad.'
            ),
        )
    return ResultadoCircuitBreaker(
        nivel=None, porcentaje_rechazo=porcentaje,
        total_leidos=total_leidos, rechazados=rechazados,
    )


def lanzar_si_bloqueado(resultado: ResultadoCircuitBreaker) -> None:
    """Lanza la excepción apropiada si el nivel es CRITICO o ERROR."""
    if resultado.nivel == 'CRITICO':
        raise ErrorCircuitBreakerCritico(resultado.mensaje or 'Circuit breaker CRITICO')
    if resultado.nivel == 'ERROR':
        raise ErrorCircuitBreakerError(resultado.mensaje or 'Circuit breaker ERROR')


__all__ = [
    'UmbralesCircuitBreaker',
    'ResultadoCircuitBreaker',
    'evaluar',
    'lanzar_si_bloqueado',
    'UMBRAL_WARNING_DEFAULT',
    'UMBRAL_ERROR_DEFAULT',
    'UMBRAL_CRITICO_DEFAULT',
    'MIN_MUESTRA_BREAKER',
]
