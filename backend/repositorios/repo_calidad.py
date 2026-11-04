"""
repositorios/repo_calidad.py
============================
Consultas para observabilidad de calidad de datos (Bronce.Seguimiento_Errores).
"""

from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from nucleo.conexion import obtener_engine
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

def obtener_resumen_calidad_hoy() -> dict:
    """
    Obtiene métricas de errores detectados el día de hoy.
    """
    hoy = date.today()
    try:
        with obtener_engine().connect() as con:
            # 1. Total errores hoy
            total_hoy = con.execute(
                text("SELECT COUNT(*) FROM Bronce.Seguimiento_Errores WHERE CAST(Fecha_Sistema AS DATE) = :hoy"),
                {"hoy": hoy}
            ).scalar() or 0

            # 2. Top 3 Tipos de Error
            top_errores = con.execute(
                text("""
                    SELECT TOP 3 Tipo_Error_Raw, COUNT(*) as Cuenta
                    FROM Bronce.Seguimiento_Errores
                    WHERE CAST(Fecha_Sistema AS DATE) = :hoy
                    GROUP BY Tipo_Error_Raw
                    ORDER BY Cuenta DESC
                """),
                {"hoy": hoy}
            ).fetchall()

            # 3. Top 3 Fundos con errores
            top_fundos = con.execute(
                text("""
                    SELECT TOP 3 Fundo_Raw, COUNT(*) as Cuenta
                    FROM Bronce.Seguimiento_Errores
                    WHERE CAST(Fecha_Sistema AS DATE) = :hoy
                    GROUP BY Fundo_Raw
                    ORDER BY Cuenta DESC
                """),
                {"hoy": hoy}
            ).fetchall()

            # 4. Tendencia (Errores última hora vs anterior) - Opcional para SSE
            
            return {
                "total_hoy": total_hoy,
                "top_tipos": [dict(f._mapping) for f in top_errores],
                "top_fundos": [dict(f._mapping) for f in top_fundos],
                "timestamp_servidor": datetime.now().isoformat()
            }
    except SQLAlchemyError:
        log.exception("Error al obtener resumen de calidad")
        return {
            "total_hoy": 0,
            "top_tipos": [],
            "top_fundos": [],
            "timestamp_servidor": datetime.now().isoformat(),
            "error": "Error de base de datos"
        }
