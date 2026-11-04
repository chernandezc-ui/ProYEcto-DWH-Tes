"""
servicios/listeners.py
======================
Handlers de señales Blinker del EventBus.

Registrar en main.py lifespan:
    from servicios.listeners import registrar_listeners, desregistrar_listeners

Cada handler es síncrono y liviano (solo logging o caché). Nunca deben
hacer I/O pesado directamente — delegar a asyncio.to_thread si se necesita.
"""

from __future__ import annotations

from nucleo.logging import obtener_logger
from servicios.event_bus import EventBus

log = obtener_logger(__name__)


def _on_task_finished(sender, **kwargs) -> None:
    log.info(
        "ETL corrida finalizada",
        extra={
            "id_corrida":   kwargs.get("id_corrida"),
            "estado":       kwargs.get("estado"),
            "iniciado_por": kwargs.get("iniciado_por"),
        },
    )


def _on_task_failed(sender, **kwargs) -> None:
    log.error(
        "ETL corrida fallida",
        extra={
            "id_corrida": kwargs.get("id_corrida"),
            "error":      kwargs.get("error"),
        },
    )


def _on_mdm_decision(sender, **kwargs) -> None:
    log.info(
        "MDM decisión registrada",
        extra={
            "accion":       kwargs.get("accion"),
            "tabla_origen": kwargs.get("tabla_origen"),
            "id_registro":  kwargs.get("id_registro"),
            "analista":     kwargs.get("analista"),
        },
    )


def _on_mdm_reinyeccion(sender, **kwargs) -> None:
    log.info(
        "MDM reinyección completada",
        extra={
            "reinyectados": kwargs.get("reinyectados"),
            "omitidos":     kwargs.get("omitidos"),
            "analista":     kwargs.get("analista"),
        },
    )


def _on_cache_flush(sender, **kwargs) -> None:
    from nucleo.cache import cache
    cache.limpiar_todo()
    log.info("Caché invalidada por señal", extra={"sender": sender})


_LISTENERS = [
    (EventBus.task_finished,       _on_task_finished),
    (EventBus.task_failed,         _on_task_failed),
    (EventBus.mdm_decision,        _on_mdm_decision),
    (EventBus.mdm_reinyeccion,     _on_mdm_reinyeccion),
    (EventBus.cache_flush_requested, _on_cache_flush),
]


def registrar_listeners() -> None:
    for signal, handler in _LISTENERS:
        signal.connect(handler)


def desregistrar_listeners() -> None:
    for signal, handler in _LISTENERS:
        signal.disconnect(handler)
