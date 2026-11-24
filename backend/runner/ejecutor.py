"""
runner/ejecutor.py
==================
Ejecutor de un subproceso pipeline.py para una corrida específica.

Responsabilidades:
  - Lanzar pipeline.py como subprocess
  - Capturar stdout/stderr línea a línea
  - Persistir cada línea en Control.Corrida_Evento (no en memoria)
  - Publicar heartbeats periódicos al lock y a la corrida
  - Detectar cancelación en cada ciclo de heartbeat
  - Registrar inicio y fin en Auditoria.Log_Carga
  - Retornar el estado final (OK | ERROR | CANCELADO | TIMEOUT)
"""

from __future__ import annotations
import json
import os
import queue
import re
import signal
import sys
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from nucleo.etl_argumentos import construir_argumentos_pipeline, deserializar_comentario_etl
from nucleo.auditoria import registrar_inicio_corrida, registrar_fin_corrida
from nucleo.logging import obtener_logger
from servicios.event_bus import EventBus
import repositorios.repo_corridas as r_corrida
import repositorios.repo_locks as r_lock

log = obtener_logger(__name__)

EstadoFinal = Literal["OK", "ERROR", "CANCELADO", "TIMEOUT"]

_DIR_ETL = Path(__file__).resolve().parents[2] / "ETL"
_SCRIPT  = _DIR_ETL / "pipeline.py"
_PATRON_PASO = re.compile(r"\[(?P<orden>\d+)/(?:\d+)\]\s+(?P<descripcion>.+?)\s*$")
_PATRON_ERROR = re.compile(r"ERROR(?:\s+en\s+(?P<objetivo>[^:]+))?:\s*(?P<detalle>.+)$")
_RE_METRICAS = re.compile(
    r"(\d[\d\s]*)\s+(?:leidos?|procesados?)"
    r".*?(\d[\d\s]*)\s+(?:rechazados?|errores?)",
    re.IGNORECASE,
)
_PREFIJO_EVENTO_ESTRUCTURADO = "@@ACP_EVENT "
# Tiempo máximo por paso individual del pipeline.
# Si un paso activo supera este límite sin producir output, se aborta la corrida.
_TIMEOUT_PASO_SEGUNDOS = 600
# Tiempo máximo esperando el primer output tras lanzar pipeline.py.
# Evita que un subproceso congelado al arrancar retenga el lock durante 1 hora.
_TIMEOUT_ARRANQUE_SEGUNDOS = 90
# Intervalo de sondeo de cancelación (más ágil que el heartbeat de 30s).
_POLL_CANCELACION_SEG = 5


@dataclass
class _PasoActivo:
    id_paso: int
    nombre_paso: str
    orden: int
    cerrado: bool = False


def _resolver_python() -> str:
    """El ETL usa exactamente el intérprete y dependencias del runner."""
    return sys.executable


def _normalizar_nombre_paso(descripcion: str) -> str:
    return descripcion.strip().rstrip(".").strip()


_RE_ANSI = re.compile(r'\x1b\[.*?m')

def _limpiar_color(linea: str) -> str:
    """Elimina los códigos de escape ANSI de una cadena."""
    return _RE_ANSI.sub('', linea)


def _extraer_inicio_paso(linea: str) -> tuple[int, str] | None:
    coincidencia = _PATRON_PASO.search(linea.strip())
    if not coincidencia:
        return None
    return (
        int(coincidencia.group("orden")),
        _normalizar_nombre_paso(coincidencia.group("descripcion")),
    )


def _linea_es_error_de_paso(linea: str, paso_activo: _PasoActivo | None) -> tuple[bool, str | None]:
    coincidencia = _PATRON_ERROR.search(linea.strip())
    if not coincidencia:
        return False, None

    objetivo = (coincidencia.group("objetivo") or "").strip()
    if paso_activo is None or not objetivo:
        return True, linea.strip()
    if objetivo in paso_activo.nombre_paso:
        return True, linea.strip()
    return False, None


