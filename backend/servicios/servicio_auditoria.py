"""
servicios/servicio_auditoria.py
================================
Lógica de consulta de auditoría.
Todos los métodos son async — I/O delegado a asyncio.to_thread.
Los listeners de EventBus se registran desde main.py en lifespan.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import repositorios.repo_auditoria as repo


async def obtener_historial(limite: int = 50) -> list[dict]:
    """Retorna las últimas N corridas registradas en Auditoria.Log_Carga (legacy)."""
    return await asyncio.to_thread(repo.listar_corridas, limite=limite)


async def obtener_ultimo_estado_tabla(tabla_destino: str) -> dict | None:
    """Retorna el último estado de carga para una tabla específica."""
    return await asyncio.to_thread(repo.ultimo_estado_tabla, tabla_destino)


async def obtener_pagina_bitacora(
    pagina: int,
    tamano: int,
    estado: list[str] | None,
    tabla_destino: str | None,
    desde: datetime | None,
    hasta: datetime | None,
    id_corrida: str | None,
) -> dict:
    """Lista paginada + COUNT en paralelo bajo los mismos filtros."""
    items_task = asyncio.to_thread(
        repo.listar_bitacora,
        pagina=pagina,
        tamano=tamano,
        estado=estado,
        tabla_destino=tabla_destino,
        desde=desde,
        hasta=hasta,
        id_corrida=id_corrida,
    )
    total_task = asyncio.to_thread(
        repo.contar_bitacora,
        estado=estado,
        tabla_destino=tabla_destino,
        desde=desde,
        hasta=hasta,
        id_corrida=id_corrida,
    )
    items, total = await asyncio.gather(items_task, total_task)
    return {"items": items, "total": total, "pagina": pagina, "tamano": tamano}


async def obtener_detalle_log(id_log: int) -> dict | None:
    """Detalle individual de una entrada Log_Carga."""
    return await asyncio.to_thread(repo.obtener_detalle_log, id_log)


async def obtener_resumen_bitacora(ventana_dias: int) -> dict:
    """KPIs agregados de la ventana."""
    return await asyncio.to_thread(repo.resumen_bitacora, ventana_dias)
