"""
repositorios/repo_corridas.py
=============================
Operaciones sobre Control.Corrida, Corrida_Evento y Corrida_Paso.
"""

from __future__ import annotations
from datetime import datetime, timezone
import time
from typing import Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

EstadoCorrida = Literal["PENDIENTE", "EJECUTANDO", "OK", "ERROR", "CANCELADO", "TIMEOUT"]
TipoEvento    = Literal["LOG", "PROGRESO", "ERROR", "FIN"]

def insertar_corrida(
    id_corrida: str,
    iniciado_por: str,
    comentario: str | None = None,
    max_reintentos: int = 0,
    timeout_segundos: int = 3600,
) -> None:
    with obtener_engine().begin() as con:
        con.execute(
            text("""
                INSERT INTO Control.Corrida
                    (ID_Corrida, Iniciado_Por, Comentario, Estado,
                     Max_Reintentos, Timeout_Segundos, Fecha_Solicitud)
                VALUES
                    (:id, :usuario, :comentario, 'PENDIENTE',
                     :max_ret, :timeout, :ahora)
            """),
            {
                "id":         id_corrida,
                "usuario":    iniciado_por,
                "comentario": comentario,
                "max_ret":    max_reintentos,
                "timeout":    timeout_segundos,
                "ahora":      datetime.now(tz=timezone.utc),
            },
        )

def obtener_corrida(id_corrida: str) -> dict | None:
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        ID_Corrida          AS id_corrida,
                        Iniciado_Por        AS iniciado_por,
                        Comentario          AS comentario,
                        Estado              AS estado,
                        Intento_Numero      AS intento_numero,
                        Max_Reintentos      AS max_reintentos,
                        Fecha_Solicitud     AS fecha_solicitud,
                        Fecha_Inicio        AS fecha_inicio,
                        Fecha_Fin           AS fecha_fin,
                        PID_Runner          AS pid_runner,
                        Heartbeat_Ultimo    AS heartbeat_ultimo,
                        Timeout_Segundos    AS timeout_segundos,
                        Mensaje_Final       AS mensaje_final,
                        ID_Log_Auditoria    AS id_log_auditoria
                    FROM Control.Corrida
                    WHERE ID_Corrida = :id
                """),
                {"id": id_corrida},
            ).fetchone()
            return dict(fila._mapping) if fila else None
    except SQLAlchemyError:
        log.exception("Error al obtener corrida", extra={"id_corrida": id_corrida})
        raise ErrorBaseDatos()

def listar_corridas(limite: int = 50, solo_activas: bool = False) -> list[dict]:
    filtro = "WHERE Estado IN ('PENDIENTE','EJECUTANDO')" if solo_activas else ""
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text(f"""
                    SELECT TOP (:limite)
                        ID_Corrida          AS id_corrida,
                        Iniciado_Por        AS iniciado_por,
                        Comentario          AS comentario,
                        Estado              AS estado,
                        Intento_Numero      AS intento_numero,
                        Max_Reintentos      AS max_reintentos,
                        Fecha_Solicitud     AS fecha_solicitud,
                        Fecha_Inicio        AS fecha_inicio,
                        Fecha_Fin           AS fecha_fin,
                        Heartbeat_Ultimo    AS heartbeat_ultimo,
                        Mensaje_Final       AS mensaje_final,
                        ID_Log_Auditoria    AS id_log_auditoria
                    FROM Control.Corrida
                    {filtro}
                    ORDER BY Fecha_Solicitud DESC, ID_Corrida DESC
                """),
                {"limite": limite},
            ).fetchall()
            return [dict(f._mapping) for f in filas]
    except SQLAlchemyError:
        log.exception("Error al listar corridas")
        raise ErrorBaseDatos()

_ESTADOS_TERMINALES = ("OK", "ERROR", "CANCELADO", "TIMEOUT")

_SQL_ACTUALIZAR_ESTADO_CORRIDA = text("""
    UPDATE Control.Corrida
    SET Estado = :estado,
        Fecha_Inicio = CASE
            WHEN :estado = 'EJECUTANDO' THEN :ahora
            ELSE Fecha_Inicio
        END,
        Fecha_Fin = CASE
            WHEN :estado IN ('OK','ERROR','CANCELADO','TIMEOUT') THEN :ahora
            ELSE Fecha_Fin
        END,
        PID_Runner = CASE
            WHEN :estado = 'EJECUTANDO' THEN :pid
            WHEN :estado IN ('OK','ERROR','CANCELADO','TIMEOUT') THEN NULL
            ELSE PID_Runner
        END,
        Mensaje_Final = CASE
            WHEN :tiene_mensaje = 1 THEN :msg
            ELSE Mensaje_Final
        END,
        ID_Log_Auditoria = CASE
            WHEN :tiene_log = 1 THEN :id_log
            ELSE ID_Log_Auditoria
        END
    WHERE ID_Corrida = :id
