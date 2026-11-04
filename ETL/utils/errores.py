"""
utils/errores.py
================
Excepciones propias del pipeline ETL.
Centraliza los tipos de error para evitar imports circulares.
"""


class ErrorCircuitBreakerCritico(RuntimeError):
    """
    Lanzada por BaseFactProcessor cuando el rechazo real supera LIMITE_CRITICO.
    Al propagarse fuera de _ejecutar_fact el orquestador aborta el pipeline completo.
    """


class ErrorCircuitBreakerError(RuntimeError):
    """
    Lanzada por BaseFactProcessor cuando el rechazo real supera LIMITE_ERROR.
    Aborta el fact actual; el orquestador bloquea Gold pero puede continuar
    con los facts restantes.
    """
