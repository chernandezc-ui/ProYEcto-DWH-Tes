"""
api/rutas_config.py
====================
Router /api/v1/config — Reglas de validación y parámetros del pipeline.

Seguridad: analista_mdm+ (nivel 20). admin (40) pasa automáticamente.
"""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request
from nucleo.auth import UsuarioActual, require_rol, obtener_usuario_actual
from nucleo.http_utils import obtener_ip_cliente, obtener_request_id
from nucleo.excepciones import ErrorRecursoNoEncontrado
from schemas.config.respuesta import (
    RespuestaPaginadaParametros,
    RespuestaPaginadaReglas,
)
from schemas.config.peticion import SolicitudActualizarParametro, SolicitudBatchParametros
import servicios.servicio_config as servicio

enrutador_config = APIRouter(prefix="/v1/config", tags=["Configuración"])


@enrutador_config.get(
    "/reglas",
    response_model=RespuestaPaginadaReglas,
    summary="Lista reglas de validación",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def obtener_reglas(
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=15, ge=1, le=10000),
) -> RespuestaPaginadaReglas:
    resultado = await servicio.listar_reglas(pagina=pagina, tamano=tamano)
    return RespuestaPaginadaReglas(**resultado)


@enrutador_config.get(
    "/parametros",
    response_model=RespuestaPaginadaParametros,
    summary="Lista parámetros del pipeline",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def obtener_parametros(
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=10, ge=1, le=10000),
) -> RespuestaPaginadaParametros:
    resultado = await servicio.listar_parametros(pagina=pagina, tamano=tamano)
    return RespuestaPaginadaParametros(**resultado)


@enrutador_config.patch(
    "/parametros",
    summary="Actualiza múltiples parámetros del pipeline",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def actualizar_parametros_batch(
    peticion: SolicitudBatchParametros,
    request: Request,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
):
    exitos = 0
    fallos = []
    
    for p in peticion.parametros:
        exito = await servicio.actualizar_parametro(
            nombre=p.nombre_parametro,
            valor=p.valor,
            usuario=usuario.nombre_usuario,
            endpoint=str(request.url),
            request_id=obtener_request_id(request),
            ip_origen=obtener_ip_cliente(request)
        )
        if exito:
            exitos += 1
        else:
            fallos.append(p.nombre_parametro)
    
    return {
        "mensaje": f"Proceso finalizado. Exitos: {exitos}, Fallos: {len(fallos)}",
        "fallos": fallos
    }


@enrutador_config.patch(
    "/parametros/{nombre}",
    summary="Actualiza un solo parámetro del pipeline",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def actualizar_parametro(
    nombre: str,
    peticion: SolicitudActualizarParametro,
    request: Request,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
):
    exito = await servicio.actualizar_parametro(
        nombre=nombre,
        valor=peticion.valor,
        usuario=usuario.nombre_usuario,
        endpoint=str(request.url),
        request_id=obtener_request_id(request),
        ip_origen=obtener_ip_cliente(request)
    )
    
    if not exito:
        raise ErrorRecursoNoEncontrado(f"Parámetro '{nombre}'")
        
    return {"mensaje": f"Parámetro '{nombre}' actualizado con éxito"}