""")


def actualizar_estado_corrida(
    id_corrida: str,
    estado: EstadoCorrida,
    mensaje_final: str | None = None,
    id_log_auditoria: int | None = None,
    pid_runner: int | None = None,
) -> None:
    params = {
        "id": id_corrida,
        "estado": estado,
        "ahora": datetime.now(tz=timezone.utc),
        "pid": pid_runner,
        "tiene_mensaje": 1 if mensaje_final is not None else 0,
        "msg": (mensaje_final or "")[:1000],
        "tiene_log": 1 if id_log_auditoria is not None else 0,
        "id_log": id_log_auditoria,
    }
    try:
        with obtener_engine().begin() as con:
            con.execute(_SQL_ACTUALIZAR_ESTADO_CORRIDA, params)
    except SQLAlchemyError:
        log.exception("Error al actualizar estado de corrida", extra={"id_corrida": id_corrida})
        raise ErrorBaseDatos()

def actualizar_heartbeat_corrida(id_corrida: str, pid: int) -> None:
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    UPDATE Control.Corrida
                    SET Heartbeat_Ultimo = :ahora, PID_Runner = :pid
                    WHERE ID_Corrida = :id
                """),
                {"ahora": datetime.now(tz=timezone.utc), "pid": pid, "id": id_corrida},
            )
    except SQLAlchemyError:
        log.warning("No se pudo actualizar heartbeat", extra={"id_corrida": id_corrida})

def corrida_fue_cancelada(id_corrida: str) -> bool:
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT 1 FROM Control.Corrida
                    WHERE ID_Corrida = :id AND Estado = 'CANCELADO'
                """),
                {"id": id_corrida},
            ).fetchone()
            return fila is not None
    except SQLAlchemyError:
        return False

def insertar_evento(id_corrida: str, mensaje: str, tipo: TipoEvento = "LOG") -> None:
    params = {
        "id":   id_corrida,
        "tipo": tipo,
        "msg":  mensaje[:4000],
        "ahora": datetime.now(tz=timezone.utc),
    }
    _sql = text("""
        INSERT INTO Control.Corrida_Evento
            (ID_Corrida, Tipo, Mensaje, Fecha_Evento)
        VALUES (:id, :tipo, :msg, :ahora)
    """)
    for intento in range(2):
        try:
            with obtener_engine().begin() as con:
                con.execute(_sql, params)
            return
        except SQLAlchemyError:
            if intento == 0:
                time.sleep(0.5)
            else:
                log.warning("No se pudo persistir evento tras reintento", extra={"id_corrida": id_corrida})

def insertar_eventos_batch(eventos: list[dict]) -> None:
    """Inserta una lista de eventos (id_corrida, mensaje, tipo) en batch."""
    if not eventos:
        return
    ahora = datetime.now(tz=timezone.utc)
    params = [
        {
            "id": ev["id_corrida"],
            "tipo": ev.get("tipo", "LOG"),
            "msg": ev["mensaje"][:4000],
            "ahora": ahora,
        }
        for ev in eventos
    ]
    _sql = text("""
        INSERT INTO Control.Corrida_Evento
            (ID_Corrida, Tipo, Mensaje, Fecha_Evento)
        VALUES (:id, :tipo, :msg, :ahora)
    """)
    for intento in range(2):
        try:
            with obtener_engine().begin() as con:
                con.execute(_sql, params)
            return
        except SQLAlchemyError:
            if intento == 0:
                time.sleep(0.5)
            else:
                log.warning("No se pudo persistir lote de eventos", extra={"cantidad": len(eventos)})

def listar_eventos_y_estado(
    id_corrida: str,
    desde_id: int = 0,
    limite: int = 500,
) -> tuple[list[dict], str | None]:
    """
    Combina listado de eventos nuevos + estado actual de la corrida en una sola
    query (CROSS JOIN). Reduce de 2-3 queries a 1 por ciclo de polling SSE.
    Retorna (eventos, estado_corrida_o_None).
    """
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text("""
                    SELECT TOP (:limite)
                        ce.ID_Evento    AS id_evento,
                        ce.Tipo         AS tipo,
                        ce.Mensaje      AS mensaje,
                        ce.Fecha_Evento AS fecha_evento,
                        c.Estado        AS estado_corrida
                    FROM Control.Corrida_Evento ce
                    INNER JOIN Control.Corrida c
                        ON c.ID_Corrida = ce.ID_Corrida
                    WHERE ce.ID_Corrida = :id AND ce.ID_Evento > :desde
                    ORDER BY ce.ID_Evento ASC
                """),
                {"id": id_corrida, "desde": desde_id, "limite": limite},
            ).fetchall()

            estado: str | None = None
            eventos: list[dict] = []
            for fila in filas:
                m = dict(fila._mapping)
                estado = m.pop("estado_corrida", None) or estado
                eventos.append(m)

            if estado is None:
                fila_estado = con.execute(
                    text("SELECT Estado AS estado FROM Control.Corrida WHERE ID_Corrida = :id"),
                    {"id": id_corrida},
                ).fetchone()
                estado = fila_estado.estado if fila_estado else None

            return eventos, estado
    except SQLAlchemyError:
        log.exception("Error al listar eventos+estado", extra={"id_corrida": id_corrida})
        return [], None


def insertar_paso(id_corrida: str, nombre_paso: str, orden: int = 1) -> int:
    """Inserta un paso en Control.Corrida_Paso. Retorna el ID_Paso generado, o lanza ErrorBaseDatos."""
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("""
                    INSERT INTO Control.Corrida_Paso
                        (ID_Corrida, Nombre_Paso, Orden, Estado, Fecha_Inicio)
                    OUTPUT INSERTED.ID_Paso
                    VALUES (:id, :nombre, :orden, 'EJECUTANDO', :ahora)
                """),
                {
                    "id": id_corrida,
                    "nombre": nombre_paso,
                    "orden": orden,
                    "ahora": datetime.now(tz=timezone.utc),
                },
            )
            return resultado.fetchone()[0]
    except SQLAlchemyError:
        log.exception("Error al insertar paso", extra={"id_corrida": id_corrida})
        raise ErrorBaseDatos()

def cerrar_paso(
    id_paso: int,
    estado: str,
    mensaje_error: str | None = None,
    filas_procesadas: int = 0,
    filas_rechazadas: int = 0,
) -> None:
    # PENDIENTE MIGRACIÓN: columnas Filas_Procesadas y Filas_Rechazadas aún no existen.
    # Una vez aplicado backend/migrations/add_filas_to_corrida_paso.sql, reemplazar
    # este UPDATE con la versión que incluye:
    #   SET Filas_Procesadas = :filas_proc, Filas_Rechazadas = :filas_rec
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    UPDATE Control.Corrida_Paso
                    SET Estado = :estado, Fecha_Fin = :ahora, Mensaje_Error = :err
                    WHERE ID_Paso = :id
                """),
                {"estado": estado, "ahora": datetime.now(tz=timezone.utc), "err": mensaje_error, "id": id_paso},
            )
    except SQLAlchemyError:
        log.warning("No se pudo cerrar paso", extra={"id_paso": id_paso})

