"""
backend/tests/conftest.py
=========================
Fixtures globales de pytest para el backend.

Conexión: usa la instancia aislada validada por el conftest raíz.
Las pruebas SQL requieren --run-sqlserver y un destino explícito.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def engine(sqlserver_engine):
    """Engine del destino de prueba validado, nunca la BD de desarrollo."""
    if sqlserver_engine is None:
        pytest.skip("La fixture engine requiere integración SQL Server habilitada")
    return sqlserver_engine


@pytest.fixture
def db_rollback(engine):
    """
    Conexión envuelta en transacción que se revierte al cerrar.

    Uso en tests que insertan/actualizan:

        def test_algo(db_rollback):
            db_rollback.execute(text("INSERT ..."))
            # automáticamente rollback al final del test

    Para tests de SOLO LECTURA no es necesario — usar `engine.connect()`
    directo es más liviano.
    """
    conexion = engine.connect()
    trans = conexion.begin()
    try:
        yield conexion
    finally:
        trans.rollback()
        conexion.close()
