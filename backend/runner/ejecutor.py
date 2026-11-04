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
import os
import queue
import re
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
# Tiempo máximo por paso individual del pipeline.
# Si un paso activo supera este límite sin producir output, se aborta la corrida.
_TIMEOUT_PASO_SEGUNDOS = 600


@dataclass
class _PasoActivo:
    id_paso: int
    nombre_paso: str
    orden: int
    cerrado: bool = False


def _resolver_python() -> str:
    """Resuelve el intérprete Python correcto dentro del venv activo."""
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        # Windows: Scripts/python.exe  |  Unix: bin/python
        for candidato in (
            Path(venv) / "Scripts" / "python.exe",
            Path(venv) / "bin" / "python",
        ):
            if candidato.exists():
                return str(candidato)
    # Fallback: uvicorn wrapper — tomar el python del mismo directorio
    exe = sys.executable
    if "uvicorn" in exe.lower():
        return str(Path(exe).parent / "python.exe")
    return exe


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


def _cerrar_paso_activo(
    paso_activo: _PasoActivo | None,
    *,
    estado: str,
    mensaje_error: str | None = None,
) -> None:
    if paso_activo is None or paso_activo.cerrado or paso_activo.id_paso < 0:
        return
    r_corrida.cerrar_paso(
        paso_activo.id_paso,
        estado=estado,
        mensaje_error=mensaje_error,
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
        env["PYTHONUNBUFFERED"] = "1"  # fuerza flush inmediato de stdout en el pipeline

        proceso = subprocess.Popen(
            [python_exe, "-u", str(_SCRIPT), *argumentos_pipeline],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(_DIR_ETL),
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
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
        ultimo_heartbeat = time.monotonic()
        deadline = time.monotonic() + timeout_segundos
        timestamp_inicio_paso: datetime | None = None
        # Métricas recolectadas pero pendientes de persistencia hasta que se aplique
        # backend/migrations/add_filas_to_corrida_paso.sql (columnas Filas_Procesadas, Filas_Rechazadas).
        _metricas_paso_actual: dict[str, int] = {"filas_procesadas": 0, "filas_rechazadas": 0}

        while True:
            ahora = time.monotonic()

            # ── Heartbeat y cancelación — se ejecuta aunque no haya output ──
            if ahora - ultimo_heartbeat >= heartbeat_intervalo_seg:
                r_corrida.actualizar_heartbeat_corrida(id_corrida, pid)
                r_lock.actualizar_heartbeat_lock(id_corrida=id_corrida)
                ultimo_heartbeat = ahora

                if r_corrida.corrida_fue_cancelada(id_corrida):
                    log.info("[RUNNER] Cancelación detectada, terminando proceso",
                             extra={"id_corrida": id_corrida})
                    proceso.terminate()
                    cancelado_por_heartbeat = True
                    break

                if timestamp_inicio_paso is not None:
                    seg_en_paso = (datetime.now() - timestamp_inicio_paso).total_seconds()
                    if seg_en_paso > _TIMEOUT_PASO_SEGUNDOS:
                        log.error(
                            "[EJECUTOR] Paso activo supera timeout (%ds) — abortando corrida",
                            _TIMEOUT_PASO_SEGUNDOS,
                            extra={"id_corrida": id_corrida, "segundos": int(seg_en_paso)},
                        )
                        proceso.terminate()
                        estado_final = "TIMEOUT"
                        break

            if ahora > deadline:
                log.warning("[RUNNER] Timeout alcanzado, terminando proceso",
                            extra={"id_corrida": id_corrida})
                proceso.terminate()
                estado_final = "TIMEOUT"
                break

            # ── Leer múltiples líneas de la cola (batching) ──
            lineas = []
            try:
                # Esperamos hasta 1s por la primera línea
                linea_inicial = cola_stdout.get(timeout=1.0)
                if linea_inicial is not None:
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
                
                # Agregamos a la lista de inserción en batch
                eventos_batch.append({
                    "id_corrida": id_corrida,
                    "mensaje": linea_limpia,
                    "tipo": "LOG"
                })

                inicio_paso = _extraer_inicio_paso(linea_limpia)
                if inicio_paso is not None:
                    orden_paso, nombre_paso = inicio_paso
                    _cerrar_paso_activo(paso_activo, estado="OK")
                    paso_activo = _abrir_nuevo_paso(id_corrida, orden_paso, nombre_paso)
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
            proceso.kill()
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

    msg_final = (
        "Pipeline finalizado con éxito."
        if estado_final == "OK"
        else f"Pipeline terminó con estado {estado_final}. Código: {codigo_retorno}."
    )

    # Evento de cierre
    r_corrida.insertar_evento(id_corrida, f"[FIN] {msg_final}", tipo="FIN")

    _cerrar_paso_activo(
        paso_activo,
        estado="OK" if estado_final == "OK" else "ERROR",
        mensaje_error=msg_final if estado_final != "OK" else None,
    )

    # Actualizar Control.Corrida
    r_corrida.actualizar_estado_corrida(
        id_corrida=id_corrida,
        estado=estado_final,
        mensaje_final=msg_final,
    )

    # Actualizar Auditoria.Log_Carga
    if id_log is not None:
        try:
            registrar_fin_corrida(
                id_log=id_log,
                estado="OK" if estado_final == "OK" else "ERROR",
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
