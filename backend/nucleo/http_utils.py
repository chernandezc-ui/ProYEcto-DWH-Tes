"""
nucleo/http_utils.py
====================
Helpers HTTP compartidos para routers y manejadores globales.
"""

from __future__ import annotations

from fastapi import Request


def obtener_ip_cliente(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def obtener_request_id(request: Request, default: str | None = None) -> str | None:
    state = getattr(request, "state", None)
    return getattr(state, "request_id", default)
