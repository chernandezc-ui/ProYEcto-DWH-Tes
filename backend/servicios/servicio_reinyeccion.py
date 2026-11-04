"""
servicios/servicio_reinyeccion.py
==================================
Servicio de orquestación para la Herramienta de Reinyección MDM.
Todos los métodos son async — I/O delegado a asyncio.to_thread.
Emite señal mdm_reinyeccion al EventBus al completar.
"""

from __future__ import annotations

import asyncio

from nucleo.cache import cache
from nucleo.logging import obtener_logger
from servicios.event_bus import EventBus
import repositorios.repo_reinyeccion as repo
import repositorios.repo_auditoria as repo_auditoria

log = obtener_logger(__name__)


async def contar_candidatos(tabla_filtro: str | None = None) -> int:
    """Retorna cuántos registros RESUELTOS están disponibles para reinyectar."""
    return await asyncio.to_thread(
        repo.contar_candidatos_reinyeccion,
        tabla_filtro=tabla_filtro,
    )


async def ejecutar_reinyeccion(
    analista: str,
    tabla_filtro: str | None = None,
) -> dict:
    """
    Flujo completo de reinyección (no bloqueante):
    1. Obtiene candidatos RESUELTOS con ID_Registro_Origen válido.
    2. Actualiza Estado_Carga = 'CARGADO' en Bronce (masivo).
    3. Invalida caché global.
    4. Registra en auditoría MDM.
    5. Emite señal mdm_reinyeccion al EventBus.
    """
    log.info("Iniciando reinyección MDM", extra={"analista": analista, "filtro": tabla_filtro})

    candidatos = await asyncio.to_thread(
        repo.obtener_resueltos_pendientes,
        tabla_filtro=tabla_filtro,
    )

    if not candidatos:
        log.info("Sin candidatos para reinyección", extra={"analista": analista})
        return {
            "reinyectados": 0,
            "omitidos": 0,
            "detalle": ["ℹ️ No hay registros RESUELTOS con ID de origen válido para reinyectar."],
        }

    resultado = await asyncio.to_thread(repo.reinyectar_en_bronce, candidatos)

    await asyncio.to_thread(cache.limpiar_todo)

    try:
        await asyncio.to_thread(
            repo_auditoria.insertar_decision_mdm,
            tabla_origen="REINYECCION_MASIVA",
            id_registro="BATCH",
            valor_canonico="",
            decision="REINYECCION",
            analista=analista,
            comentario=(
                f"Reinyección masiva: {resultado['reinyectados']} registros reactivados, "
                f"{resultado['omitidos']} omitidos. Filtro: {tabla_filtro or 'todas las tablas'}."
            ),
        )
    except Exception:
        log.warning("No se pudo registrar auditoría de reinyección", exc_info=True)

    EventBus.mdm_reinyeccion.send(
        "servicio_reinyeccion",
        reinyectados=resultado["reinyectados"],
        omitidos=resultado["omitidos"],
        analista=analista,
        filtro=tabla_filtro,
    )
    log.info(
        "Reinyección completada",
        extra={
            "reinyectados": resultado["reinyectados"],
            "omitidos": resultado["omitidos"],
            "analista": analista,
        },
    )
    return resultado
