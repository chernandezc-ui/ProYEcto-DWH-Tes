"""
servicios/servicio_config.py
============================
Servicio para la gestión de reglas de validación y parámetros del pipeline.
Centraliza la auditoría y el acceso a repositorios de configuración.
"""

from __future__ import annotations

import asyncio

from nucleo.logging import obtener_logger
from servicios.servicio_auth import registrar_accion
import repositorios.repo_config as repo

log = obtener_logger(__name__)


async def listar_reglas(pagina: int = 1, tamano: int = 20) -> dict:
    """Lista reglas de validación configuradas."""
    return await asyncio.to_thread(repo.listar_reglas, pagina=pagina, tamano=tamano)


async def listar_parametros(pagina: int = 1, tamano: int = 20) -> dict:
    """Lista parámetros técnicos del pipeline."""
    return await asyncio.to_thread(repo.listar_parametros, pagina=pagina, tamano=tamano)


async def actualizar_parametro(
    nombre: str,
    valor: str,
    usuario: str,
    endpoint: str,
    request_id: str | None = None,
    ip_origen: str | None = None,
) -> bool:
    """
    Actualiza un parámetro y registra la acción en la bitácora de auditoría.
    """
    exito = await asyncio.to_thread(
        repo.actualizar_parametro,
        nombre=nombre,
        valor=valor,
        modificado_por=usuario
    )
    
    if exito:
        await registrar_accion(
            nombre_usuario=usuario,
            accion="ACTUALIZAR_PARAMETRO",
            endpoint=endpoint,
            request_id=request_id,
            ip_origen=ip_origen,
            detalle=f"parametro={nombre} nuevo_valor={valor}"
        )
        log.info(
            "Parámetro de configuración actualizado",
            extra={"parametro": nombre, "usuario": usuario}
        )
    
    return exito
