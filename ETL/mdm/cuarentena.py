"""
cuarentena.py
=============
Helpers Python para escribir items en MDM.Cuarentena_* y para consultar el
flag global `MDM_MODO_ESTRICTO`.

Política de inserción: UPSERT por dominio.
- Si la clave ya existe en estado PENDIENTE → incrementa `Veces_Visto` y
  actualiza `Fecha_Ultima_Vez`.
- Si no existe → INSERT.
- Si ya está APROBADA/FUSIONADA/RECHAZADA → no se vuelve a abrir.

Las tablas son creadas por `sql_migrations/fase40_cuarentena_estricta_dims.sql`.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

_log = logging.getLogger("ETL_Pipeline")


_modo_estricto_cache: bool | None = None


def es_modo_estricto(engine: Engine) -> bool:
    """
    Devuelve True si Config.Parametros_Pipeline.MDM_MODO_ESTRICTO = 'ON'.
    Cacheado por proceso para evitar query por cada fila.
    Llamar `resetear_cache_modo_estricto()` después de cambiar el flag.
    """
    global _modo_estricto_cache
    if _modo_estricto_cache is not None:
        return _modo_estricto_cache
    try:
        with engine.connect() as conn:
            val = conn.execute(text("""
                SELECT Valor FROM Config.Parametros_Pipeline
                WHERE Nombre_Parametro = 'MDM_MODO_ESTRICTO'
            """)).scalar()
        _modo_estricto_cache = (str(val or 'OFF').strip().upper() == 'ON')
    except Exception as err:
        # Si la tabla no existe o falla, asumimos OFF (legacy).
        _log.warning(f'es_modo_estricto: fallback OFF por error: {err}')
        _modo_estricto_cache = False
    return _modo_estricto_cache


def resetear_cache_modo_estricto() -> None:
    """Forzar relectura del flag en próxima invocación."""
    global _modo_estricto_cache
    _modo_estricto_cache = None


# ---------------------------------------------------------------------------
# Helpers de UPSERT por dominio
# ---------------------------------------------------------------------------
def _to_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ('none', 'nan', 'null', '<na>') else None


def registrar_cuarentena_geografia(
    engine: Engine,
    *,
    fundo: Any = None, sector: Any = None, modulo: Any = None,
    turno: Any = None, valvula: Any = None, cama: Any = None,
    origen_tabla: str = '(desconocido)',
    origen_archivo: str | None = None,
) -> int:
    """
    Inserta o incrementa contador en MDM.Cuarentena_Geografia.
    Devuelve el ID_Cuarentena_Geo afectado.
    """
    params = {
        'F': _to_str(fundo), 'S': _to_str(sector), 'M': _to_str(modulo),
        'T': _to_str(turno), 'V': _to_str(valvula), 'C': _to_str(cama),
        'tabla': origen_tabla, 'arch': origen_archivo,
    }
    with engine.begin() as conn:
        # UPSERT manual: intentar UPDATE, si no afecta filas -> INSERT.
        upd = conn.execute(text("""
            UPDATE MDM.Cuarentena_Geografia
            SET Veces_Visto = Veces_Visto + 1,
                Fecha_Ultima_Vez = GETDATE()
            OUTPUT inserted.ID_Cuarentena_Geo
            WHERE Estado = 'PENDIENTE'
              AND ISNULL(Fundo,  '') = ISNULL(:F, '')
              AND ISNULL(Sector, '') = ISNULL(:S, '')
              AND ISNULL(Modulo, '') = ISNULL(:M, '')
              AND ISNULL(Turno,  '') = ISNULL(:T, '')
              AND ISNULL(Valvula,'') = ISNULL(:V, '')
              AND ISNULL(Cama,   '') = ISNULL(:C, '')
        """), params).scalar()
        if upd is not None:
            return int(upd)
        ins = conn.execute(text("""
            INSERT INTO MDM.Cuarentena_Geografia (
                Fundo, Sector, Modulo, Turno, Valvula, Cama,
                Origen_Tabla, Origen_Archivo
            )
            OUTPUT INSERTED.ID_Cuarentena_Geo
            VALUES (:F, :S, :M, :T, :V, :C, :tabla, :arch)
        """), params).scalar()
        return int(ins)


def registrar_cuarentena_variedad(
    engine: Engine,
    *,
    nombre_recibido: str,
    nombre_normalizado: str | None = None,
    origen_tabla: str = '(desconocido)',
    origen_archivo: str | None = None,
    score_levenshtein: float | None = None,
    id_variedad_sugerido: int | None = None,
) -> int:
    params = {
        'rec': nombre_recibido, 'norm': nombre_normalizado or nombre_recibido,
        'tabla': origen_tabla, 'arch': origen_archivo,
        'score': score_levenshtein, 'sug': id_variedad_sugerido,
    }
    with engine.begin() as conn:
        upd = conn.execute(text("""
            UPDATE MDM.Cuarentena_Variedad
            SET Veces_Visto = Veces_Visto + 1,
                Fecha_Ultima_Vez = GETDATE()
            OUTPUT inserted.ID_Cuarentena_Var
            WHERE Estado = 'PENDIENTE' AND Nombre_Normalizado = :norm
        """), params).scalar()
        if upd is not None:
            return int(upd)
        ins = conn.execute(text("""
            INSERT INTO MDM.Cuarentena_Variedad (
                Nombre_Recibido, Nombre_Normalizado,
                Origen_Tabla, Origen_Archivo,
                Score_Levenshtein, ID_Variedad_Sugerido
            )
            OUTPUT INSERTED.ID_Cuarentena_Var
            VALUES (:rec, :norm, :tabla, :arch, :score, :sug)
        """), params).scalar()
        return int(ins)


def registrar_cuarentena_personal(
    engine: Engine,
    *,
    dni: str,
    nombre: str | None = None,
    rol: str | None = None,
    origen_tabla: str = '(desconocido)',
    origen_archivo: str | None = None,
) -> int:
    params = {
        'dni': dni, 'nombre': nombre, 'rol': rol,
        'tabla': origen_tabla, 'arch': origen_archivo,
    }
    with engine.begin() as conn:
        upd = conn.execute(text("""
            UPDATE MDM.Cuarentena_Personal
            SET Veces_Visto = Veces_Visto + 1,
                Fecha_Ultima_Vez = GETDATE()
            OUTPUT inserted.ID_Cuarentena_Per
            WHERE Estado = 'PENDIENTE' AND DNI_Recibido = :dni
        """), params).scalar()
        if upd is not None:
            return int(upd)
        ins = conn.execute(text("""
            INSERT INTO MDM.Cuarentena_Personal (
                DNI_Recibido, Nombre_Recibido, Rol_Recibido,
                Origen_Tabla, Origen_Archivo
            )
            OUTPUT INSERTED.ID_Cuarentena_Per
            VALUES (:dni, :nombre, :rol, :tabla, :arch)
        """), params).scalar()
        return int(ins)


__all__ = [
    'es_modo_estricto',
    'resetear_cache_modo_estricto',
    'registrar_cuarentena_geografia',
    'registrar_cuarentena_variedad',
    'registrar_cuarentena_personal',
]
