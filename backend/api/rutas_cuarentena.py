"""
api/rutas_cuarentena.py
========================
Router /api/v1/cuarentena — MDM Cuarentena

Seguridad:
  - GET   /           → viewer+
  - PATCH /resolver   → analista_mdm+
  - PATCH /rechazar   → analista_mdm+

Contratos v2:
  - analista se extrae del token JWT (no del body)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from nucleo.auth import UsuarioActual, obtener_usuario_actual, require_rol
from nucleo.http_utils import obtener_ip_cliente, obtener_request_id
from schemas.cuarentena.peticion import PeticionRechazarCuarentena, PeticionResolverCuarentena
from schemas.cuarentena.respuesta import (
    RespuestaAccionCuarentena,
    RespuestaCuarentena,
    RespuestaPaginada,
    RespuestaResumenCuarentena,
)
from servicios.servicio_auth import registrar_accion
from servicios.servicio_cuarentena import (
    listar_cuarentena,
    obtener_resumen_cuarentena,
    rechazar_registro,
    resolver_registro,
)

enrutador_cuarentena = APIRouter(prefix="/v1/cuarentena", tags=["Cuarentena"])


@enrutador_cuarentena.get(
    "/resumen",
    response_model=RespuestaResumenCuarentena,
    summary="Resumen de registros en cuarentena por estado",
    description="Devuelve conteos agregados (total, pendientes, resueltos, descartados) con una sola query SQL.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def resumen() -> RespuestaResumenCuarentena:
    datos = await obtener_resumen_cuarentena()
    # El repo retorna claves en mayúsculas ({PENDIENTE, RESUELTO, DESCARTADO, TOTAL});
    # el schema usa nombres en minúsculas.
    return RespuestaResumenCuarentena(
        total=datos.get("TOTAL", 0),
        pendientes=datos.get("PENDIENTE", 0),
        resueltos=datos.get("RESUELTO", 0),
        descartados=datos.get("DESCARTADO", 0),
    )


@enrutador_cuarentena.get(
    "",
    response_model=RespuestaPaginada,
    summary="Lista registros en cuarentena",
    description=(
        "Lista registros pendientes desde MDM.Cuarentena. "
        "Soporta filtro por tabla origen y paginación server-side."
    ),
    dependencies=[Depends(require_rol("viewer"))],
)
async def listar(
    pagina:       int = Query(default=1,  ge=1,        description="Número de página."),
    tamano:       int = Query(default=20, ge=1, le=10000, description="Registros por página."),
    tabla_filtro: str | None = Query(default=None,      description="Filtrar por tabla Bronce."),
    estado_filtro: str | None = Query(default="PENDIENTE", description="Filtro de estado, ej. PENDIENTE, RESUELTO, o vacío para todos."),
) -> RespuestaPaginada:
    # Si manda "all" o vacío, buscamos todos
    estado_f = None if not estado_filtro or estado_filtro.lower() == "all" else estado_filtro.upper()
    resultado = await listar_cuarentena(pagina=pagina, tamano=tamano, tabla_filtro=tabla_filtro, estado_filtro=estado_f)
    return RespuestaPaginada(
        total=resultado["total"],
        pagina=resultado["pagina"],
        tamano=resultado["tamano"],
        datos=[RespuestaCuarentena(**r) for r in resultado["datos"]],
    )


@enrutador_cuarentena.patch(
    "/{tabla_origen}/{id_registro}/resolver",
    response_model=RespuestaAccionCuarentena,
    summary="Resuelve un registro de cuarentena",
    description="Marca el registro como RESUELTO con el valor canónico. Requiere rol **analista_mdm**.",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def resolver(
    tabla_origen: str,
    id_registro:  str,
    cuerpo:       PeticionResolverCuarentena,
    request:      Request,
    usuario:      Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> RespuestaAccionCuarentena:
    resultado = await resolver_registro(
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico=cuerpo.valor_canonico,
        analista=usuario.nombre_usuario,
        comentario=cuerpo.comentario,
    )
    await registrar_accion(
        nombre_usuario=usuario.nombre_usuario,
        accion="RESOLVER_CUARENTENA",
        endpoint=str(request.url),
        request_id=obtener_request_id(request),
        ip_origen=obtener_ip_cliente(request),
        detalle=f"tabla={tabla_origen} id={id_registro}",
    )
    return RespuestaAccionCuarentena(**resultado)


@enrutador_cuarentena.patch(
    "/{tabla_origen}/{id_registro}/rechazar",
    response_model=RespuestaAccionCuarentena,
    summary="Rechaza un registro de cuarentena",
    description="Marca el registro como DESCARTADO. Requiere rol **analista_mdm**.",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def rechazar(
    tabla_origen: str,
    id_registro:  str,
    cuerpo:       PeticionRechazarCuarentena,
    request:      Request,
    usuario:      Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> RespuestaAccionCuarentena:
    resultado = await rechazar_registro(
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        motivo=cuerpo.motivo,
        analista=usuario.nombre_usuario,
    )
    await registrar_accion(
        nombre_usuario=usuario.nombre_usuario,
        accion="RECHAZAR_CUARENTENA",
        endpoint=str(request.url),
        request_id=obtener_request_id(request),
        ip_origen=obtener_ip_cliente(request),
        detalle=f"tabla={tabla_origen} id={id_registro}",
    )
    return RespuestaAccionCuarentena(**resultado)
