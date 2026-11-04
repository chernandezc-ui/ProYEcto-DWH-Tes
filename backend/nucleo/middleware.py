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

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from nucleo.logging import request_id_context


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

        # Aislar el contexto de cada tarea y propagarlo también a to_thread.
        token = request_id_context.set(request_id)

        try:
            response = await call_next(request)
        finally:
            request_id_context.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
