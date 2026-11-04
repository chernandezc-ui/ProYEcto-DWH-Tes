"""
nucleo/excepciones.py
=====================
Excepciones HTTP explícitas del backend ACP.
Los routers nunca dejan propagar errores genéricos de SQLAlchemy.

Todos los manejadores incluyen request_id y timestamp en la respuesta.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from nucleo.http_utils import obtener_request_id


# ── Excepciones de dominio ────────────────────────────────────────────────────

class ErrorBaseDatos(HTTPException):
    """Error de conexión o consulta SQL. Nunca expone detalles internos al cliente."""
    def __init__(self, detalle: str = "Error en la base de datos. Contacte al administrador."):
        super().__init__(status_code=503, detail=detalle)


class ErrorRecursoNoEncontrado(HTTPException):
    """El recurso solicitado no existe en la BD."""
    def __init__(self, recurso: str = "Recurso"):
        super().__init__(status_code=404, detail=f"{recurso} no encontrado.")


class ErrorValidacion(HTTPException):
    """El payload del cliente no cumple las reglas de negocio."""
    def __init__(self, detalle: str):
        super().__init__(status_code=422, detail=detalle)


class ErrorCorridaNoEncontrada(HTTPException):
    """El id_corrida solicitado no existe en el broker SSE."""
    def __init__(self, id_corrida: str):
        super().__init__(
            status_code=404,
            detail=f"Corrida '{id_corrida}' no encontrada o ya finalizada.",
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _request_id(request: Request) -> str:
    """Extrae el request_id del estado del request si el middleware está activo."""
    return obtener_request_id(request, "-")


def _ahora_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _cuerpo_error(codigo: int, mensaje: str, request_id: str) -> dict:
    from nucleo.api_response import StandardResponse
    return StandardResponse.fail(
        error_msg=mensaje,
        metadata={
            "codigo_http": codigo,
            "request_id": request_id,
            "timestamp": _ahora_iso()
        }
    ).model_dump()


# ── Manejadores globales ──────────────────────────────────────────────────────

async def manejar_error_http(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler global: devuelve JSON estructurado con request_id."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_cuerpo_error(exc.status_code, exc.detail, _request_id(request)),
    )


async def manejar_error_validacion(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handler para errores 422 de Pydantic/FastAPI.

    FastAPI por defecto devuelve `{"detail": [{loc, msg, type, input, ...}]}`
    como array. Sin un handler explícito el portal lo recibe crudo y muestra
    "[object Object]" porque no sabe colapsarlo a string.

    Aquí:
      1. Logueamos cada error de validación con loc + msg (visible en consola
         del FastAPI para diagnosticar qué campo del body falla).
      2. Devolvemos una respuesta con `detail` ya colapsado a string legible,
         compatible con el resto de errores HTTP del backend.
    """
    from nucleo.logging import obtener_logger
    log = obtener_logger(__name__)

    errores = exc.errors()
    partes: list[str] = []
    for err in errores:
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body") or "body"
        msg = err.get("msg", "valor inválido")
        partes.append(f"{loc}: {msg}")
    detalle = " | ".join(partes) or "Cuerpo de petición inválido."

    log.warning(
        "Validación 422 en %s %s -> %s",
        request.method, request.url.path, detalle,
        extra={"request_id": _request_id(request), "errores_pydantic": errores},
    )

    return JSONResponse(
        status_code=422,
        content=_cuerpo_error(422, detalle, _request_id(request)),
    )


async def manejar_error_generico(request: Request, exc: Exception) -> JSONResponse:
    """Captura cualquier excepción no controlada. Evita exponer stack trace."""
    from nucleo.logging import obtener_logger
    log = obtener_logger(__name__)
    log.exception(
        "Error no controlado en el servidor",
        extra={"request_id": _request_id(request)},
    )
    return JSONResponse(
        status_code=500,
        content=_cuerpo_error(
            500,
            "Error interno del servidor. Revise los logs del backend.",
            _request_id(request),
        ),
    )