def _parsear_evento_estructurado(linea: str) -> dict | None:
    """Parsea líneas estructuradas `@@ACP_EVENT {...}` emitidas por pipeline.py."""
    if not linea.startswith(_PREFIJO_EVENTO_ESTRUCTURADO):
        return None
    crudo = linea[len(_PREFIJO_EVENTO_ESTRUCTURADO):].strip()
    if not crudo:
        return None
    try:
        datos = json.loads(crudo)
        return datos if isinstance(datos, dict) else None
    except json.JSONDecodeError:
        return None


def _terminar_arbol_proceso(proceso: subprocess.Popen) -> None:
    """
    Termina el subproceso y todos sus hijos en Windows (taskkill /T /F)
    y en Linux/POSIX (killpg sobre el grupo de procesos creado con start_new_session).
    """
    if proceso.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proceso.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
            return
        except Exception:
            pass
    elif hasattr(os, "killpg") and hasattr(os, "getpgid"):
        try:
            pgid = os.getpgid(proceso.pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                proceso.wait(timeout=3)
                return
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                return
        except ProcessLookupError:
            return
        except Exception:
            pass
    try:
        proceso.terminate()
    except Exception:
        pass


def _cerrar_paso_activo(
    paso_activo: _PasoActivo | None,
    *,
    estado: str,
    mensaje_error: str | None = None,
    filas_procesadas: int = 0,
    filas_rechazadas: int = 0,
) -> None:
    if paso_activo is None or paso_activo.cerrado or paso_activo.id_paso < 0:
        return
    r_corrida.cerrar_paso(
        paso_activo.id_paso,
        estado=estado,
        mensaje_error=mensaje_error,
        filas_procesadas=filas_procesadas,
        filas_rechazadas=filas_rechazadas,
    )
    paso_activo.cerrado = True


def _abrir_nuevo_paso(id_corrida: str, orden: int, nombre_paso: str) -> _PasoActivo:
    return _PasoActivo(
        id_paso=r_corrida.insertar_paso(id_corrida, nombre_paso, orden=orden),
        nombre_paso=nombre_paso,
        orden=orden,
    )


def _bucle_heartbeat_segundo_plano(
    id_corrida: str,
    pid: int,
    intervalo_seg: int,
    detener: threading.Event,
) -> None:
    """
    Mantiene heartbeat de corrida y lock vivos aun cuando el subprocess
    no emita stdout. Evita robo de lock si pipeline cuelga sin output.
    """
    while not detener.wait(intervalo_seg):
        try:
            r_corrida.actualizar_heartbeat_corrida(id_corrida, pid)
            r_lock.actualizar_heartbeat_lock(id_corrida=id_corrida)
        except Exception:
            log.warning("[RUNNER] heartbeat segundo plano fallo", extra={"id_corrida": id_corrida})


def _leer_stdout_en_thread(
    stdout,
    cola: "queue.Queue[str | None]",
) -> None:
    """Lee stdout línea a línea y pone cada línea en la cola. Pone None al terminar."""
    try:
        for linea in stdout:
            cola.put(linea)
    finally:
        cola.put(None)  # centinela de fin


def ejecutar_corrida(
    id_corrida: str,
    iniciado_por: str,
    comentario: str | None = None,
    timeout_segundos: int = 3600,
    heartbeat_intervalo_seg: int = 30,
    timeout_arranque_segundos: int = _TIMEOUT_ARRANQUE_SEGUNDOS,
) -> EstadoFinal:
    """
    Ejecuta pipeline.py para la corrida dada.

    Flujo:
        1. Registra el inicio en Auditoria.Log_Carga → obtiene id_log
        2. Actualiza Control.Corrida a EJECUTANDO
        3. Lanza subprocess con timeout de watchdog
        4. Lee stdout línea a línea → INSERT Control.Corrida_Evento
        5. Cada heartbeat_intervalo_seg verifica cancelación
        6. Al terminar: actualiza Control.Corrida y Auditoria.Log_Carga

    Retorna el estado final.
    """
    pid = os.getpid()
    estado_final: EstadoFinal = "ERROR"
    codigo_retorno = -1
    id_log: int | None = None
    parametros = deserializar_comentario_etl(comentario)
    modo_ejecucion = parametros["modo_ejecucion"]
    nombre_pipeline = "PIPELINE_COMPLETO" if modo_ejecucion == "completo" else "PIPELINE_FACTS"
    argumentos_pipeline = construir_argumentos_pipeline(comentario)

    # ── 1. Auditoría de inicio ─────────────────────────────────────────────────
    try:
        id_log = registrar_inicio_corrida(
            nombre_proceso="ETL_RUNNER",
            tabla_destino=nombre_pipeline,
            nombre_archivo=f"corrida_{id_corrida[:8]}_{modo_ejecucion}",
        )
    except Exception:
        log.warning("No se pudo registrar inicio en auditoría", extra={"id_corrida": id_corrida})
        r_corrida.insertar_evento(
            id_corrida,
            "[ADVERTENCIA] Fallo al registrar auditoría de inicio — la corrida continuará sin ID de log.",
            tipo="LOG",
        )

    # ── 2. Marcar corrida como EJECUTANDO ─────────────────────────────────────
    r_corrida.actualizar_estado_corrida(
        id_corrida=id_corrida,
        estado="EJECUTANDO",
        pid_runner=pid,
        id_log_auditoria=id_log,
    )
    r_corrida.insertar_evento(id_corrida, f"[RUNNER] Inicio. PID={pid}", tipo="LOG")
    paso_activo: _PasoActivo | None = None
    pasos_paralelos: dict[str, _PasoActivo] = {}
    motivo_timeout: str | None = None
    _metricas_paso_actual: dict[str, int] = {"filas_procesadas": 0, "filas_rechazadas": 0}

    # ── 3. Lanzar subprocess ──────────────────────────────────────────────────
    proceso: subprocess.Popen | None = None
    cancelado_por_heartbeat = False
    detener_heartbeat = threading.Event()
    hilo_heartbeat: threading.Thread | None = None

    try:
        python_exe = _resolver_python()
        log.info(
            "[RUNNER] Lanzando subprocess",
            extra={"python": python_exe, "script": str(_SCRIPT), "pipeline_args": argumentos_pipeline},
        )
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"      # fuerza flush inmediato de stdout en el pipeline
        env["PYTHONIOENCODING"] = "utf-8"  # evita errores de codificación en consola Windows
        env["PYTHONFAULTHANDLER"] = "1"    # permite diagnóstico si el subproceso se cuelga

        popen_kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "cwd": str(_DIR_ETL),
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "env": env,
        }
        if sys.platform != "win32":
            popen_kwargs["start_new_session"] = True

        proceso = subprocess.Popen(
            [python_exe, "-u", str(_SCRIPT), *argumentos_pipeline],
            **popen_kwargs,
        )
        log.info(
            "[RUNNER] Subprocess iniciado",
            extra={"id_corrida": id_corrida, "pid_pipeline": proceso.pid},
        )

        hilo_heartbeat = threading.Thread(
            target=_bucle_heartbeat_segundo_plano,
            args=(id_corrida, pid, heartbeat_intervalo_seg, detener_heartbeat),
            daemon=True,
            name=f"hb-{id_corrida[:8]}",
        )
        hilo_heartbeat.start()

        cola_stdout: queue.Queue[str | None] = queue.Queue()
        hilo_stdout = threading.Thread(
            target=_leer_stdout_en_thread,
            args=(proceso.stdout, cola_stdout),
            daemon=True,
            name=f"stdout-{id_corrida[:8]}",
        )
        hilo_stdout.start()

        # ── 4. Leer stdout + heartbeat en thread paralelo ──────────────────────
        inicio_subproceso = time.monotonic()
        ultimo_heartbeat = inicio_subproceso
        ultimo_check_cancelacion = inicio_subproceso
        recibio_primer_output = False
        deadline = inicio_subproceso + timeout_segundos
        timestamp_inicio_paso: datetime | None = None
        _metricas_paso_actual: dict[str, int] = {"filas_procesadas": 0, "filas_rechazadas": 0}

        while True:
            ahora = time.monotonic()

            # ── Sondeo rápido de cancelación (cada 5s) ──
            if ahora - ultimo_check_cancelacion >= min(_POLL_CANCELACION_SEG, heartbeat_intervalo_seg):
                ultimo_check_cancelacion = ahora
                if r_corrida.corrida_fue_cancelada(id_corrida):
                    log.info(
                        "[RUNNER] Cancelación detectada, terminando árbol de proceso",
                        extra={"id_corrida": id_corrida},
                    )
                    _terminar_arbol_proceso(proceso)
                    cancelado_por_heartbeat = True
                    break

            # ── Watchdog de arranque: evita cuelgues silenciosos antes del primer output ──
            if (
                not recibio_primer_output
                and timeout_arranque_segundos > 0
                and (ahora - inicio_subproceso) > timeout_arranque_segundos
            ):
                motivo_timeout = (
                    f"Pipeline no emitió salida durante los primeros "
                    f"{timeout_arranque_segundos}s de arranque (posible bloqueo inicial)."
                )
                log.error(
                    "[EJECUTOR] Timeout de arranque sin output (%ds) — abortando corrida",
                    timeout_arranque_segundos,
                    extra={"id_corrida": id_corrida},
                )
                r_corrida.insertar_evento(id_corrida, f"[TIMEOUT ARRANQUE] {motivo_timeout}", tipo="ERROR")
                _terminar_arbol_proceso(proceso)
                estado_final = "TIMEOUT"
                break

            # ── Heartbeat y timeout por paso — se ejecuta aunque no haya output ──
            if ahora - ultimo_heartbeat >= heartbeat_intervalo_seg:
                r_corrida.actualizar_heartbeat_corrida(id_corrida, pid)
                r_lock.actualizar_heartbeat_lock(id_corrida=id_corrida)
                ultimo_heartbeat = ahora

                if timestamp_inicio_paso is not None:
                    seg_en_paso = (datetime.now() - timestamp_inicio_paso).total_seconds()
                    if seg_en_paso > _TIMEOUT_PASO_SEGUNDOS:
                        motivo_timeout = (
                            f"Paso activo superó el límite de {_TIMEOUT_PASO_SEGUNDOS}s sin avance."
                        )
                        log.error(
                            "[EJECUTOR] Paso activo supera timeout (%ds) — abortando corrida",
                            _TIMEOUT_PASO_SEGUNDOS,
                            extra={"id_corrida": id_corrida, "segundos": int(seg_en_paso)},
                        )
                        _terminar_arbol_proceso(proceso)
                        estado_final = "TIMEOUT"
                        break

            if ahora > deadline:
                motivo_timeout = f"Corrida excedió el timeout global de {timeout_segundos}s."
                log.warning("[RUNNER] Timeout alcanzado, terminando proceso",
                            extra={"id_corrida": id_corrida})
                _terminar_arbol_proceso(proceso)
                estado_final = "TIMEOUT"
                break

            # ── Leer múltiples líneas de la cola (batching) ──
            lineas = []
            try:
                # Esperamos hasta 1s por la primera línea
                linea_inicial = cola_stdout.get(timeout=1.0)
                if linea_inicial is not None:
                    recibio_primer_output = True
                    lineas.append(linea_inicial)
                    # Drenar el resto de la cola disponible instantáneamente (hasta 500 líneas por ciclo)
                    while len(lineas) < 500:
                        try:
                            l_extra = cola_stdout.get_nowait()
                            if l_extra is None:
                                lineas.append(None)
                                break
                            lineas.append(l_extra)
                        except queue.Empty:
                            break
                else:
                    lineas.append(None)
            except queue.Empty:
                continue  # sin output — volver a chequear heartbeat/timeout

            # Procesar el batch
            eventos_batch = []
            termino_proceso = False

            for linea in lineas:
                if linea is None:
                    termino_proceso = True
                    break

                linea_limpia = _limpiar_color(linea.strip())
                if not linea_limpia:
                    continue

                evento_estructurado = _parsear_evento_estructurado(linea_limpia)
                if evento_estructurado is not None:
                    tipo_ev = str(evento_estructurado.get("tipo", "")).lower()
                    nombre_fact = str(evento_estructurado.get("fact", "")).strip()

                    if tipo_ev == "fact_inicio" and nombre_fact:
                        orden_fact = int(evento_estructurado.get("orden") or 100)
                        pasos_paralelos[nombre_fact] = _abrir_nuevo_paso(
                            id_corrida,
                            orden=100 + orden_fact,
                            nombre_paso=f"Fact: {nombre_fact}"[:100],
                        )
                        timestamp_inicio_paso = datetime.now()
                        eventos_batch.append({
                            "id_corrida": id_corrida,
                            "mensaje": f"[FACT INICIO] {nombre_fact}",
                            "tipo": "PROGRESO",
                        })
                        continue

                    if tipo_ev == "fact_fin" and nombre_fact:
                        estado_raw = str(evento_estructurado.get("estado", "OK")).upper()
                        estado_paso = "OK" if estado_raw == "OK" else "ERROR"
                        insertados = int(evento_estructurado.get("insertados") or 0)
                        rechazados = int(evento_estructurado.get("rechazados") or 0)
                        duracion_seg = evento_estructurado.get("duracion_seg")
                        msg_err = evento_estructurado.get("mensaje") or None

                        paso_fact = pasos_paralelos.pop(nombre_fact, None)
                        _cerrar_paso_activo(
                            paso_fact,
                            estado=estado_paso,
                            mensaje_error=str(msg_err) if estado_paso != "OK" and msg_err else None,
                            filas_procesadas=insertados,
                            filas_rechazadas=rechazados,
                        )
                        timestamp_inicio_paso = datetime.now()
                        dur_txt = f" ({duracion_seg}s)" if duracion_seg is not None else ""
                        resumen_txt = (
                            f"[FACT {estado_raw}] {nombre_fact}: "
                            f"{insertados} insertados, {rechazados} rechazados{dur_txt}"
                        )
                        if msg_err and estado_paso != "OK":
                            resumen_txt = f"{resumen_txt} — {msg_err}"
                        eventos_batch.append({
                            "id_corrida": id_corrida,
                            "mensaje": resumen_txt[:4000],
                            "tipo": "PROGRESO" if estado_paso == "OK" else "ERROR",
                        })
                        continue

                # Agregamos a la lista de inserción en batch
                eventos_batch.append({
                    "id_corrida": id_corrida,
                    "mensaje": linea_limpia[:4000],
                    "tipo": "LOG",
                })

                inicio_paso = _extraer_inicio_paso(linea_limpia)
                if inicio_paso is not None:
                    orden_paso, nombre_paso = inicio_paso
                    _cerrar_paso_activo(
                        paso_activo,
                        estado="OK",
                        filas_procesadas=_metricas_paso_actual["filas_procesadas"],
                        filas_rechazadas=_metricas_paso_actual["filas_rechazadas"],
                    )
                    paso_activo = _abrir_nuevo_paso(id_corrida, orden_paso, nombre_paso[:100])
                    timestamp_inicio_paso = datetime.now()
                    _metricas_paso_actual = {"filas_procesadas": 0, "filas_rechazadas": 0}
                else:
                    _paso_para_cerrar = paso_activo  # captura referencia antes de cualquier modificación futura
                    es_error_paso, mensaje_error = _linea_es_error_de_paso(linea_limpia, _paso_para_cerrar)
                    if es_error_paso:
                        _cerrar_paso_activo(
                            _paso_para_cerrar,
                            estado="ERROR",
                            mensaje_error=mensaje_error,
                            filas_procesadas=_metricas_paso_actual["filas_procesadas"],
                            filas_rechazadas=_metricas_paso_actual["filas_rechazadas"],
                        )
                    m_met = _RE_METRICAS.search(linea_limpia)
                    if m_met:
                        _metricas_paso_actual["filas_procesadas"] = int(m_met.group(1).replace(" ", ""))
                        _metricas_paso_actual["filas_rechazadas"] = int(m_met.group(2).replace(" ", ""))

            if eventos_batch:
                r_corrida.insertar_eventos_batch(eventos_batch)

            if termino_proceso:
                break

        log.info("[RUNNER] Stdout agotado, esperando fin de proceso", extra={"id_corrida": id_corrida})
        proceso.wait(timeout=10)
        codigo_retorno = proceso.returncode
        log.info(
            "[RUNNER] Proceso terminado",
            extra={"id_corrida": id_corrida, "returncode": codigo_retorno},
        )

    except subprocess.TimeoutExpired:
        if proceso:
            _terminar_arbol_proceso(proceso)
        codigo_retorno = -9
        estado_final = "TIMEOUT"
    except Exception as exc:
        r_corrida.insertar_evento(id_corrida, f"[RUNNER ERROR] {exc}", tipo="ERROR")
        log.exception("[RUNNER] Excepción al ejecutar pipeline", extra={"id_corrida": id_corrida})
        codigo_retorno = -99
    finally:
        detener_heartbeat.set()
        if hilo_heartbeat is not None:
            hilo_heartbeat.join(timeout=max(10, heartbeat_intervalo_seg + 5))

    # ── 6. Determinar estado final ────────────────────────────────────────────
    if cancelado_por_heartbeat and codigo_retorno != 0:
        # Cancelación genuina: el proceso fue terminado forzosamente
        estado_final = "CANCELADO"
    elif cancelado_por_heartbeat and codigo_retorno == 0:
        # Race condition: el proceso terminó exitosamente antes de que se procesara la cancelación
        log.warning(
            "[EJECUTOR] Cancelación solicitada pero proceso terminó con código 0 — marcando OK",
            extra={"id_corrida": id_corrida},
        )
        estado_final = "OK"
    elif estado_final not in ("TIMEOUT",):
        estado_final = "OK" if codigo_retorno == 0 else "ERROR"

    if estado_final == "OK":
        msg_final = "Pipeline finalizado con éxito."
    elif motivo_timeout:
        msg_final = motivo_timeout
    else:
        msg_final = f"Pipeline terminó con estado {estado_final}. Código: {codigo_retorno}."

    # Evento de cierre
    r_corrida.insertar_evento(id_corrida, f"[FIN] {msg_final}", tipo="FIN")

    estado_paso_cierre = "OK" if estado_final == "OK" else ("OMITIDO" if estado_final == "CANCELADO" else "ERROR")
    _cerrar_paso_activo(
        paso_activo,
        estado=estado_paso_cierre,
        mensaje_error=msg_final if estado_final != "OK" else None,
        filas_procesadas=_metricas_paso_actual.get("filas_procesadas", 0),
        filas_rechazadas=_metricas_paso_actual.get("filas_rechazadas", 0),
    )
    for paso_pendiente in pasos_paralelos.values():
        _cerrar_paso_activo(
            paso_pendiente,
            estado=estado_paso_cierre,
            mensaje_error=msg_final if estado_final != "OK" else None,
        )

    # Actualizar Control.Corrida
    r_corrida.actualizar_estado_corrida(
        id_corrida=id_corrida,
        estado=estado_final,
        mensaje_final=msg_final,
    )

    # Actualizar Auditoria.Log_Carga (preserva OK | ERROR | CANCELADO | TIMEOUT)
    if id_log is not None:
        try:
            registrar_fin_corrida(
                id_log=id_log,
                estado=estado_final,
                mensaje_error=msg_final if estado_final != "OK" else None,
            )
        except Exception:
            log.warning("No se pudo actualizar auditoría al finalizar")
            r_corrida.insertar_evento(
                id_corrida,
                "[ADVERTENCIA] Fallo al actualizar registro de auditoría al finalizar.",
                tipo="LOG",
            )

    log.info(
        "[RUNNER] Corrida finalizada",
        extra={"id_corrida": id_corrida, "estado": estado_final, "codigo": codigo_retorno},
    )

    if estado_final == "OK":
        EventBus.task_finished.send(
            "ejecutor",
            id_corrida=id_corrida,
            estado=estado_final,
            iniciado_por=iniciado_por,
        )
    else:
        EventBus.task_failed.send(
            "ejecutor",
            id_corrida=id_corrida,
            estado=estado_final,
            error=msg_final,
        )

    return estado_final
