"""
repositorios/repo_auditoria.py
================================
Todas las consultas SQL relacionadas con Auditoria.Log_Carga
y Auditoria.Log_Decisiones_MDM.

Contrato:
- Recibe parámetros tipados.
- Retorna dicts o None; nunca retorna Row de SQLAlchemy al exterior.
- Propaga ErrorBaseDatos si falla la BD.
- Falla silenciosamente solo donde está documentado (registro de auditoría).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


# ── Escritura ──────────────────────────────────────────────────────────────────

def insertar_inicio_corrida(
    nombre_proceso: str,
    tabla_destino: str,
    nombre_archivo: str = "API_BACKEND",
) -> int | None:
    """
    Inserta una fila en Auditoria.Log_Carga con estado EN_PROCESO.
    Retorna el ID generado o None si falla (fallo silencioso).
    """
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("""
                    INSERT INTO Auditoria.Log_Carga (
                        Nombre_Proceso,
                        Tabla_Destino,
                        Nombre_Archivo_Fuente,
                        Fecha_Inicio,
                        Estado_Proceso,
                        Filas_Leidas,
                        Filas_Insertadas,
                        Filas_Rechazadas,
                        Duracion_Segundos,
                        Mensaje_Error
                    )
                    OUTPUT INSERTED.ID_Log_Carga
                    VALUES (
                        :nombre_proceso,
                        :tabla_destino,
                        :nombre_archivo,
                        :fecha_inicio,
                        'EN_PROCESO',
                        0, 0, 0, 0, NULL
                    )
                """),
                {
                    "nombre_proceso": nombre_proceso,
                    "tabla_destino":  tabla_destino,
                    "nombre_archivo": nombre_archivo,
                    "fecha_inicio":   datetime.now(tz=timezone.utc),
                },
            )
            id_log = resultado.fetchone()[0]
            log.debug("Corrida registrada en auditoría", extra={"id_log": id_log})
            return id_log
    except SQLAlchemyError:
        log.exception("No se pudo registrar inicio de corrida en auditoría")
        return None


def actualizar_fin_corrida(
    id_log: int,
    estado: str,
    filas_insertadas: int = 0,
    filas_rechazadas: int = 0,
    mensaje_error: str | None = None,
) -> None:
    """
    Actualiza la fila de auditoría al finalizar (OK o ERROR).
    Falla silenciosamente para no bloquear la respuesta al cliente.
    """
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    UPDATE Auditoria.Log_Carga
                    SET
                        Fecha_Fin         = :fecha_fin,
                        Estado_Proceso    = :estado,
                        Filas_Insertadas  = :filas_insertadas,
                        Filas_Rechazadas  = :filas_rechazadas,
                        Duracion_Segundos = DATEDIFF(SECOND, Fecha_Inicio, :fecha_fin),
                        Mensaje_Error     = :mensaje_error
                    WHERE ID_Log_Carga = :id_log
                """),
                {
                    "fecha_fin":        datetime.now(tz=timezone.utc),
                    "estado":           estado,
                    "filas_insertadas": filas_insertadas,
                    "filas_rechazadas": filas_rechazadas,
                    "mensaje_error":    mensaje_error,
                    "id_log":           id_log,
                },
            )
    except SQLAlchemyError:
        log.exception("No se pudo actualizar fin de corrida en auditoría", extra={"id_log": id_log})