def listar_pasos_corrida(id_corrida: str) -> list[dict]:
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text("""
                    SELECT
                        ID_Paso        AS id_paso,
                        ID_Corrida     AS id_corrida,
                        Nombre_Paso    AS nombre_paso,
                        Orden          AS orden,
                        Estado         AS estado,
                        Fecha_Inicio   AS fecha_inicio,
                        Fecha_Fin      AS fecha_fin,
                        Mensaje_Error  AS mensaje_error
                    FROM Control.Corrida_Paso
                    WHERE ID_Corrida = :id
                    ORDER BY Orden ASC, ID_Paso ASC
                """),
                {"id": id_corrida},
            ).fetchall()
            return [dict(fila._mapping) for fila in filas]
    except SQLAlchemyError:
        log.exception("Error al listar pasos de corrida", extra={"id_corrida": id_corrida})
        raise ErrorBaseDatos()

def solicitar_cancelacion(id_corrida: str, solicitado_por: str) -> bool:
    try:
        with obtener_engine().begin() as con:
            rows = con.execute(
                text("""
                    UPDATE Control.Corrida
                    SET Estado = 'CANCELADO',
                        Mensaje_Final = :msg,
                        Fecha_Fin = GETDATE()
                    WHERE ID_Corrida = :id
                      AND Estado IN ('PENDIENTE', 'EJECUTANDO')
                """),
                {
                    "id":  id_corrida,
                    "msg": f"Cancelado por {solicitado_por}",
                },
            ).rowcount
            return rows > 0
    except SQLAlchemyError:
        log.exception("Error al solicitar cancelación")
        return False

def obtener_resumen_control_plane() -> dict:
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM Control.Corrida
                         WHERE Estado IN ('PENDIENTE', 'EJECUTANDO')) AS corridas_activas,
                        (SELECT COUNT(*) FROM Control.Comando_Ejecucion
                         WHERE Estado_Cmd = 'PENDIENTE') AS comandos_pendientes,
                        (SELECT COUNT(*) FROM Control.Comando_Ejecucion
                         WHERE Estado_Cmd = 'PROCESANDO') AS comandos_procesando
                """)
            ).fetchone()
            if not fila:
                return {
                    "corridas_activas": 0,
                    "comandos_pendientes": 0,
                    "comandos_procesando": 0,
                }
            return dict(fila._mapping)
    except SQLAlchemyError:
        log.exception("Error al consultar resumen del control-plane")
        raise ErrorBaseDatos()
