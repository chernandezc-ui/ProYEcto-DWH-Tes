"""
repositorios/repo_config.py
============================
Consultas de solo lectura sobre Config.Reglas_Validacion y Config.Parametros_Pipeline.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


def listar_reglas(pagina: int = 1, tamano: int = 20) -> dict:
    offset = (pagina - 1) * tamano
    try:
        with obtener_engine().connect() as con:
            total = con.execute(text("SELECT COUNT(*) FROM Config.Reglas_Validacion")).scalar() or 0
            filas = con.execute(text("""
                SELECT
                    Tabla_Destino   AS tabla_destino,
                    Columna         AS columna,
                    Tipo_Validacion AS tipo_validacion,
                    Valor_Min       AS valor_min,
                    Valor_Max       AS valor_max,
                    Accion          AS accion,
                    Activo          AS activo
                FROM Config.Reglas_Validacion
                ORDER BY Tabla_Destino, Columna
                OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
            """), {"offset": offset, "tamano": tamano}).fetchall()
            # KPIs rápidos
            kpis_raw = con.execute(text("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN Activo = 1 THEN 1 ELSE 0 END) AS activas
                FROM Config.Reglas_Validacion
            """)).fetchone()

            total_kpis = kpis_raw.total or 0
            activas = kpis_raw.activas or 0

        return {
            "total": total,
            "pagina": pagina,
            "tamano": tamano,
            "kpis": {
                "total": total_kpis,
                "activas": activas,
                "inactivas": total_kpis - activas
            },
            "datos": [dict(f._mapping) for f in filas],
        }
    except SQLAlchemyError:
        log.exception("Error al listar reglas de validación")
        raise ErrorBaseDatos()


def listar_parametros(pagina: int = 1, tamano: int = 20) -> dict:
    offset = (pagina - 1) * tamano
    try:
        with obtener_engine().connect() as con:
            total = con.execute(text("SELECT COUNT(*) FROM Config.Parametros_Pipeline")).scalar() or 0
            filas = con.execute(text("""
                SELECT
                    Nombre_Parametro AS nombre_parametro,
                    Valor            AS valor,
                    Descripcion      AS descripcion,
                    CONVERT(varchar, Fecha_Modificacion, 120) AS fecha_modificacion
                FROM Config.Parametros_Pipeline
                ORDER BY Nombre_Parametro
                OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
            """), {"offset": offset, "tamano": tamano}).fetchall()
        return {
            "total": total, "pagina": pagina, "tamano": tamano,
            "datos": [dict(f._mapping) for f in filas],
        }
    except SQLAlchemyError:
        log.exception("Error al listar parámetros del pipeline")
        raise ErrorBaseDatos()
def actualizar_parametro(nombre: str, valor: str, modificado_por: str) -> bool:
    try:
        with obtener_engine().begin() as con:
            rows = con.execute(text("""
                UPDATE Config.Parametros_Pipeline
                SET Valor = :valor,
                    Fecha_Modificacion = GETDATE(),
                    Modificado_Por = :usuario
                WHERE Nombre_Parametro = :nombre
            """), {
                "valor": valor,
                "usuario": modificado_por,
                "nombre": nombre
            }).rowcount
            return rows > 0
    except SQLAlchemyError:
        log.exception("Error al actualizar parámetro", extra={"nombre": nombre})
        raise ErrorBaseDatos()
