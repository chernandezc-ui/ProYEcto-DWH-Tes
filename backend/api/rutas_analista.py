"""
api/rutas_analista.py
======================
Router /api/v1/analista — Endpoints del portal analista.

Endpoints:
    GET   /v1/analista/vistas         Catálogo de vistas DWH disponibles
    POST  /v1/analista/widget         Genera figura Plotly desde config
    GET   /v1/analista/notificaciones Lista paginada de notificaciones
    GET   /v1/analista/home           Workspace guardado del analista
    PATCH /v1/analista/home           Persiste workspace del analista

Seguridad: analista_mdm+
"""
from __future__ import annotations

import asyncio
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from nucleo.auth import obtener_usuario_actual, require_rol
from schemas.analista.modelos import (
    ConfigWidget, RespuestaWidget, InfoVista, RespuestaNotificaciones,
)
from servicios.servicio_analista_charts import generar_figura, listar_vistas
from servicios.servicio_analista_notificaciones import obtener_notificaciones
import repositorios.repo_proyecciones as repo_proy

enrutador_analista = APIRouter(prefix="/v1/analista", tags=["Analista"])

_AUTH = [Depends(require_rol("analista_mdm"))]


@enrutador_analista.get(
    "/vistas",
    response_model=list[InfoVista],
    dependencies=_AUTH,
    summary="Catálogo de vistas DWH",
)
async def get_vistas() -> list[InfoVista]:
    return listar_vistas()


@enrutador_analista.post(
    "/widget",
    response_model=RespuestaWidget,
    dependencies=_AUTH,
    summary="Genera figura Plotly para un widget",
)
async def post_widget(config: ConfigWidget) -> RespuestaWidget:
    try:
        return await generar_figura(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generando widget: {exc}") from exc


@enrutador_analista.get(
    "/notificaciones",
    response_model=RespuestaNotificaciones,
    dependencies=_AUTH,
    summary="Notificaciones del analista",
)
async def get_notificaciones(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    severidad: Optional[str] = Query(default=None),
) -> RespuestaNotificaciones:
    return await obtener_notificaciones(
        page=page,
        page_size=page_size,
        severidad=severidad,
    )


@enrutador_analista.get(
    "/home",
    dependencies=_AUTH,
    summary="Workspace guardado del analista",
)
async def get_home(
    usuario=Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    clave = f"ANALISTA_HOME_{usuario.nombre_usuario}"
    data = await asyncio.to_thread(repo_proy.leer_param_json, clave)
    if data is None:
        return {"widgets": [], "savedAt": None}
    return data


@enrutador_analista.patch(
    "/home",
    dependencies=_AUTH,
    summary="Persiste workspace del analista",
)
async def patch_home(
    body: dict[str, Any],
    usuario=Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    clave = f"ANALISTA_HOME_{usuario.nombre_usuario}"
    ok = await asyncio.to_thread(
        repo_proy.guardar_param_json,
        clave,
        body,
        f"Workspace analista {usuario.nombre_usuario}",
        "analista_home",
    )
    return {"ok": ok, "savedAt": body.get("savedAt")}
