"""
nucleo/auditoria.py
===================
Wrapper de alto nivel hacia Auditoria.Log_Carga.
Delega todo el SQL a repositorios.repo_auditoria.

Este módulo existe por compatibilidad con servicio_etl.py — proporciona
la API pública que el pipeline runner usa para registrar corridas.
"""

from __future__ import annotations

import repositorios.repo_auditoria as _repo


def registrar_inicio_corrida(
    nombre_proceso: str,
    tabla_destino: str,
    nombre_archivo: str = "API_BACKEND",
) -> int | None:
    """Inserta inicio de corrida. Retorna id_log o None si falla."""
    return _repo.insertar_inicio_corrida(
        nombre_proceso=nombre_proceso,
        tabla_destino=tabla_destino,
        nombre_archivo=nombre_archivo,
    )


def registrar_fin_corrida(
    id_log: int,
    estado: str,
    filas_insertadas: int = 0,
    filas_rechazadas: int = 0,
    mensaje_error: str | None = None,
) -> None:
    """Actualiza fin de corrida. Falla silenciosamente."""
    _repo.actualizar_fin_corrida(
        id_log=id_log,
        estado=estado,
        filas_insertadas=filas_insertadas,
        filas_rechazadas=filas_rechazadas,
        mensaje_error=mensaje_error,
    )


def obtener_historial_corridas(
    limite: int = 50,
    tabla_destino: str | None = None,
) -> list[dict]:
    """Consulta historial de corridas en Auditoria.Log_Carga."""
    return _repo.listar_corridas(limite=limite, tabla_destino=tabla_destino)
