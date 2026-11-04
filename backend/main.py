"""
main.py
=======
Punto de entrada del backend ACP Platform.

Registra todos los routers, middlewares, manejadores de error
y expone los health checks principal, liveness y readiness.

Arranque directo:
    uvicorn main:aplicacion --host 0.0.0.0 --port 8810

Arranque por módulo (dev con reload):
    python main.py
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# ── Núcleo ────────────────────────────────────────────────────────────────────
from nucleo.settings import settings
from nucleo.logging import configurar_logging, obtener_logger
from nucleo.middleware import RequestIdMiddleware
from nucleo.conexion import verificar_conexion
from nucleo.excepciones import (
    manejar_error_generico,
    manejar_error_http,
    manejar_error_validacion,
)
from servicios.listeners import registrar_listeners, desregistrar_listeners

# ── Routers ───────────────────────────────────────────────────────────────────
from api.rutas_health import enrutador_health
from api.rutas_auth import enrutador_auth
from api.rutas_etl import enrutador_etl
from api.rutas_cuarentena import enrutador_cuarentena
from api.rutas_ingesta import enrutador_ingesta
from api.rutas_catalogos import enrutador_catalogos
from api.rutas_auditoria import enrutador_auditoria
from api.rutas_config import enrutador_config
from api.rutas_reinyeccion import enrutador_reinyeccion
from api.rutas_alertas import enrutador_alertas
from api.rutas_analista import enrutador_analista
from api.rutas_proyecciones import enrutador_proyecciones

# Configura logging al importar el módulo (antes del lifespan)
configurar_logging()
log = obtener_logger(__name__)


_MAX_REINTENTOS_BD = 3
_ESPERA_REINTENTO_SEG = 5


async def _verificar_bd_en_background() -> None:
    """
    Verifica la BD en background, sin bloquear el bind del puerto HTTP.

    Antes esta lógica vivía en `lifespan` ANTES del `yield`, lo que retrasaba
    el arranque hasta 15 s cuando SQL Server tardaba en responder. El launcher
    no podía detectar el puerto como vivo durante ese tiempo. Ahora arrancamos
    inmediatamente y reportamos el estado de la BD por logs.
    """
    info: dict = {"conectado": False}
    for intento in range(1, _MAX_REINTENTOS_BD + 1):
        info = await asyncio.to_thread(verificar_conexion)
        if info["conectado"]:
            log.info(
                "Backend conectado a BD",
                extra={
                    "entorno":     settings.entorno,
                    "base_datos":  info["base_datos"],
                    "latencia_ms": info["latencia_ms"],
                    "version_sql": info.get("version", "-"),
                    "intento":     intento,
                },
            )
            return
        log.warning(
            "BD no disponible, reintentando…",
            extra={
                "intento": intento,
                "max": _MAX_REINTENTOS_BD,
                "error": info.get("error"),
            },
        )
        if intento < _MAX_REINTENTOS_BD:
            await asyncio.sleep(_ESPERA_REINTENTO_SEG)

    log.warning(
        "Backend operando SIN conexión a SQL Server tras reintentos",
        extra={
            "entorno": settings.entorno,
            "error":   info.get("error", "desconocido"),
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    registrar_listeners()
    log.info("Backend iniciado — verificando BD en segundo plano")
    # Fire-and-forget: el puerto HTTP queda disponible inmediatamente.
    bd_task = asyncio.create_task(_verificar_bd_en_background())

    yield

    if not bd_task.done():
        bd_task.cancel()
        try:
            await bd_task
        except asyncio.CancelledError:
            pass
    desregistrar_listeners()
    log.info("Backend detenido limpiamente")


# ── Aplicación ─────────────────────────────────────────────────────────────────
aplicacion = FastAPI(
    title=settings.api_titulo,
    description=(
        "Backend headless para el DWH Geographic Phenology - Agrícola Cerro Prieto. "
        "Expone el pipeline ETL como subproceso con telemetría SSE, gestión de cuarentena MDM, "
        "consulta de catálogos y auditoría de cargas."
    ),
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middlewares ────────────────────────────────────────────────────────────────
aplicacion.add_middleware(RequestIdMiddleware)
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origenes,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ── Manejadores de error ───────────────────────────────────────────────────────
aplicacion.add_exception_handler(RequestValidationError, manejar_error_validacion)
aplicacion.add_exception_handler(HTTPException, manejar_error_http)
aplicacion.add_exception_handler(Exception, manejar_error_generico)
log.info(
    "Handlers de excepción registrados: RequestValidationError, HTTPException, Exception"
)

# ── Routers ──────────────────────────────────────────────────────────────────
# Infraestructura (sin versionar)
aplicacion.include_router(enrutador_health)      # /health, /health/live, /health/ready
# Autenticación (sin versionar, estable por diseño)
aplicacion.include_router(enrutador_auth)          # /auth/login, /auth/me, /auth/usuarios
# Dominio — todos bajo /api con versionado /v1 en el propio router
aplicacion.include_router(enrutador_etl,          prefix="/api")
aplicacion.include_router(enrutador_cuarentena,   prefix="/api")
aplicacion.include_router(enrutador_ingesta,      prefix="/api")
aplicacion.include_router(enrutador_catalogos,    prefix="/api")
aplicacion.include_router(enrutador_auditoria,    prefix="/api")
aplicacion.include_router(enrutador_config,       prefix="/api")
aplicacion.include_router(enrutador_reinyeccion,  prefix="/api")  # Herramienta Re-inyección MDM
aplicacion.include_router(enrutador_alertas,      prefix="/api")  # Ack persistente de alertas
aplicacion.include_router(enrutador_analista,     prefix="/api")  # Portal analista: charts + notificaciones
aplicacion.include_router(enrutador_proyecciones, prefix="/api")

# ── Documentación Scalar (opcional, lazy import) ──────────────────────────────
# `scalar_fastapi` añade ~100-300ms al cold-start si se importa al boot.
# Lo cargamos sólo cuando alguien visita /scalar.
@aplicacion.get("/scalar", include_in_schema=False)
async def scalar_html():
    """Sirve la documentación moderna de Scalar."""
    try:
        from scalar_fastapi import get_scalar_api_reference
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="scalar_fastapi no está instalado en este entorno.",
        ) from exc
    return get_scalar_api_reference(
        openapi_url=aplicacion.openapi_url,
        title=aplicacion.title + " (Scalar)",
    )


# ── Arranque directo ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:aplicacion",
        host=settings.host,
        port=settings.puerto,
        workers=settings.workers,
        reload=settings.reload or settings.es_desarrollo,
        log_level=settings.log_nivel.lower(),
    )
