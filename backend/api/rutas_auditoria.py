"""
api/rutas_auditoria.py
=======================
Router /api/v1/auditoria — Bitácora ETL de solo lectura.

Endpoints:
    GET /v1/auditoria/log-carga             Historial plano (legacy, lista TOP N)
    GET /v1/auditoria/log-carga/{tabla}     Último estado de una tabla (legacy)
    GET /v1/auditoria/bitacora              Listado paginado con filtros (v2)
    GET /v1/auditoria/bitacora/{id_log}     Detalle individual por ID
    GET /v1/auditoria/bitacora/resumen      KPIs agregados por ventana

Seguridad: viewer+ en todos los endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from nucleo.auth import require_rol
from nucleo.excepciones import ErrorRecursoNoEncontrado
from schemas.auditoria.respuesta import (
    RespuestaBitacoraPagina,
    RespuestaLogCarga,
    RespuestaResumenBitacora,
    RespuestaUltimoEstado,
)
from servicios.servicio_auditoria import (
    obtener_detalle_log,
    obtener_historial,
    obtener_pagina_bitacora,
    obtener_resumen_bitacora,
    obtener_ultimo_estado_tabla,
)

enrutador_auditoria = APIRouter(prefix="/v1/auditoria", tags=["Auditoría"])

_ESTADOS_VALIDOS = {"OK", "ERROR", "EN_PROCESO", "SKIPPED", "TIMEOUT"}


# ── Legacy (consumido por portal Streamlit) ───────────────────────────────────

@enrutador_auditoria.get(
    "/log-carga",
    response_model=list[RespuestaLogCarga],
    summary="Historial de cargas ETL (legacy)",
    description="Lista TOP N registros ordenados por fecha desc. Para paginación con filtros, usar /bitacora.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def listar_log_carga(
    limite: Annotated[int, Query(ge=1, le=500, description="Máximo de registros a retornar.")] = 50,
) -> list[RespuestaLogCarga]:
    registros = await obtener_historial(limite=limite)
    return [RespuestaLogCarga(**r) for r in registros]


@enrutador_auditoria.get(
    "/log-carga/{tabla_destino}",
    response_model=RespuestaUltimoEstado,
    summary="Último estado de una tabla (legacy)",
    description="Retorna la última entrada de Auditoria.Log_Carga para una tabla específica.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def ultimo_estado(tabla_destino: str) -> RespuestaUltimoEstado:
    datos = await obtener_ultimo_estado_tabla(tabla_destino)
    if datos is None:
        raise ErrorRecursoNoEncontrado(f"Tabla '{tabla_destino}'")
    return RespuestaUltimoEstado(**datos)


# ── Bitácora v2 (consumida por portal Next.js) ─────────────────────────────────

@enrutador_auditoria.get(
    "/bitacora",
    response_model=RespuestaBitacoraPagina,
    summary="Bitácora paginada con filtros",
    description=(
        "Listado paginado de Auditoria.Log_Carga con filtros server-side: "
        "estado (multi), tabla_destino (LIKE), rango de fechas, id_corrida."
    ),
    dependencies=[Depends(require_rol("viewer"))],
)
async def listar_bitacora(
    pagina:        Annotated[int, Query(ge=1,   description="Página (1-indexed).")] = 1,
    tamano:        Annotated[int, Query(ge=1, le=200, description="Filas por página.")] = 50,
    estado:        Annotated[list[str] | None, Query(description="Uno o varios estados (OK, ERROR, EN_PROCESO, …).")] = None,
    tabla_destino: Annotated[str | None,  Query(description="Subcadena del nombre de tabla (LIKE).", max_length=120)] = None,
    desde:         Annotated[datetime | None, Query(description="Fecha de inicio inclusiva (ISO 8601).")] = None,
    hasta:         Annotated[datetime | None, Query(description="Fecha de inicio inclusiva límite (ISO 8601).")] = None,
    id_corrida:    Annotated[str | None,  Query(description="UUID de corrida (Control.Corrida).", max_length=36)] = None,
) -> RespuestaBitacoraPagina:
    estados_validos = (
        [e for e in estado if e in _ESTADOS_VALIDOS] if estado else None
    )
    datos = await obtener_pagina_bitacora(
        pagina=pagina,
        tamano=tamano,
        estado=estados_validos,
        tabla_destino=tabla_destino,
        desde=desde,
        hasta=hasta,
        id_corrida=id_corrida,
    )
    return RespuestaBitacoraPagina(
        items=[RespuestaLogCarga(**r) for r in datos["items"]],
        total=datos["total"],
        pagina=datos["pagina"],
        tamano=datos["tamano"],
    )


@enrutador_auditoria.get(
    "/bitacora/resumen",
    response_model=RespuestaResumenBitacora,
    summary="KPIs agregados de bitácora por ventana",
    description="Total, OK, errores, en_proceso, filas y tasa de éxito para los últimos N días.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def resumen_bitacora(
    ventana_dias: Annotated[int, Query(ge=1, le=365, description="Ventana en días (1=hoy, 7=7d, 30=30d).")] = 7,
) -> RespuestaResumenBitacora:
    datos = await obtener_resumen_bitacora(ventana_dias)
    return RespuestaResumenBitacora(**datos)


@enrutador_auditoria.get(
    "/bitacora/{id_log}",
    response_model=RespuestaLogCarga,
    summary="Detalle de una entrada de bitácora",
    description="Retorna el registro completo (incluye mensaje_error sin truncar) de un ID_Log_Carga.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def detalle_log(id_log: int) -> RespuestaLogCarga:
    datos = await obtener_detalle_log(id_log)
    if datos is None:
        raise ErrorRecursoNoEncontrado(f"Log_Carga ID={id_log}")
    return RespuestaLogCarga(**datos)
