"""
config/conexion.py
==================
Módulo de conexión del ETL que delega en comun/conexion.py.
Mantiene las firmas del ETL para compatibilidad.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from sqlalchemy import text

# Asegurar que el directorio raíz del proyecto está en sys.path para importar comun
_DIR_CONFIG = Path(__file__).resolve().parent
_DIR_PROYECTO = _DIR_CONFIG.parent.parent
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import (
    obtener_engine,
    resetear_engine,
)
from comun.conexion import verificar_conexion as _verificar_conexion_dict

def verificar_conexion() -> bool:
    """
    Ping de conexión adaptado para el ETL (espera retorno booleano).
    """
    info = _verificar_conexion_dict()
    if info.get("conectado"):
        print(f"  [OK] Conectado a: {info.get('base_datos')}")
        return True
    print(f"  [ERROR] Conexion: {info.get('error', 'desconocido')}")
    return False

def limpiar_sesiones_huerfanas(
    minutos_inactivo: int = 5,
    nombre_aplicacion: str = 'ACP_ETL_Pipeline',
) -> list[int]:
    """
    Mata sesiones durmientes en SQL Server del pipeline anterior que no cerraron correctamente.
    """
    engine = obtener_engine()
    matados: list[int] = []
    try:
        with engine.connect() as conexion:
            filas = conexion.execute(text("""
                SELECT s.session_id
                FROM sys.dm_exec_sessions s
                JOIN sys.dm_tran_session_transactions t
                  ON t.session_id = s.session_id
                WHERE s.program_name = :app
                  AND s.session_id <> @@SPID
                  AND s.status = 'sleeping'
                  AND t.is_user_transaction = 1
                  AND DATEDIFF(MINUTE, s.last_request_end_time, GETDATE()) >= :min
            """), {'app': nombre_aplicacion, 'min': minutos_inactivo}).fetchall()

            for (spid,) in filas:
                try:
                    conexion.execute(text(f'KILL {int(spid)};'))
                    matados.append(int(spid))
                except Exception as err_kill:
                    print(f'  WARN: no se pudo matar sesion {spid}: {err_kill}')

        if matados:
            print(f'  Liberadas {len(matados)} sesiones huerfanas: {matados}')
    except Exception as err:
        print(f'  WARN: limpiar_sesiones_huerfanas omitido: {err}')

    return matados

__all__ = ["obtener_engine", "resetear_engine", "verificar_conexion", "limpiar_sesiones_huerfanas"]
