"""
runner/runner.py
=================
Proceso separado del web server. Ejecuta corridas ETL de forma controlada.

Arranque:
    python runner/runner.py

O en producción con supervisord / Windows Service.

Ciclo principal:
  1. Espera un comando PENDIENTE en Control.Comando_Ejecucion (poll cada 5s)
  2. Intenta adquirir el lock de Control.Bloqueo_Ejecucion
  3. Si adquiere el lock:
       a. Marca la corrida como EJECUTANDO
       b. Llama a ejecutor.ejecutar_corrida() (bloquea hasta que termina)
       c. Libera el lock
  4. Si no adquiere el lock: espera el siguiente ciclo
  5. Implementa retry: si la corrida falló y max_reintentos > intentos actuales,
     encola un nuevo comando REINTENTAR

Señales de parada:
  - SIGINT (Ctrl+C): termina de forma limpia
  - Archivo runner.stop en el directorio runner/: parada suave entre ciclos
"""

from __future__ import annotations

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

_DIR_BACKEND = Path(__file__).resolve().parent.parent
if str(_DIR_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DIR_BACKEND))

from nucleo.logging import configurar_logging, obtener_logger
from nucleo.settings import settings
import repositorios.repo_corridas as r_corrida
import repositorios.repo_locks as r_lock
import repositorios.repo_comandos as r_cmd
from runner.ejecutor import ejecutar_corrida

configurar_logging()
log = obtener_logger("runner")

_STOP_FILE    = Path(__file__).parent / "runner.stop"
_POLL_COLA_COMANDOS_SEG   = 1      # Segundos entre polls (antes 5s)
_LOCK_TTL_VENCIMIENTO_SEG = 120    # Segundos antes de considerar lock muerto

_continuar = True

def _detener(sig, frame):  # type: ignore
    global _continuar
    log.info("[RUNNER] Señal de parada recibida.")
    _continuar = False

signal.signal(signal.SIGINT,  _detener)
signal.signal(signal.SIGTERM, _detener)


def _procesar_comando(cmd: dict) -> None:
    """
    Ejecuta un comando tomado de la cola.
    Gestiona el ciclo completo: lock → ejecución → retry → liberación.
    """
    id_corrida   = cmd["ID_Corrida"]
    id_comando   = cmd["ID_Comando"]
    iniciado_por = cmd["Iniciado_Por"]
    comentario   = cmd.get("Comentario")
    max_ret      = int(cmd["Max_Reintentos"] or 0)
    timeout      = int(cmd["Timeout_Seg"]    or 3600)

    log.info("[RUNNER] Tomando comando", extra={
        "id_corrida": id_corrida, "id_comando": id_comando
    })

    # ── Lock de concurrencia ──────────────────────────────────────────────────
    if not r_lock.adquirir_lock(id_corrida, timeout_lock_seg=_LOCK_TTL_VENCIMIENTO_SEG):
        bloqueo = r_lock.lock_activo()
        log.warning("[RUNNER] No se pudo adquirir lock — otra corrida en ejecución",
                    extra={"bloqueo": bloqueo})
        r_cmd.marcar_comando(id_comando, "ERROR_COLA", "Lock ocupado por otra corrida.")
        r_corrida.actualizar_estado_corrida(id_corrida, "ERROR",
                                     "No se pudo adquirir lock de ejecución.")
        return

    try:
        r_cmd.marcar_comando(id_comando, "PROCESANDO")
        estado = ejecutar_corrida(
            id_corrida=id_corrida,
            iniciado_por=iniciado_por,
            comentario=comentario,
            timeout_segundos=timeout,
        )
    finally:
        r_lock.liberar_lock(id_corrida)

    r_cmd.marcar_comando(id_comando, "PROCESADO")

    # ── Retry automático ──────────────────────────────────────────────────────
    if estado == "ERROR" and max_ret > 0:
        corrida = r_corrida.obtener_corrida(id_corrida)
        intento_actual = max(1, corrida.get("intento_numero", 1) if corrida else 1)
        if intento_actual <= max_ret:
            # Backoff exponencial antes del reintento: 30s, 60s, 120s, ... máx 5 min
            backoff_seg = min(30 * (2 ** max(0, intento_actual - 1)), 300)
            log.info("[RUNNER] Reintento en %ds (intento %d)", backoff_seg, intento_actual + 1)
            time.sleep(backoff_seg)
            log.info("[RUNNER] Encolando reintento",
                     extra={"id_corrida": id_corrida, "intento": intento_actual + 1})
            nuevo_id = f"{id_corrida}-r{intento_actual + 1}"
            comentario_reintento = (corrida or {}).get("comentario") or comentario
            try:
                r_corrida.insertar_corrida(
                    id_corrida=nuevo_id,
                    iniciado_por=iniciado_por,
                    comentario=comentario_reintento,
                    max_reintentos=max_ret,
                    timeout_segundos=timeout,
                )
                r_cmd.encolar_comando(
                    id_corrida=nuevo_id,
                    iniciado_por=iniciado_por,
                    tipo_comando="REINTENTAR",
                    comentario=comentario_reintento,
                    max_reintentos=max_ret - 1,
                    timeout_seg=timeout,
                )
            except Exception:
                log.exception("[RUNNER] No se pudo encolar reintento")


def _limpiar_corridas_huerfanas() -> None:
    """Marca como TIMEOUT las corridas que quedaron en EJECUTANDO sin heartbeat válido."""
    try:
        activas = r_corrida.listar_corridas(solo_activas=True)
        ahora = datetime.now()
        for c in activas:
            if c.get("estado") != "EJECUTANDO":
                continue
            heartbeat = c.get("heartbeat_ultimo")
            if heartbeat is None or (ahora - heartbeat).total_seconds() > _LOCK_TTL_VENCIMIENTO_SEG:
                id_c = c["id_corrida"]
                r_corrida.actualizar_estado_corrida(
                    id_c, "TIMEOUT",
                    "Corrida huérfana detectada al reiniciar el runner."
                )
                log.warning("[RUNNER] Corrida huérfana marcada TIMEOUT", extra={"id_corrida": id_c})
    except Exception as exc:
        log.error("[RUNNER] Error limpiando corridas huérfanas", extra={"error": str(exc)})


def _ciclo_principal() -> None:
    log.info("[RUNNER] Iniciando. PID=%d", os.getpid())

    _limpiar_corridas_huerfanas()

    while _continuar:
        # Parada suave vía archivo sentinel
        if _STOP_FILE.exists():
            log.info("[RUNNER] Archivo runner.stop detectado. Deteniendo.")
            _STOP_FILE.unlink(missing_ok=True)
            break

        cmd = r_cmd.tomar_comando_pendiente()
        if cmd is None:
            time.sleep(_POLL_COLA_COMANDOS_SEG)
            continue

        try:
            _procesar_comando(cmd)
        except Exception:
            log.exception("[RUNNER] Error inesperado procesando comando",
                          extra={"cmd": cmd})
            r_cmd.marcar_comando(
                int(cmd.get("ID_Comando", -1)),
                "ERROR_COLA",
                "Excepción inesperada en el runner.",
            )

    log.info("[RUNNER] Terminado limpiamente.")


if __name__ == "__main__":
    _ciclo_principal()
