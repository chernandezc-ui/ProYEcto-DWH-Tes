"""
utils/errores.py
================
Excepciones propias del pipeline ETL.
Centraliza los tipos de error para evitar imports circulares.
"""


class ErrorCircuitBreakerCritico(RuntimeError):
    """
    Lanzada por el orquestador o reconstructor cuando el resultado es CRITICO.
    Al propagarse fuera de _ejecutar_fact el orquestador aborta el pipeline completo.
    """


class ErrorCircuitBreakerError(RuntimeError):
    """
    Lanzada por el orquestador o reconstructor cuando el resultado es ERROR.
    Aborta el fact actual; el orquestador bloquea Gold pero puede continuar
    con los facts restantes.
    """