def insertar_decision_mdm(
    tabla_origen: str,
    id_registro: str,
    valor_canonico: str,
    decision: str,
    analista: str,
    comentario: str,
) -> None:
    """
    Registra la decisión MDM en Auditoria.Log_Decisiones_MDM.
    Falla silenciosamente si la tabla no existe o hay error.
    """
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    INSERT INTO Auditoria.Log_Decisiones_MDM (
                        Tabla_Origen,
                        Texto_Crudo,
                        Valor_Canonico,
                        Decision,
                        Analista_DNI,
                        Comentario,
                        Fecha_Decision
                    ) VALUES (
                        :tabla_origen,
                        :id_registro,
                        :valor_canonico,
                        :decision,
                        :analista,
                        :comentario,
                        :fecha_decision
                    )
                """),
                {
                    "tabla_origen":    tabla_origen,
                    "id_registro":     id_registro,
                    "valor_canonico":  valor_canonico,
                    "decision":        decision,
                    "analista":        analista,
                    "comentario":      comentario,
                    "fecha_decision":  datetime.now(tz=timezone.utc),
                },
            )
    except SQLAlchemyError:
        log.warning("No se pudo registrar decisión MDM en auditoría")


# ── Lectura ────────────────────────────────────────────────────────────────────

def _construir_filtros_bitacora(
    estado: list[str] | None,
    tabla_destino: str | None,
    desde: datetime | None,
    hasta: datetime | None,
    id_corrida: str | None,
) -> tuple[str, dict]:
    """Construye WHERE compartido entre listar_bitacora y contar_bitacora."""
    where: list[str] = []
    params: dict = {}

    if estado:
        marcadores = ", ".join(f":estado_{i}" for i in range(len(estado)))
        where.append(f"lc.Estado_Proceso IN ({marcadores})")
        for i, e in enumerate(estado):
            params[f"estado_{i}"] = e
    if tabla_destino:
        where.append("lc.Tabla_Destino LIKE :tabla")
        params["tabla"] = f"%{tabla_destino}%"
    if desde:
        where.append("lc.Fecha_Inicio >= :desde")
        params["desde"] = desde
    if hasta:
        where.append("lc.Fecha_Inicio <= :hasta")
        params["hasta"] = hasta
    if id_corrida:
        where.append("CAST(c.ID_Corrida AS NVARCHAR(36)) = :id_corrida")
        params["id_corrida"] = id_corrida

    clausula_where = ("WHERE " + " AND ".join(where)) if where else ""
    return clausula_where, params


def listar_bitacora(
    pagina: int = 1,
    tamano: int = 50,
    estado: list[str] | None = None,
    tabla_destino: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    id_corrida: str | None = None,
) -> list[dict]:
    """
    Consulta paginada de Auditoria.Log_Carga con filtros opcionales.
    Page-size acotado por el caller (ver capa rutas).
    """
    pagina = max(1, pagina)
    tamano = max(1, min(tamano, 200))
    offset = (pagina - 1) * tamano

    clausula_where, params = _construir_filtros_bitacora(estado, tabla_destino, desde, hasta, id_corrida)
    params.update({"offset": offset, "tamano": tamano})

    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text(f"""
                    SELECT
                        lc.ID_Log_Carga            AS id_log,
                        lc.Nombre_Proceso          AS nombre_proceso,
                        lc.Tabla_Destino           AS tabla_destino,
                        lc.Nombre_Archivo_Fuente   AS nombre_archivo,
                        lc.Fecha_Inicio            AS fecha_inicio,
                        lc.Fecha_Fin               AS fecha_fin,
                        lc.Estado_Proceso          AS estado,
                        lc.Filas_Insertadas        AS filas_insertadas,
                        lc.Filas_Rechazadas        AS filas_rechazadas,
                        lc.Duracion_Segundos       AS duracion_segundos,
                        lc.Mensaje_Error           AS mensaje_error,
                        CAST(c.ID_Corrida AS NVARCHAR(36)) AS id_corrida
                    FROM Auditoria.Log_Carga lc WITH (NOLOCK)
                    LEFT JOIN Control.Corrida c WITH (NOLOCK)
                           ON c.ID_Log_Auditoria = lc.ID_Log_Carga
                    {clausula_where}
                    ORDER BY lc.Fecha_Inicio DESC, lc.ID_Log_Carga DESC
                    OFFSET :offset ROWS
                    FETCH NEXT :tamano ROWS ONLY
                """),
                params,
            ).fetchall()
            return [dict(fila._mapping) for fila in filas]
    except SQLAlchemyError:
        log.exception("Error al listar bitácora")
        return []


def contar_bitacora(
    estado: list[str] | None = None,
    tabla_destino: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    id_corrida: str | None = None,
) -> int:
    """COUNT total bajo los mismos filtros que listar_bitacora."""
    clausula_where, params = _construir_filtros_bitacora(estado, tabla_destino, desde, hasta, id_corrida)
    try:
        with obtener_engine().connect() as con:
            total = con.execute(
                text(f"""
                    SELECT COUNT(*) AS total
                    FROM Auditoria.Log_Carga lc WITH (NOLOCK)
                    LEFT JOIN Control.Corrida c WITH (NOLOCK)
                           ON c.ID_Log_Auditoria = lc.ID_Log_Carga
                    {clausula_where}
                """),
                params,
            ).scalar()
            return int(total or 0)
    except SQLAlchemyError:
        log.exception("Error al contar bitácora")
        return 0


def obtener_detalle_log(id_log: int) -> dict | None:
    """Retorna detalle completo de una entrada Log_Carga (incluye mensaje_error sin truncar)."""
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        lc.ID_Log_Carga            AS id_log,
                        lc.Nombre_Proceso          AS nombre_proceso,
                        lc.Tabla_Destino           AS tabla_destino,
                        lc.Nombre_Archivo_Fuente   AS nombre_archivo,
                        lc.Fecha_Inicio            AS fecha_inicio,
                        lc.Fecha_Fin               AS fecha_fin,
                        lc.Estado_Proceso          AS estado,
                        lc.Filas_Insertadas        AS filas_insertadas,
                        lc.Filas_Rechazadas        AS filas_rechazadas,
                        lc.Duracion_Segundos       AS duracion_segundos,
                        lc.Mensaje_Error           AS mensaje_error,
                        CAST(c.ID_Corrida AS NVARCHAR(36)) AS id_corrida
                    FROM Auditoria.Log_Carga lc WITH (NOLOCK)
                    LEFT JOIN Control.Corrida c WITH (NOLOCK)
                           ON c.ID_Log_Auditoria = lc.ID_Log_Carga
                    WHERE lc.ID_Log_Carga = :id_log
                """),
                {"id_log": id_log},
            ).fetchone()
            return dict(fila._mapping) if fila else None
    except SQLAlchemyError:
        log.exception("Error al obtener detalle de log", extra={"id_log": id_log})
        raise ErrorBaseDatos()


