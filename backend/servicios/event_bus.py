"""
servicios/event_bus.py
======================
Bus de eventos Blinker para comunicación desacoplada entre capas.

Uso:
    # Emitir desde cualquier servicio:
    from servicios.event_bus import EventBus
    EventBus.task_finished.send("ETL_RUNNER", id_corrida=id, estado="OK")

    # Suscribirse (normalmente en lifespan de main.py):
    @EventBus.task_finished.connect
    def _handler(sender, **kw): ...

Las señales son síncronas (Blinker no es async). Los handlers no deben
hacer I/O pesado — deben delegar a asyncio.to_thread si necesitan acceso a BD.
"""

from __future__ import annotations

import logging

from blinker import Namespace

log = logging.getLogger("EventBus")

_ns = Namespace()


class EventBus:
    # ── ETL ───────────────────────────────────────────────────────────────────
    # Corrida encolada por el servicio ETL
    task_started  = _ns.signal("task_started")
    # Runner completó la corrida con éxito
    task_finished = _ns.signal("task_finished")
    # Runner terminó con error o timeout
    task_failed   = _ns.signal("task_failed")

    # ── Proyecciones ──────────────────────────────────────────────────────────
    # Motor calculó resultado (desde portal o futura API de proyecciones)
    projection_calculated = _ns.signal("projection_calculated")
    # Proyección persistida en DWH
    projection_saved      = _ns.signal("projection_saved")

    # ── MDM ───────────────────────────────────────────────────────────────────
    # Registro de cuarentena resuelto/descartado
    mdm_decision  = _ns.signal("mdm_decision")
    # Reinyección masiva completada
    mdm_reinyeccion = _ns.signal("mdm_reinyeccion")

    # ── Sistema ───────────────────────────────────────────────────────────────
    # Solicitar invalidación global de caché (cualquier módulo puede emitirla)
    cache_flush_requested = _ns.signal("cache_flush_requested")
    # Alerta de carga alta detectada por middleware
    system_overload       = _ns.signal("system_overload")

    @classmethod
    def publish(cls, signal_name: str, sender: str, **kwargs) -> None:
        """
        Emite una señal por nombre. Útil para código dinámico.
        Para código estático preferir llamar la señal directamente:
            EventBus.task_finished.send(sender, **kw)
        """
        sig = getattr(cls, signal_name, None)
        if sig is None:
            log.warning("EventBus: señal desconocida '%s'", signal_name)
            return
        log.debug("EventBus.publish [%s] from [%s] data=%s", signal_name, sender, kwargs)
        sig.send(sender, **kwargs)


# Alias de conveniencia — import directo de `bus` para los listeners
bus = EventBus
