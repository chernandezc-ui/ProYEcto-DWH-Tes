"""
api/rutas_reinyeccion.py
=========================
Router /api/v1/reinyeccion — Herramienta de Reinyección MDM

Permite al analista MDM re-encolar en Bronce los registros que ya
fueron resueltos en Cuarentena, para que el pipeline los vuelva a
procesar sin necesidad de subir archivos nuevamente.

Seguridad:
  - GET  /candidatos  → analista_mdm+  (ver cuántos hay listos)
  - POST /ejecutar    → analista_mdm+  (lanzar la reinyección)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from nucleo.auth import UsuarioActual, obtener_usuario_actual, require_rol
from schemas.reinyeccion.respuesta import RespuestaConteoReinyeccion, RespuestaReinyeccion
from servicios.servicio_auth import registrar_accion
from servicios.servicio_reinyeccion import contar_candidatos, ejecutar_reinyeccion

enrutador_reinyeccion = APIRouter(
    prefix="/v1/reinyeccion",
    tags=["Reinyección MDM"],
)


@enrutador_reinyeccion.get(
    "/candidatos",
    response_model=RespuestaConteoReinyeccion,
    summary="Cuenta registros listos para reinyectar",
    description=(
        "Retorna el número de registros RESUELTOS en MDM.Cuarentena que tienen "
        "un ID_Registro_Origen válido y serían candidatos a ser reinyectados en Bronce. "
        "Requiere rol **analista_mdm**."
    ),
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def obtener_candidatos(
    tabla: str | None = Query(default=None, description="Filtrar por tabla de origen (parcial)."),
) -> RespuestaConteoReinyeccion:
    total = await contar_candidatos(tabla_filtro=tabla)
    return RespuestaConteoReinyeccion(candidatos=total)


@enrutador_reinyeccion.post(
    "/ejecutar",
    response_model=RespuestaReinyeccion,
    summary="Ejecuta la reinyección masiva en Bronce",
    description=(
        "Toma todos los registros RESUELTOS en MDM.Cuarentena con ID_Registro_Origen válido "
        "y actualiza su Estado_Carga a 'CARGADO' en las tablas Bronce correspondientes. "
        "El pipeline ETL los reprocesará en la siguiente corrida. "
        "Requiere rol **analista_mdm**."
    ),
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def ejecutar(
    request: Request,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
    tabla: str | None = Query(default=None, description="Limitar a una tabla Bronce específica."),
) -> RespuestaReinyeccion:
    resultado = await ejecutar_reinyeccion(analista=usuario.nombre_usuario, tabla_filtro=tabla)

    await registrar_accion(
        nombre_usuario=usuario.nombre_usuario,
        accion="REINYECCION_MDM",
        endpoint=str(request.url),
        request_id=getattr(request.state, "request_id", None),
        detalle=(
            f"reinyectados={resultado['reinyectados']} "
            f"omitidos={resultado['omitidos']} "
            f"filtro={tabla or 'todas'}"
        ),
    )

    return RespuestaReinyeccion(
        reinyectados=resultado["reinyectados"],
        omitidos=resultado["omitidos"],
        detalle=resultado["detalle"],
    )
