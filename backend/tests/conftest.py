"""
backend/tests/conftest.py
=========================
Fixtures globales de pytest para el backend.

Conexión: reusa `obtener_engine()` del módulo principal — no hay DB
efímera, los tests leen contra la BD de dev. Por eso TODOS los tests
deben ser de SOLO LECTURA o usar `db_rollback` para envolver mutaciones
en una transacción que se revierte al final.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Permitir importar `repositorios`, `servicios`, `api` sin instalar el
# backend como paquete. Mismo truco que `scripts/medir_catalogos.py`.
_DIR_BACKEND = Path(__file__).resolve().parents[1]
if str(_DIR_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DIR_BACKEND))

from nucleo.conexion import obtener_engine  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """Engine compartido por toda la suite — evita reconectar por test."""
    return obtener_engine()


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
