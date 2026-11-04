"""
repositorios/repo_reinyeccion.py
=================================
Capa de datos para la Herramienta de Reinyección MDM.

Lógica:
  Para cada registro RESUELTO en MDM.Cuarentena que tenga un
  ID_Registro_Origen válido, localiza la fila correspondiente en la
  tabla Bronce y restablece su Estado_Carga → 'CARGADO'.

  Esto permite que el pipeline ETL procese de nuevo esos registros
  con las reglas MDM ya actualizadas, sin que el usuario tenga que
  re-subir archivos.

Contrato:
  - Retorna dicts simples o lanza ErrorBaseDatos.
  - Nunca expone SQLAlchemy al exterior.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

# Mapa canónico: nombre normalizado del origen lógico que aparece en
# MDM.Cuarentena.Tabla_Origen → lista de tablas Bronce físicas con su PK real.
# Cada origen puede mapear a una o varias tablas físicas (caso clima, cosecha y poda).
# Verificado contra INFORMATION_SCHEMA en LCP-PAG-PRACTIC el 2026-04-27.
_TABLAS_BRONCE: dict[str, list[dict[str, str]]] = {
    "bronce.peladas":                  [{"tabla": "Bronce.Peladas",                  "pk": "ID_Peladas"}],
    "bronce.tasa_crecimiento_brotes":  [{"tabla": "Bronce.Tasa_Crecimiento_Brotes",  "pk": "ID_Tasa_Crecimiento"}],
    "bronce.evaluacion_pesos":         [{"tabla": "Bronce.Evaluacion_Pesos",         "pk": "ID_Evaluacion_Pesos"}],
    "bronce.evaluacion_vegetativa":    [{"tabla": "Bronce.Evaluacion_Vegetativa",    "pk": "ID_Evaluacion_Vegetativa"}],
    "bronce.conteo_fruta":             [{"tabla": "Bronce.Conteo_Fruta",             "pk": "ID_Conteo_Fruta"}],
    "bronce.induccion_floral":         [{"tabla": "Bronce.Induccion_Floral",         "pk": "ID_Induccion_Floral"}],
    "bronce.fisiologia":               [{"tabla": "Bronce.Fisiologia",               "pk": "ID_Fisiologia"}],
    "bronce.tareo":                    [{"tabla": "Bronce.Consolidado_Tareos",       "pk": "ID_Tareo"}],
    "bronce.consolidado_tareos":       [{"tabla": "Bronce.Consolidado_Tareos",       "pk": "ID_Tareo"}],
    # Origen lógico clima → 2 tablas físicas (manifiesto Fact_Telemetria_Clima)
    "bronce.clima":                    [{"tabla": "Bronce.Reporte_Clima",            "pk": "ID_Reporte_Clima"}],
    "bronce.reporte_clima":            [{"tabla": "Bronce.Reporte_Clima",            "pk": "ID_Reporte_Clima"}],
    # Origen lógico cosecha SAP → 2 tablas físicas (manifiesto Fact_Cosecha_SAP)
    "bronce.cosecha_sap": [
        {"tabla": "Bronce.Reporte_Cosecha", "pk": "ID_Reporte_Cosecha"},
        {"tabla": "Bronce.Data_SAP",        "pk": "ID_Data_SAP"},
    ],
    "bronce.reporte_cosecha":          [{"tabla": "Bronce.Reporte_Cosecha",          "pk": "ID_Reporte_Cosecha"}],
    "bronce.data_sap":                 [{"tabla": "Bronce.Data_SAP",                 "pk": "ID_Data_SAP"}],
    # Origen lógico ciclo poda → 2 tablas físicas (manifiesto Fact_Ciclo_Poda)
    "bronce.ciclo_poda": [
        {"tabla": "Bronce.Evaluacion_Calidad_Poda", "pk": "ID_Evaluacion_Poda"},
        {"tabla": "Bronce.Ciclos_Fenologicos",      "pk": "ID_Ciclo_Fenologico"},
    ],
    "bronce.evaluacion_calidad_poda":  [{"tabla": "Bronce.Evaluacion_Calidad_Poda",  "pk": "ID_Evaluacion_Poda"}],
    "bronce.ciclos_fenologicos":       [{"tabla": "Bronce.Ciclos_Fenologicos",       "pk": "ID_Ciclo_Fenologico"}],
    # Sanidad — el manifiesto usa Bronce.Seguimiento_Errores como fuente
    "bronce.sanidad_activo":           [{"tabla": "Bronce.Seguimiento_Errores",      "pk": "ID_Seguimiento_Errores"}],
    "bronce.seguimiento_errores":      [{"tabla": "Bronce.Seguimiento_Errores",      "pk": "ID_Seguimiento_Errores"}],
}


def obtener_resueltos_pendientes(tabla_filtro: str | None = None) -> list[dict]:
    """
    Obtiene todos los registros RESUELTOS en MDM.Cuarentena que aún no han
    sido reinyectados al pipeline (es decir, ID_Registro_Origen IS NOT NULL).

    Opcional: filtrar por tabla_origen (parcial, case-insensitive).
    """
    clausula_filtro = ""
    params: dict = {}
    if tabla_filtro:
        clausula_filtro = "AND LOWER(Tabla_Origen) LIKE :filtro"
        params["filtro"] = f"%{tabla_filtro.lower()}%"

    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text(f"""
                    SELECT
                        CAST(ID_Cuarentena AS VARCHAR(30)) AS id_cuarentena,
                        Tabla_Origen                       AS tabla_origen,
                        Campo_Origen                       AS campo_origen,
                        Valor_Recibido                     AS valor_raw,
                        Valor_Corregido                    AS valor_corregido,
                        ID_Registro_Origen                 AS id_registro_origen
                    FROM MDM.Cuarentena
                    WHERE Estado = 'RESUELTO'
                      AND ID_Registro_Origen IS NOT NULL
                    {clausula_filtro}
                    ORDER BY Tabla_Origen, ID_Cuarentena
                """),
                params,
            ).fetchall()

        return [dict(f._mapping) for f in filas]

    except SQLAlchemyError:
        log.exception("Error al obtener resueltos para reinyección")
        raise ErrorBaseDatos()


def reinyectar_en_bronce(registros: list[dict]) -> dict:
    """
    Para cada registro resuelto, actualiza Estado_Carga = 'CARGADO' en Bronce.

    Agrupa por tabla para hacer un solo UPDATE por conjunto de IDs.

    Retorna: {reinyectados: int, omitidos: int, detalle: list[str]}
    """
    reinyectados = 0
    omitidos = 0
    detalle: list[str] = []

    # Agrupar IDs por tabla
    por_tabla: dict[str, list[int]] = {}
    for reg in registros:
        tabla_key = reg["tabla_origen"].lower()
        id_origen = reg.get("id_registro_origen")

        if tabla_key not in _TABLAS_BRONCE:
            omitidos += 1
            detalle.append(f"⚠️ Tabla '{reg['tabla_origen']}' no mapeada — omitida.")
            continue

        if not id_origen:
            omitidos += 1
            detalle.append(f"⚠️ Registro #{reg['id_cuarentena']} sin ID_Registro_Origen — omitido.")
            continue

        por_tabla.setdefault(tabla_key, []).append(int(id_origen))

    if not por_tabla:
        return {"reinyectados": 0, "omitidos": omitidos, "detalle": detalle}

    try:
        with obtener_engine().begin() as con:
            for tabla_key, ids in por_tabla.items():
                # Construimos placeholders de forma segura una sola vez por origen
                placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
                params_ids = {f"id_{i}": v for i, v in enumerate(ids)}

                # Un origen lógico puede mapear a varias tablas físicas (clima, cosecha, poda).
                # Probamos cada destino: el ID solo existirá en la tabla correcta.
                for destino in _TABLAS_BRONCE[tabla_key]:
                    tabla_sql = destino["tabla"]
                    pk_sql = destino["pk"]

                    resultado = con.execute(
                        text(f"""
                            UPDATE {tabla_sql}
                            SET Estado_Carga = 'CARGADO'
                            WHERE {pk_sql} IN ({placeholders})
                              AND Estado_Carga = 'RECHAZADO'
                        """),
                        params_ids,
                    )
                    n = resultado.rowcount
                    reinyectados += n
                    detalle.append(f"✅ {tabla_sql}: {n} registros reactivados de {len(ids)} candidatos.")

                    log.info(
                        "Reinyección completada para tabla",
                        extra={"tabla": tabla_sql, "actualizados": n, "candidatos": len(ids)},
                    )

    except SQLAlchemyError:
        log.exception("Error durante reinyección en Bronce")
        raise ErrorBaseDatos()

    return {"reinyectados": reinyectados, "omitidos": omitidos, "detalle": detalle}


def contar_candidatos_reinyeccion(tabla_filtro: str | None = None) -> int:
    """Retorna el conteo rápido de registros RESUELTOS disponibles para reinyectar."""
    clausula_filtro = ""
    params: dict = {}
    if tabla_filtro:
        clausula_filtro = "AND LOWER(Tabla_Origen) LIKE :filtro"
        params["filtro"] = f"%{tabla_filtro.lower()}%"

    try:
        with obtener_engine().connect() as con:
            total = con.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM MDM.Cuarentena
                    WHERE Estado = 'RESUELTO'
                      AND ID_Registro_Origen IS NOT NULL
                    {clausula_filtro}
                """),
                params,
            ).scalar() or 0
        return int(total)
    except SQLAlchemyError:
        log.exception("Error al contar candidatos para reinyección")
        raise ErrorBaseDatos()
