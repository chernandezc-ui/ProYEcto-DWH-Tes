"""
repositorios/repo_log_acceso.py
================================
SQL de escritura hacia Auditoria.Log_Acceso.

Todos los métodos fallan silenciosamente — la auditoría de acceso
nunca debe bloquear el flujo principal de la aplicación.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


def registrar_acceso(
    nombre_usuario: str,
    accion: str,
    resultado: str,
    endpoint: str | None = None,
    request_id: str | None = None,
    ip_origen: str | None = None,
    detalle: str | None = None,
) -> None:
    """
    Inserta un registro en Auditoria.Log_Acceso.
    Falla silenciosamente — nunca propaga excepciones.

    resultado: 'OK' | 'DENEGADO' | 'ERROR'
    """
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    INSERT INTO Auditoria.Log_Acceso
                        (Nombre_Usuario, Accion, Endpoint, Request_ID,
                         IP_Origen, Resultado, Detalle, Fecha_Accion)
                    VALUES
                        (:usuario, :accion, :endpoint, :request_id,
                         :ip, :resultado, :detalle, :fecha)
                """),
                {
                    "usuario":    nombre_usuario,
                    "accion":     accion[:200],
                    "endpoint":   (endpoint or "")[:300],
                    "request_id": (request_id or "")[:50],
                    "ip":         (ip_origen or "")[:50],
                    "resultado":  resultado[:20],
                    "detalle":    (detalle or "")[:500],
                    "fecha":      datetime.now(),
                },
            )
    except SQLAlchemyError:
        log.warning(
            "No se pudo registrar acceso en auditoría",
            extra={"usuario": nombre_usuario, "accion": accion},
        )
