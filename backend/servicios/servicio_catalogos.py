"""
servicios/servicio_catalogos.py
===============================
Lógica de consulta de catálogos MDM y Silver.
Todos los métodos son async — delegan I/O a asyncio.to_thread para no
bloquear el event loop de FastAPI mientras el repositorio consulta SQL Server.
"""

from __future__ import annotations

import asyncio

from nucleo.cache import cache
from nucleo.logging import obtener_logger
import repositorios.repo_catalogos as repo

log = obtener_logger(__name__)

_TTL_CATALOGOS = 3600   # 1 hora — datos de dimensiones estáticas


async def _con_cache(clave: str, ttl: int, fn, *args, **kwargs):
    """
    Helper async: intenta caché (sync, rápido) antes de ir a la BD.
    La consulta SQL se ejecuta en threadpool para no bloquear el event loop.
    """
    cached = await asyncio.to_thread(cache.obtener, clave)
    if cached is not None:
        log.debug("Cache hit catálogos", extra={"clave": clave})
        return cached
    resultado = await asyncio.to_thread(fn, *args, **kwargs)
    await asyncio.to_thread(cache.guardar, clave, resultado, ttl)
    return resultado


async def listar_variedades(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee MDM.Catalogo_Variedades (catálogo maestro MDM)."""
    return await _con_cache(
        f"variedades:{pagina}:{tamano}",
        _TTL_CATALOGOS,
        repo.listar_variedades,
        pagina=pagina,
        tamano=tamano,
    )


async def listar_dim_variedades(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Variedad (dimensión DWH ya homologada)."""
    return await _con_cache(
        f"dim_variedades:{pagina}:{tamano}",
        _TTL_CATALOGOS,
        repo.listar_dim_variedades,
        pagina=pagina,
        tamano=tamano,
    )


async def crear_dim_variedad(nombre_variedad: str, breeder: str | None) -> dict:
    """
    Crea una nueva variedad en Silver.Dim_Variedad.
    Propaga ValueError si el nombre ya existe.
    Invalida caché de variedades post-creación.
    """
    resultado = await asyncio.to_thread(
        repo.insertar_dim_variedad,
        nombre_variedad=nombre_variedad,
        breeder=breeder,
    )
    await asyncio.to_thread(cache.limpiar_todo)
    return resultado


async def cambiar_estado_dim_variedad(id_variedad: int, es_activa: bool) -> dict:
    """
    Activa o desactiva (soft-delete) una variedad en Silver.Dim_Variedad.
    Propaga ValueError si el ID no existe.
    """
    resultado = await asyncio.to_thread(
        repo.cambiar_estado_dim_variedad,
        id_variedad=id_variedad,
        es_activa=es_activa,
    )
    await asyncio.to_thread(cache.limpiar_todo)
    return resultado


async def listar_geografia(
    pagina: int = 1,
    tamano: int = 50,
    texto: str | None = None,
    fundo: str | None = None,
    sector: str | None = None,
) -> dict:
    """
    Lee Silver.Dim_Geografia vigente con paginación y filtros server-side.

    La caché está indexada por la combinación completa de filtros — cada
    filtro distinto se cachea por separado. Como la dimensión es estática
    (cambia mensualmente), TTL de 1h es seguro.
    """
    clave = f"geografia:{pagina}:{tamano}:{texto or ''}:{fundo or ''}:{sector or ''}"
    return await _con_cache(
        clave,
        _TTL_CATALOGOS,
        repo.listar_geografia,
        pagina=pagina,
        tamano=tamano,
        texto=texto,
        fundo=fundo,
        sector=sector,
    )


async def listar_personal(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Personal con paginación server-side."""
    return await _con_cache(
        f"personal:{pagina}:{tamano}",
        _TTL_CATALOGOS,
        repo.listar_personal,
        pagina=pagina,
        tamano=tamano,
    )
