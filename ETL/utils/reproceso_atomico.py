"""Reconstrucción por fact: borrado, Bronce y carga comparten un commit."""
from contextlib import contextmanager

from sqlalchemy.engine import Engine

from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError


class EngineTransaccional(Engine):
    """Vista del engine que presta una conexión sin cerrarla ni hacer commits.

    Compatible con los procesadores existentes que usan `with engine.connect()`
    y `with engine.begin()`. La transacción pertenece exclusivamente al llamador.
    No debe almacenarse ni compartirse entre hilos.
    """

    def __init__(self, engine, conexion):
        super().__init__(engine.pool, engine.dialect, engine.url)
        self._conexion = conexion

    @contextmanager
    def connect(self):
        yield self._conexion

    @contextmanager
    def begin(self):
        yield self._conexion


def reconstruir_fact_atomica(engine, preparar, cargar):
    with engine.begin() as conexion:
        prestado = EngineTransaccional(engine, conexion)
        preparacion = preparar(prestado)
        resultado = cargar(prestado)
        nivel = resultado.get('breaker_nivel')
        if nivel in ('ERROR', 'CRITICO'):
            clase = ErrorCircuitBreakerCritico if nivel == 'CRITICO' else ErrorCircuitBreakerError
            raise clase(resultado.get('breaker_mensaje') or f'Reproceso bloqueado: {nivel}')
        if resultado.get('posible_perdida_silenciosa'):
            raise RuntimeError('Reproceso con posible perdida silenciosa; se conserva la fact anterior.')
        if preparacion['filas_destino_eliminadas'] and not resultado.get('insertados', 0):
            raise RuntimeError('Reconstruccion vacia; se conserva la fact anterior.')
    return preparacion, resultado
