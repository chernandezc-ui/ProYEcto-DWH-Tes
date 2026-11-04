"""
repositorios/repo_locks.py
==========================
Gestión de exclusión mutua para el runner ETL (Control.Bloqueo_Ejecucion).
"""

from __future__ import annotations
import socket
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos, ErrorRecursoNoEncontrado
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)
_HOSTNAME = socket.gethostname()

def adquirir_lock(id_corrida: str, timeout_lock_seg: int = 120) -> bool:
    try:
        with obtener_engine().begin() as con:
            rows = con.execute(
                text("""
                    UPDATE Control.Bloqueo_Ejecucion
                    SET
                        ID_Corrida_Activa = :corrida,
                        Adquirido_Por     = :host,
                        Fecha_Adquisicion = :ahora,
                        Heartbeat         = :ahora
                    WHERE ID_Lock = 1
                      AND (
                          ID_Corrida_Activa IS NULL
                          OR DATEDIFF(SECOND, Heartbeat, GETDATE()) > :timeout_lock
                      )
                """),
                {
                    "corrida":      id_corrida,
                    "host":         _HOSTNAME,
                    "ahora":        datetime.now(tz=timezone.utc),
                    "timeout_lock": timeout_lock_seg,
                },
            ).rowcount
            return rows == 1
    except SQLAlchemyError:
        log.exception("Error al adquirir lock")
        return False

def liberar_lock(id_corrida: str) -> None:
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    UPDATE Control.Bloqueo_Ejecucion
                    SET ID_Corrida_Activa = NULL, Adquirido_Por = NULL,
                        Fecha_Adquisicion = NULL, Heartbeat = NULL
                    WHERE ID_Lock = 1 AND ID_Corrida_Activa = :corrida
                """),
                {"corrida": id_corrida},
            )
    except SQLAlchemyError:
        log.warning("No se pudo liberar el lock", extra={"id_corrida": id_corrida})

def actualizar_heartbeat_lock(id_corrida: str | None = None) -> None:
    """
    Refresca el heartbeat del lock activo.
    Si se pasa id_corrida, solo actualiza si el lock pertenece a esa corrida
    (evita refrescar un lock robado por otro runner).
    """
    try:
        with obtener_engine().begin() as con:
            if id_corrida is not None:
                rows = con.execute(
                    text(
                        "UPDATE Control.Bloqueo_Ejecucion "
                        "SET Heartbeat = GETDATE() "
                        "WHERE ID_Lock = 1 AND ID_Corrida_Activa = :corrida"
                    ),
                    {"corrida": id_corrida},
                ).rowcount
                if rows == 0:
                    log.warning(
                        "[LOCK] Heartbeat no aplicado — lock ya no pertenece a esta corrida",
                        extra={"id_corrida": id_corrida},
                    )
            else:
                con.execute(
                    text("UPDATE Control.Bloqueo_Ejecucion SET Heartbeat = GETDATE() WHERE ID_Lock = 1")
                )
    except SQLAlchemyError:
        log.warning("[LOCK] Fallo al actualizar heartbeat del lock", exc_info=True)

def lock_activo() -> dict | None:
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT ID_Corrida_Activa, Adquirido_Por,
                           Fecha_Adquisicion, Heartbeat
                    FROM Control.Bloqueo_Ejecucion
                    WHERE ID_Lock = 1 AND ID_Corrida_Activa IS NOT NULL
                """)
            ).fetchone()
            return dict(fila._mapping) if fila else None
    except SQLAlchemyError:
        return None

def obtener_estado_lock(timeout_lock_seg: int = 120) -> dict:
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        ID_Lock                 AS id_lock,
                        ID_Corrida_Activa       AS id_corrida_activa,
                        Adquirido_Por           AS adquirido_por,
                        Fecha_Adquisicion       AS fecha_adquisicion,
                        Heartbeat               AS heartbeat,
                        CASE
                            WHEN ID_Corrida_Activa IS NULL THEN 'LIBRE'
                            WHEN Heartbeat IS NULL THEN 'VENCIDO'
                            WHEN DATEDIFF(SECOND, Heartbeat, GETDATE()) > :timeout_lock THEN 'VENCIDO'
                            ELSE 'ACTIVO'
                        END AS estado_lock,
                        CASE
                            WHEN Heartbeat IS NULL THEN NULL
                            ELSE DATEDIFF(SECOND, Heartbeat, GETDATE())
                        END AS segundos_desde_heartbeat
                    FROM Control.Bloqueo_Ejecucion
                    WHERE ID_Lock = 1
                """),
                {"timeout_lock": timeout_lock_seg},
            ).fetchone()
            if not fila:
                raise ErrorRecursoNoEncontrado()
            return dict(fila._mapping)
    except SQLAlchemyError:
        log.exception("Error al consultar estado del lock")
        raise ErrorBaseDatos()