def resumen_bitacora(ventana_dias: int) -> dict:
    """
    KPIs de la bitácora para la ventana dada (1=hoy, 7=últimos 7 días, 30=últimos 30).
    Retorna: total, ok, error, en_proceso, filas_ok, filas_rechazadas, tasa_exito_pct.
    """
    ventana_dias = max(1, min(ventana_dias, 365))
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        COUNT(*)                                                        AS total,
                        SUM(CASE WHEN Estado_Proceso = 'OK'         THEN 1 ELSE 0 END) AS ok,
                        SUM(CASE WHEN Estado_Proceso = 'ERROR'      THEN 1 ELSE 0 END) AS errores,
                        SUM(CASE WHEN Estado_Proceso = 'EN_PROCESO' THEN 1 ELSE 0 END) AS en_proceso,
                        COALESCE(SUM(Filas_Insertadas), 0)                              AS filas_ok,
                        COALESCE(SUM(Filas_Rechazadas), 0)                              AS filas_rechazadas
                    FROM Auditoria.Log_Carga WITH (NOLOCK)
                    WHERE Fecha_Inicio >= DATEADD(DAY, -:dias, GETDATE())
                """),
                {"dias": ventana_dias},
            ).fetchone()
            datos = dict(fila._mapping) if fila else {}
            total = int(datos.get("total") or 0)
            ok = int(datos.get("ok") or 0)
            tasa = round((ok / total) * 100, 1) if total else 0.0
            return {
                "ventana_dias":     ventana_dias,
                "total":            total,
                "ok":               ok,
                "errores":          int(datos.get("errores") or 0),
                "en_proceso":       int(datos.get("en_proceso") or 0),
                "filas_ok":         int(datos.get("filas_ok") or 0),
                "filas_rechazadas": int(datos.get("filas_rechazadas") or 0),
                "tasa_exito_pct":   tasa,
            }
    except SQLAlchemyError:
        log.exception("Error al obtener resumen de bitácora")
        return {
            "ventana_dias":     ventana_dias,
            "total":            0,
            "ok":               0,
            "errores":          0,
            "en_proceso":       0,
            "filas_ok":         0,
            "filas_rechazadas": 0,
            "tasa_exito_pct":   0.0,
        }


# ── Compatibilidad legacy (uso interno por servicio_auditoria) ─────────────────

def listar_corridas(
    limite: int = 50,
    tabla_destino: str | None = None,
) -> list[dict]:
    """Wrapper legacy sobre listar_bitacora — preserva firma del endpoint actual."""
    return listar_bitacora(
        pagina=1,
        tamano=min(limite, 200),
        tabla_destino=tabla_destino,
    )


def contar_fallos_recientes(horas: int = 24) -> dict:
    """
    Resumen barato para el indicador de salud del dashboard.

    Cuenta corridas en estado ERROR/TIMEOUT iniciadas en las últimas `horas` horas
    y devuelve el último fallo (timestamp + tabla). Una sola consulta agregada
    en lugar de bajar 50 corridas y filtrar en código.

    Retorna:
        {
          "fallos": int,
          "ultimo_fallo_fecha": datetime | None,
          "ultimo_fallo_tabla": str | None,
        }
    """
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        COUNT(*)                                              AS fallos,
                        MAX(Fecha_Inicio)                                     AS ultimo_fallo_fecha,
                        MAX(CASE WHEN rn = 1 THEN Tabla_Destino END)          AS ultimo_fallo_tabla
                    FROM (
                        SELECT
                            Fecha_Inicio,
                            Tabla_Destino,
                            ROW_NUMBER() OVER (ORDER BY Fecha_Inicio DESC)    AS rn
                        FROM Auditoria.Log_Carga WITH (NOLOCK)
                        WHERE Estado_Proceso IN ('ERROR', 'TIMEOUT')
                          AND Fecha_Inicio >= DATEADD(HOUR, -:horas, SYSUTCDATETIME())
                    ) AS recientes
                """),
                {"horas": horas},
            ).fetchone()
            if fila is None:
                return {"fallos": 0, "ultimo_fallo_fecha": None, "ultimo_fallo_tabla": None}
            d = dict(fila._mapping)
            return {
                "fallos": int(d.get("fallos") or 0),
                "ultimo_fallo_fecha": d.get("ultimo_fallo_fecha"),
                "ultimo_fallo_tabla": d.get("ultimo_fallo_tabla"),
            }
    except SQLAlchemyError:
        log.exception("Error al contar fallos recientes", extra={"horas": horas})
        raise ErrorBaseDatos()


def ultimo_estado_tabla(tabla_destino: str) -> dict | None:
    """
    Retorna el último estado de carga para una tabla específica.
    None si no hay registros.
    """
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT TOP 1
                        Tabla_Destino       AS tabla_destino,
                        Estado_Proceso      AS estado,
                        Fecha_Inicio        AS fecha_inicio,
                        Fecha_Fin           AS fecha_fin,
                        Filas_Insertadas    AS filas_insertadas,
                        Duracion_Segundos   AS duracion_segundos,
                        Mensaje_Error       AS mensaje_error
                    FROM Auditoria.Log_Carga
                    WHERE Tabla_Destino = :tabla
                    ORDER BY Fecha_Inicio DESC
                """),
                {"tabla": tabla_destino},
            ).fetchone()
            return dict(fila._mapping) if fila else None
    except SQLAlchemyError:
        log.exception("Error al consultar último estado de tabla", extra={"tabla": tabla_destino})
        raise ErrorBaseDatos()
