"""
nucleo/rate_limit.py
====================
Rate limiting en memoria para endpoints sensibles (sin dependencias externas).

Política: ventana deslizante por IP.
  - Máximo N intentos en los últimos W segundos.
  - Al superar el límite retorna HTTP 429 con Retry-After.
  - Las entradas antiguas se purgan automáticamente al consultar.

LIMITACIÓN CONOCIDA (V-05): el estado es por-proceso. Con ACP_WORKERS>1 o
varias réplicas cada proceso tiene su propio contador, por lo que el límite
efectivo se multiplica por el número de procesos. Para un límite global y
resistente a reinicios, sustituir este backend por Redis (p. ej. slowapi).
Mientras tanto acotamos el número de IPs rastreadas para que un atacante que
rote IPs no agote la memoria del proceso.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

_lock_global = Lock()

# { ip: deque([timestamp, ...]) }
_registro: dict[str, deque[float]] = defaultdict(deque)

# Cota de IPs distintas rastreadas simultáneamente. Evita crecimiento no
# acotado de memoria si un atacante rota direcciones de origen (memory DoS).
_MAX_IPS_RASTREADAS = 10_000


def _purgar_ventana(intentos: deque[float], ventana: int, ahora: float) -> None:
    while intentos and ahora - intentos[0] > ventana:
        intentos.popleft()


def _acotar_registro(ventana: int, ahora: float) -> None:
    """Elimina entradas cuya ventana ya expiró; si aun así se supera la cota,
    descarta las IPs más antiguas. Se llama bajo `_lock_global`."""
    if len(_registro) <= _MAX_IPS_RASTREADAS:
        return
    vacias = [ip for ip, dq in _registro.items() if not dq or ahora - dq[-1] > ventana]
    for ip in vacias:
        _registro.pop(ip, None)
    # Si sigue por encima de la cota tras purgar expiradas, recorta las más viejas.
    if len(_registro) > _MAX_IPS_RASTREADAS:
        for ip in sorted(_registro, key=lambda i: _registro[i][-1] if _registro[i] else 0.0)[
            : len(_registro) - _MAX_IPS_RASTREADAS
        ]:
            _registro.pop(ip, None)


def verificar_rate_limit(
    request: Request,
    *,
    max_intentos: int = 5,
    ventana_segundos: int = 60,
) -> None:
    """
    Dependencia FastAPI. Lanza HTTP 429 si la IP supera el límite.

    Uso:
        def rate_limit_login(request: Request) -> None:
            verificar_rate_limit(request, max_intentos=5, ventana_segundos=60)

        @router.post("/login")
        async def login(request: Request, _: None = Depends(rate_limit_login)):
            ...

    NO usar `lambda r: ...` — FastAPI lo trata como query-parameter `r` y
    devuelve 422 "query.r: Field required".
    """
    ip = request.client.host if request.client else "desconocido"
    ahora = time.monotonic()

    with _lock_global:
        _acotar_registro(ventana_segundos, ahora)
        intentos = _registro[ip]
        _purgar_ventana(intentos, ventana_segundos, ahora)

        if len(intentos) >= max_intentos:
            tiempo_restante = int(ventana_segundos - (ahora - intentos[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Demasiados intentos de inicio de sesión. "
                    f"Intente nuevamente en {tiempo_restante} segundos."
                ),
                headers={"Retry-After": str(tiempo_restante)},
            )

        intentos.append(ahora)
