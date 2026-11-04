"""
repositorios/repo_alertas.py
=============================
Consultas/mutaciones sobre MDM.Alerta_Ack (Ack persistente de alertas).

Las alertas en sí se derivan dinámicamente en el portal (proxy
`/api/cc/alerts`) combinando corridas con error + resumen de cuarentena.
Esta tabla solo persiste el estado "atendida" por ID_Alerta.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


def listar_acks() -> list[dict]:
    """
    Retorna todas las alertas atendidas con sus metadatos.
    Útil para hidratar el listado y mostrar 'atendida por X el dd/mm'.
    """
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text("""
                    SELECT
                        ID_Alerta   AS id_alerta,
                        Usuario_DNI AS usuario_dni,
                        Fecha_Ack   AS fecha_ack,
                        Comentario  AS comentario
                    FROM MDM.Alerta_Ack WITH (NOLOCK)
                    ORDER BY Fecha_Ack DESC
                """)
            ).fetchall()
            return [dict(f._mapping) for f in filas]
    except SQLAlchemyError:
        log.exception("Error al listar acks de alertas")
        raise ErrorBaseDatos()


def marcar_ack(id_alerta: str, usuario_dni: str, comentario: str | None) -> dict:
    """
    Upsert: si la alerta ya estaba acked, actualiza usuario/fecha/comentario.
    Retorna el registro resultante.
    """
    ahora = datetime.utcnow()
    try:
        with obtener_engine().begin() as con:
            # MERGE para upsert atómico
            con.execute(
                text("""
                    MERGE MDM.Alerta_Ack WITH (HOLDLOCK) AS objetivo
                    USING (SELECT :id AS ID_Alerta) AS origen
                       ON objetivo.ID_Alerta = origen.ID_Alerta
                    WHEN MATCHED THEN UPDATE SET
                        Usuario_DNI = :usuario,
                        Fecha_Ack   = :fecha,
                        Comentario  = :comentario
                    WHEN NOT MATCHED THEN INSERT (ID_Alerta, Usuario_DNI, Fecha_Ack, Comentario)
                        VALUES (:id, :usuario, :fecha, :comentario);
                """),
                {
                    "id":         id_alerta,
                    "usuario":    usuario_dni,
                    "fecha":      ahora,
                    "comentario": comentario,
                },
            )
            return {
                "id_alerta":   id_alerta,
                "usuario_dni": usuario_dni,
                "fecha_ack":   ahora,
                "comentario":  comentario,
            }
    except SQLAlchemyError:
        log.exception("Error al marcar ack", extra={"id_alerta": id_alerta})
        raise ErrorBaseDatos()


def desmarcar_ack(id_alerta: str) -> bool:
    """
    Borra el ack. Retorna True si existía y se borró, False si no había nada.
    """
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("DELETE FROM MDM.Alerta_Ack WHERE ID_Alerta = :id"),
                {"id": id_alerta},
            )
            return resultado.rowcount > 0
    except SQLAlchemyError:
        log.exception("Error al desmarcar ack", extra={"id_alerta": id_alerta})
        raise ErrorBaseDatos()
