"""
comun/sql_utils.py
==================
Helpers de mapeo y ejecucion de queries SQLAlchemy.

Concentra los patrones que se repetian ~47 veces en backend/repositorios/
y ~5 veces en ETL (pipeline, mdm, auditoria, parametros).
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy import text
from sqlalchemy.engine import Engine, Row

from comun.conexion import obtener_engine


def mapear_fila(fila: Row | None) -> dict | None:
    """Convierte una Row de SQLAlchemy a dict, o None si no hay fila."""
    return dict(fila._mapping) if fila is not None else None


def mapear_filas(filas) -> list[dict]:
    """Convierte un iterable de Rows a lista de dicts."""
    return [dict(f._mapping) for f in filas]


def ejecutar_query(
    sql: str,
    params: Mapping[str, Any] | None = None,
    *,
    engine: Engine | None = None,
) -> list[dict]:
    """SELECT y devuelve lista de dicts. Usa engine.connect() (no transaccion)."""
    eng = engine or obtener_engine()
    with eng.connect() as con:
        filas = con.execute(text(sql), params or {}).fetchall()
        return mapear_filas(filas)


def ejecutar_query_unica(
    sql: str,
    params: Mapping[str, Any] | None = None,
    *,
    engine: Engine | None = None,
) -> dict | None:
    """SELECT que devuelve solo la primera fila como dict, o None."""
    eng = engine or obtener_engine()
    with eng.connect() as con:
        fila = con.execute(text(sql), params or {}).fetchone()
        return mapear_fila(fila)


def ejecutar_comando(
    sql: str,
    params: Mapping[str, Any] | None = None,
    *,
    engine: Engine | None = None,
) -> int:
    """INSERT/UPDATE/DELETE/EXEC. Usa engine.begin() (transaccion). Retorna rowcount."""
    eng = engine or obtener_engine()
    with eng.begin() as con:
        return con.execute(text(sql), params or {}).rowcount
