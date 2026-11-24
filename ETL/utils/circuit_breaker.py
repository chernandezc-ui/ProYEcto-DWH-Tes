"""
circuit_breaker.py
==================
Lógica centralizada del circuit breaker de calidad para los Facts.

Los umbrales NO viven en el código: se leen de Config.Parametros_Pipeline
(ver config/reglas.py):

  BREAKER_WARNING_PCT / BREAKER_ERROR_PCT / BREAKER_CRITICO_PCT / BREAKER_MIN_MUESTRA
      valor global, requerido.
  BREAKER_ERROR_PCT.<Fact>  (ej. BREAKER_ERROR_PCT.Fact_Censo_Plantas)
      override opcional por fact; gana sobre el global.

BaseFactProcessor.finalizar_proceso delega en evaluar().
La evaluación es pura. El orquestador incremental lanza después del commit;
la reconstrucción atómica decide el rollback antes del commit externo.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config import reglas
from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError

NivelBloqueo = Literal['CRITICO', 'ERROR', 'WARNING', None]

PARAMETROS_BREAKER = {
    'warning': 'BREAKER_WARNING_PCT',
    'error': 'BREAKER_ERROR_PCT',
    'critico': 'BREAKER_CRITICO_PCT',
    'min_muestra': 'BREAKER_MIN_MUESTRA',
}


@dataclass(frozen=True)
class UmbralesCircuitBreaker:
    """Configuración inmutable de un circuit breaker (todos los campos obligatorios)."""
    warning: float
    error: float
    critico: float
    min_muestra: int

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


def resolver_umbrales(nombre_fact: str | None = None) -> UmbralesCircuitBreaker:
    """
    Umbrales vigentes para una fact, leídos de Config.Parametros_Pipeline.

    El valor global de cada parámetro es requerido (ErrorConfiguracion si falta);
    el parámetro '<NOMBRE>.<Fact>' es opcional y, si existe, gana.
    """
    valores = {}
    for campo, clave in PARAMETROS_BREAKER.items():
        convertir_int = campo == 'min_muestra'
        valor = reglas.parametro_int(clave) if convertir_int else reglas.parametro_float(clave)
        if nombre_fact:
            especifico = f'{clave}.{nombre_fact}'
            if reglas.parametro_opcional(especifico) is not None:
                valor = reglas.parametro_int(especifico) if convertir_int else reglas.parametro_float(especifico)
        valores[campo] = valor
    try:
        return UmbralesCircuitBreaker(**valores)
    except ValueError as error:
        destino = f' para {nombre_fact}' if nombre_fact else ''
        raise reglas.ErrorConfiguracion(f'Umbrales del breaker invalidos{destino}: {error}') from error


def evaluar(
    total_leidos: int,
    rechazados: int,
    *,
    umbrales: UmbralesCircuitBreaker,
    tabla: str = '(sin nombre)',
) -> ResultadoCircuitBreaker:
    """
    Evalúa el porcentaje de rechazo contra los umbrales. NO lanza excepciones —
    devuelve el resultado para que el caller decida (logging + raise).

    Si la muestra es menor a `min_muestra`, no aplica el breaker (devuelve nivel=None).
    """
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
    'PARAMETROS_BREAKER',
    'resolver_umbrales',
    'evaluar',
    'lanzar_si_bloqueado',
]
