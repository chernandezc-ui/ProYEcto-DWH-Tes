"""
repositorios/repo_comandos.py
=============================
Cola de comandos asíncronos para el runner ETL (Control.Comando_Ejecucion).
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

TipoComando    = Literal["INICIAR", "CANCELAR", "REINTENTAR"]
EstadoComando  = Literal["PENDIENTE", "PROCESANDO", "PROCESADO", "ERROR_COLA"]

def encolar_comando(
    id_corrida: str,
    iniciado_por: str,
    tipo_comando: TipoComando = "INICIAR",
    comentario: str | None = None,
    max_reintentos: int = 0,
    timeout_seg: int = 3600,
) -> int:
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("""
                    INSERT INTO Control.Comando_Ejecucion
                        (ID_Corrida, Tipo_Comando, Iniciado_Por, Comentario,
                         Max_Reintentos, Timeout_Seg, Estado_Cmd, Fecha_Comando)
                    OUTPUT INSERTED.ID_Comando
                    VALUES
                        (:corrida, :tipo, :usuario, :comentario,
                         :max_ret, :timeout, 'PENDIENTE', :ahora)
                """),
                {
                    "corrida":    id_corrida,
                    "tipo":       tipo_comando,
                    "usuario":    iniciado_por,
                    "comentario": comentario,
                    "max_ret":    max_reintentos,
                    "timeout":    timeout_seg,
                    "ahora":      datetime.now(tz=timezone.utc),
                },
            )
            return resultado.fetchone()[0]
    except SQLAlchemyError:
        log.exception("Error al encolar comando")
        raise ErrorBaseDatos()

def tomar_comando_pendiente() -> dict | None:
    try:
        with obtener_engine().begin() as con:
            fila = con.execute(
                text("""
                    -- Patrón "queue table" de SQL Server:
                    -- UPDLOCK   → adquiere lock de escritura en la fila seleccionada (evita doble-pick)
                    -- READPAST  → salta filas ya locked (otros runners toman comandos distintos)
                    -- ROWLOCK   → scope mínimo (no table/page lock)
                    --
                    -- Índice recomendado para evitar contención en alta concurrencia:
                    -- CREATE INDEX IX_Comando_Estado_Fecha
                    --     ON Control.Comando_Ejecucion (Estado_Cmd, Fecha_Solicitud ASC)
                    --     WHERE Estado_Cmd = 'PENDIENTE';
                    ;WITH siguiente AS (
                        SELECT TOP (1)
                            ID_Comando
                        FROM Control.Comando_Ejecucion WITH (UPDLOCK, READPAST, ROWLOCK)
                        WHERE Estado_Cmd = 'PENDIENTE'
                          AND Tipo_Comando IN ('INICIAR', 'REINTENTAR')
                        ORDER BY Fecha_Comando ASC, ID_Comando ASC
                    )
                    UPDATE ce
                    SET Estado_Cmd = 'PROCESANDO', Fecha_Proceso = GETDATE()
                    OUTPUT
                        INSERTED.ID_Comando,
                        INSERTED.ID_Corrida,
                        INSERTED.Tipo_Comando,
                        INSERTED.Iniciado_Por,
                        INSERTED.Comentario,
                        INSERTED.Max_Reintentos,
                        INSERTED.Timeout_Seg
                    FROM Control.Comando_Ejecucion ce
                    INNER JOIN siguiente
                        ON siguiente.ID_Comando = ce.ID_Comando
                """)
            ).fetchone()
            return dict(fila._mapping) if fila else None
    except SQLAlchemyError:
        log.exception("Error al tomar comando pendiente")
        return None

def marcar_comando(id_comando: int, estado: EstadoComando, mensaje: str | None = None) -> None:
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    UPDATE Control.Comando_Ejecucion
                    SET Estado_Cmd = :estado, Mensaje_Error = :msg
                    WHERE ID_Comando = :id
                """),
                {"estado": estado, "msg": mensaje, "id": id_comando},
            )
    except SQLAlchemyError:
        log.warning("No se pudo marcar comando", extra={"id_comando": id_comando})
