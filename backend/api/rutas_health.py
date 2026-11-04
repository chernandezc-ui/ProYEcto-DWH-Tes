"""
api/rutas_health.py
====================
Endpoints de salud del backend ACP Platform.

Semántica:
    GET /health        — estado completo: proceso + BD
    GET /health/live   — liveness: el proceso respira (sin BD)
    GET /health/ready  — readiness: listo para tráfico (verifica BD)

Esta separación permite a orquestadores (k8s, compose, nginx) diferenciar
entre un proceso vivo pero no listo (ej: BD caída) y un proceso caído.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from nucleo.auth import UsuarioActual, obtener_usuario_actual, require_rol
from nucleo.conexion import verificar_conexion
from nucleo.settings import settings
from repositorios.repo_corridas import obtener_resumen_control_plane
from repositorios.repo_locks import obtener_estado_lock
from repositorios.repo_calidad import obtener_resumen_calidad_hoy

enrutador_health = APIRouter(tags=["Sistema"])

_SERVICIO = settings.api_titulo
_VERSION  = settings.api_version


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _info_bd_publica(info: dict) -> dict:
    """Elimina version_sql del payload expuesto a clientes no autenticados."""
    return {k: v for k, v in info.items() if k != "version"}


def _diagnostico_control_plane() -> tuple[bool, dict]:
    try:
        resumen = obtener_resumen_control_plane()
        lock = obtener_estado_lock()
        return True, {
            "estado": "operativo",
            "resumen": resumen,
            "lock": lock,
        }
    except Exception as exc:
        return False, {
            "estado": "error",
            "error": str(exc),
        }


@enrutador_health.get("/health/live", summary="Liveness check")
def liveness() -> JSONResponse:
    """
    Liveness probe — el proceso HTTP está activo.
    Nunca contacta la base de datos.
    Siempre retorna 200 si el proceso responde.
    """
    return JSONResponse(
        status_code=200,
        content={
            "servicio":  _SERVICIO,
            "version":   _VERSION,
            "entorno":   settings.entorno,
            "estado":    "vivo",
            "timestamp": _timestamp(),
        },
    )


@enrutador_health.get("/health/ready", summary="Readiness check")
def readiness() -> JSONResponse:
    """
    Readiness probe — el proceso está listo para servir tráfico.
    Verifica la conectividad con SQL Server.
    Retorna 200 si la BD responde, 503 si no.
    """
    info_bd = verificar_conexion()
    listo   = info_bd.get("conectado", False)

    return JSONResponse(
        status_code=200 if listo else 503,
        content={
            "servicio":    _SERVICIO,
            "version":     _VERSION,
            "entorno":     settings.entorno,
            "estado":      "listo" if listo else "no_listo",
            "base_datos":  _info_bd_publica(info_bd),
            "timestamp":   _timestamp(),
        },
    )


@enrutador_health.get(
    "/health/ready/control",
    summary="Readiness del control-plane ETL",
    dependencies=[Depends(require_rol("viewer"))],
)
def readiness_control() -> JSONResponse:
    """
    Verifica que la BD responda y que el esquema Control.* sea accesible.
    """
    info_bd = verificar_conexion()
    bd_lista = info_bd.get("conectado", False)
    control_ok, control_plane = _diagnostico_control_plane() if bd_lista else (False, {
        "estado": "no_verificado",
        "error": "Base de datos no disponible",
    })
    listo = bd_lista and control_ok

    return JSONResponse(
        status_code=200 if listo else 503,
        content={
            "servicio": _SERVICIO,
            "version": _VERSION,
            "entorno": settings.entorno,
            "estado": "listo" if listo else "no_listo",
            "base_datos": _info_bd_publica(info_bd),
            "control_plane": control_plane,
            "timestamp": _timestamp(),
        },
    )


@enrutador_health.get("/health/ready/runner", summary="Readiness del runner ETL")
def readiness_runner() -> JSONResponse:
    """
    Verifica que el control-plane esté sano y que no exista un lock vencido.
    """
    info_bd = verificar_conexion()
    bd_lista = info_bd.get("conectado", False)
    control_ok, control_plane = _diagnostico_control_plane() if bd_lista else (False, {
        "estado": "no_verificado",
        "error": "Base de datos no disponible",
    })
    estado_lock = (control_plane.get("lock") or {}).get("estado_lock") if control_ok else None
    runner_sano = bd_lista and control_ok and estado_lock != "VENCIDO"

    if not bd_lista:
        estado = "no_listo"
    elif not control_ok:
        estado = "control_plane_error"
    elif estado_lock == "VENCIDO":
        estado = "lock_vencido"
    elif estado_lock == "ACTIVO":
        estado = "ocupado"
    else:
        estado = "libre"

    return JSONResponse(
        status_code=200 if runner_sano else 503,
        content={
            "servicio": _SERVICIO,
            "version": _VERSION,
            "entorno": settings.entorno,
            "estado": estado,
            "base_datos": _info_bd_publica(info_bd),
            "control_plane": control_plane,
            "timestamp": _timestamp(),
        },
    )


@enrutador_health.get(
    "/health/lock",
    summary="Estado actual del lock del runner",
    dependencies=[Depends(require_rol("viewer"))],
)
def estado_lock() -> JSONResponse:
    """
    Expone el estado del lock del runner para diagnóstico operativo.
    """
    info_bd = verificar_conexion()
    bd_lista = info_bd.get("conectado", False)
    if not bd_lista:
        return JSONResponse(
            status_code=503,
            content={
                "servicio": _SERVICIO,
                "version": _VERSION,
                "entorno": settings.entorno,
                "estado": "no_listo",
                "base_datos": info_bd,
                "lock": None,
                "timestamp": _timestamp(),
            },
        )

    try:
        lock = obtener_estado_lock()
        return JSONResponse(
            status_code=200,
            content={
                "servicio": _SERVICIO,
                "version": _VERSION,
                "entorno": settings.entorno,
                "estado": lock.get("estado_lock", "DESCONOCIDO").lower(),
                "base_datos": info_bd,
                "lock": lock,
                "timestamp": _timestamp(),
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "servicio": _SERVICIO,
                "version": _VERSION,
                "entorno": settings.entorno,
                "estado": "error",
                "base_datos": info_bd,
                "lock": {"error": str(exc)},
                "timestamp": _timestamp(),
            },
        )


@enrutador_health.get("/health", summary="Estado completo del servicio")
def health() -> JSONResponse:
    """
    Health check completo: proceso + base de datos + metadatos.
    Útil para dashboards de monitoreo.
    """
    info_bd = verificar_conexion()
    listo   = info_bd.get("conectado", False)

    return JSONResponse(
        status_code=200,
        content={
            "servicio":    _SERVICIO,
            "version":     _VERSION,
            "entorno":     settings.entorno,
            "estado":      "activo" if listo else "degradado",
            "base_datos":  _info_bd_publica(info_bd),
            "timestamp":   _timestamp(),
        },
    )

# ── GET /health/telemetria/stream (SSE) ─────────────────────────────────────────────

async def _generar_telemetria(request: Request, es_admin: bool) -> AsyncGenerator[dict, None]:
    """
    Generador SSE: emite métricas del sistema cada 3 segundos.
    Consumido por el dashboard SSR del portal (iframe EventSource).
    Emite JSON con: latencia_ms, corridas_activas, comandos_pendientes, timestamp.
    version_sql solo se incluye cuando es_admin=True (S-7).
    Máximo 1200 iteraciones (~1 hora) para liberar recursos.
    """
    import json
    for _ in range(1200):
        if await request.is_disconnected():
            return
        try:
            bd_info   = verificar_conexion()
            cp_resumen = {}
            try:
                cp_resumen = obtener_resumen_control_plane()
            except Exception:
                pass

            payload: dict = {
                "conectado":          bd_info.get("conectado", False),
                "latencia_ms":        bd_info.get("latencia_ms", None),
                "corridas_activas":   cp_resumen.get("corridas_activas", 0),
                "comandos_pendientes":cp_resumen.get("comandos_pendientes", 0),
                "comandos_procesando":cp_resumen.get("comandos_procesando", 0),
                "timestamp":          datetime.now(tz=timezone.utc).isoformat(),
            }
            if es_admin:
                payload["version_sql"] = bd_info.get("version", "—")
            yield {"event": "telemetria", "data": json.dumps(payload)}
        except Exception as exc:
            yield {"event": "error", "data": f'{{"error": "{exc}"}}'}

        await asyncio.sleep(3)


@enrutador_health.get(
    "/health/telemetria/stream",
    summary="Stream SSE de telemetría del sistema",
    description=(
        "Abre un canal SSE que emite métricas del sistema cada 3 segundos: "
        "latencia de BD, corridas activas, comandos en cola y timestamp. "
        "Consume desde el browser vía EventSource para dashboards SSR. "
        "Requiere autenticación Bearer con rol viewer o superior."
    ),
    dependencies=[Depends(require_rol("viewer"))],
)
async def stream_telemetria(
    request: Request,
    usuario: UsuarioActual = Depends(obtener_usuario_actual),
) -> EventSourceResponse:
    return EventSourceResponse(_generar_telemetria(request, es_admin=usuario.tiene_rol("admin")))


# ── GET /health/calidad/stream (SSE) ────────────────────────────────────────────────

async def _generar_calidad(request: Request) -> AsyncGenerator[dict, None]:
    """
    Generador SSE: emite métricas de calidad de datos cada 10 segundos.
    Extrae información de errores recientes en Bronce.
    Máximo 360 iteraciones (~1 hora) para liberar recursos.
    """
    import json
    for _ in range(360):
        if await request.is_disconnected():
            return
        try:
            resumen = obtener_resumen_calidad_hoy()
            yield {"event": "calidad", "data": json.dumps(resumen)}
        except Exception as exc:
            yield {"event": "error", "data": f'{{"error": "{exc}"}}'}

        await asyncio.sleep(10)


@enrutador_health.get(
    "/health/calidad/stream",
    summary="Stream SSE de observabilidad de calidad de datos",
    description=(
        "Abre un canal SSE que emite métricas de errores detectados en la capa Bronce. "
        "Emite cada 10 segundos: total errores hoy, top tipos de error, top fundos con error. "
        "Requiere autenticación Bearer con rol viewer o superior."
    ),
    dependencies=[Depends(require_rol("viewer"))],
)
async def stream_calidad(request: Request) -> EventSourceResponse:
    return EventSourceResponse(_generar_calidad(request))
