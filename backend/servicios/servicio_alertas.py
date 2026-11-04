"""
servicios/servicio_alertas.py
==============================
Capa de servicio para Ack persistente de alertas.

Las alertas se derivan en el portal; aquí solo persistimos el estado
"atendida" en MDM.Alerta_Ack y auditamos los cambios.
"""

from __future__ import annotations

import asyncio

import repositorios.repo_alertas as repo
import repositorios.repo_auditoria as repo_auditoria
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


async def obtener_acks() -> list[dict]:
    """Lista todos los acks persistidos."""
    return await asyncio.to_thread(repo.listar_acks)


async def marcar_ack(
    id_alerta: str,
    usuario_dni: str,
    comentario: str | None,
) -> dict:
    """Marca la alerta como atendida y registra en auditoría."""
    resultado = await asyncio.to_thread(
        repo.marcar_ack, id_alerta, usuario_dni, comentario,
    )
    await asyncio.to_thread(
        repo_auditoria.insertar_decision_mdm,
        tabla_origen="MDM.Alerta_Ack",
        id_registro=id_alerta,
        valor_canonico="ACK",
        decision="ACK_ALERTA",
        analista=usuario_dni,
        comentario=comentario or "",
    )
    log.info(
        "Alerta marcada como atendida",
        extra={"id_alerta": id_alerta, "usuario": usuario_dni},
    )
    return resultado


async def desmarcar_ack(id_alerta: str, usuario_dni: str) -> bool:
    """Borra el ack y registra reapertura en auditoría."""
    existia = await asyncio.to_thread(repo.desmarcar_ack, id_alerta)
    if existia:
        await asyncio.to_thread(
            repo_auditoria.insertar_decision_mdm,
            tabla_origen="MDM.Alerta_Ack",
            id_registro=id_alerta,
            valor_canonico="UNACK",
            decision="REABRIR_ALERTA",
            analista=usuario_dni,
            comentario="",
        )
        log.info(
            "Alerta reabierta",
            extra={"id_alerta": id_alerta, "usuario": usuario_dni},
        )
    return existia
