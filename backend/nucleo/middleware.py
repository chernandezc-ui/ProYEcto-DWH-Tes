"""
nucleo/middleware.py
====================
Middlewares del backend ACP Platform.

RequestIdMiddleware
-------------------
- Asigna un UUID único a cada request HTTP.
- Lo expone en request.state.request_id.
- Lo propaga al header X-Request-ID de la respuesta.
- Lo añade al contexto de logging (logging ContextFilter).

Uso en main.py:
    from nucleo.middleware import RequestIdMiddleware
    aplicacion.add_middleware(RequestIdMiddleware)
"""

from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


class _RequestIdFilter(logging.Filter):
    """
    Filter que inyecta request_id en todos los registros de log emitidos
    durante el procesamiento del request actual.
    Nota: funciona con var global por thread (seguro en Uvicorn sync workers).
    """

    _current: str = ""

    @classmethod
    def set(cls, request_id: str) -> None:
        cls._current = request_id

    @classmethod
    def clear(cls) -> None:
        cls._current = ""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.__class__._current  # type: ignore[attr-defined]
        return True


# Instalar el filter en el root logger al importar este módulo
_filtro_global = _RequestIdFilter()
logging.getLogger().addFilter(_filtro_global)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware ASGI que asigna un request_id a cada request HTTP
    y lo propaga al estado del request y al header de respuesta.
    """

    def __init__(self, app: ASGIApp, header_entrada: str = "X-Request-ID") -> None:
        super().__init__(app)
        self._header_entrada = header_entrada

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # Reusar el request_id enviado por el cliente (útil para trazabilidad)
        request_id = (
            request.headers.get(self._header_entrada)
            or str(uuid.uuid4())[:8]
        )

        # Propagar al estado del request (disponible en routers y servicios)
        request.state.request_id = request_id

        # Propagar al logging de este thread
        _RequestIdFilter.set(request_id)

        try:
            response = await call_next(request)
        finally:
            _RequestIdFilter.clear()

        response.headers["X-Request-ID"] = request_id
        return response
