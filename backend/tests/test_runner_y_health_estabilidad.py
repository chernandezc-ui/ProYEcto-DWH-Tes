"""Pruebas unitarias aisladas para estabilidad del health check, runner y telemetría estructurada."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_DIR_BACKEND = Path(__file__).resolve().parents[1]
if str(_DIR_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DIR_BACKEND))

from api import rutas_health
from runner import ejecutor


def test_readiness_runner_y_lock_serializan_datetime(monkeypatch):
    ahora = datetime(2026, 11, 24, 9, 0, 0)
    monkeypatch.setattr(
        rutas_health,
        "verificar_conexion",
        lambda: {"conectado": True, "base_datos": "ACP_TEST", "latencia_ms": 5},
    )
    monkeypatch.setattr(
        rutas_health,
        "obtener_resumen_control_plane",
        lambda: {"corridas_activas": 1, "comandos_pendientes": 0, "comandos_procesando": 1},
    )
    monkeypatch.setattr(
        rutas_health,
        "obtener_estado_lock",
        lambda: {
            "id_lock": 1,
            "id_corrida_activa": "cid-123",
            "adquirido_por": "TEST-HOST",
            "fecha_adquisicion": ahora,
            "heartbeat": ahora,
            "estado_lock": "ACTIVO",
            "segundos_desde_heartbeat": 2,
        },
    )

    resp_runner = rutas_health.readiness_runner()
    assert resp_runner.status_code == 200
    body_runner = json.loads(resp_runner.body.decode("utf-8"))
    assert body_runner["estado"] == "ocupado"
    assert body_runner["control_plane"]["lock"]["fecha_adquisicion"].startswith("2026-11-24T09:00:00")

    resp_lock = rutas_health.estado_lock()
    assert resp_lock.status_code == 200
    body_lock = json.loads(resp_lock.body.decode("utf-8"))
    assert body_lock["estado"] == "activo"
    assert body_lock["lock"]["heartbeat"].startswith("2026-11-24T09:00:00")


def test_parsear_evento_estructurado():
    ok = ejecutor._parsear_evento_estructurado(
        '@@ACP_EVENT {"tipo":"fact_fin","fact":"Fact_Cosecha_SAP","estado":"OK","insertados":42}'
    )
    assert ok is not None
    assert ok["fact"] == "Fact_Cosecha_SAP"
    assert ok["insertados"] == 42

    assert ejecutor._parsear_evento_estructurado("linea normal de log") is None
    assert ejecutor._parsear_evento_estructurado("@@ACP_EVENT {json roto") is None


def test_ejecutor_rastrea_facts_paralelas_independientes(monkeypatch):
    pasos_insertados: list[tuple[int, str, int]] = []
    pasos_cerrados: list[dict] = []
    eventos_guardados: list[dict] = []
    fin_auditoria: list[dict] = []

    def fake_insertar_paso(_cid, nombre_paso, orden=1):
        pid = len(pasos_insertados) + 1
        pasos_insertados.append((pid, nombre_paso, orden))
        return pid

    def fake_cerrar_paso(id_paso, estado, mensaje_error=None, filas_procesadas=0, filas_rechazadas=0):
        pasos_cerrados.append({
            "id_paso": id_paso,
            "estado": estado,
            "mensaje_error": mensaje_error,
            "filas_procesadas": filas_procesadas,
            "filas_rechazadas": filas_rechazadas,
        })

    monkeypatch.setattr(ejecutor, "registrar_inicio_corrida", lambda **_kw: 99)
    monkeypatch.setattr(ejecutor, "registrar_fin_corrida", lambda **kw: fin_auditoria.append(kw))
    monkeypatch.setattr(ejecutor.r_corrida, "actualizar_estado_corrida", lambda **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "insertar_evento", lambda *_a, **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "insertar_eventos_batch", lambda batch: eventos_guardados.extend(batch))
    monkeypatch.setattr(ejecutor.r_corrida, "insertar_paso", fake_insertar_paso)
    monkeypatch.setattr(ejecutor.r_corrida, "cerrar_paso", fake_cerrar_paso)
    monkeypatch.setattr(ejecutor.r_corrida, "actualizar_heartbeat_corrida", lambda *_a, **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "corrida_fue_cancelada", lambda _cid: False)
    monkeypatch.setattr(ejecutor.r_lock, "actualizar_heartbeat_lock", lambda **_kw: None)
    monkeypatch.setattr(ejecutor.EventBus.task_finished, "send", lambda *_a, **_kw: None)

    lineas_sim = [
        '@@ACP_EVENT {"tipo":"fact_inicio","fact":"Fact_A","orden":1}\n',
        '@@ACP_EVENT {"tipo":"fact_inicio","fact":"Fact_B","orden":2}\n',
        '@@ACP_EVENT {"tipo":"fact_fin","fact":"Fact_B","estado":"ERROR","insertados":0,"rechazados":12,"duracion_seg":1.2,"mensaje":"Fallo B"}\n',
        '@@ACP_EVENT {"tipo":"fact_fin","fact":"Fact_A","estado":"OK","insertados":350,"rechazados":3,"duracion_seg":2.1,"mensaje":""}\n',
    ]

    fake_proc = MagicMock()
    fake_proc.pid = 12345
    fake_proc.stdout = iter(lineas_sim)
    fake_proc.returncode = 0
    fake_proc.wait.return_value = 0
    monkeypatch.setattr(ejecutor.subprocess, "Popen", lambda *_a, **_kw: fake_proc)

    estado = ejecutor.ejecutar_corrida(
        id_corrida="cid-paralelo-1",
        iniciado_por="carlos.admin",
        timeout_segundos=60,
        heartbeat_intervalo_seg=30,
        timeout_arranque_segundos=30,
    )

    assert estado == "OK"
    assert len(pasos_insertados) == 2
    assert {p[1] for p in pasos_insertados} == {"Fact: Fact_A", "Fact: Fact_B"}
    cerrados_por_id = {p["id_paso"]: p for p in pasos_cerrados}
    # Fact_A (id 1) cerró OK con 350 insertados; Fact_B (id 2) cerró ERROR con 12 rechazados
    assert cerrados_por_id[1]["estado"] == "OK"
    assert cerrados_por_id[1]["filas_procesadas"] == 350
    assert cerrados_por_id[2]["estado"] == "ERROR"
    assert cerrados_por_id[2]["filas_rechazadas"] == 12
    assert "Fallo B" in (cerrados_por_id[2]["mensaje_error"] or "")
    assert fin_auditoria[-1]["estado"] == "OK"


def test_ejecutor_dispara_watchdog_de_arranque_sin_output(monkeypatch):
    terminado = []
    fin_auditoria = []

    monkeypatch.setattr(ejecutor, "registrar_inicio_corrida", lambda **_kw: 100)
    monkeypatch.setattr(ejecutor, "registrar_fin_corrida", lambda **kw: fin_auditoria.append(kw))
    monkeypatch.setattr(ejecutor.r_corrida, "actualizar_estado_corrida", lambda **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "insertar_evento", lambda *_a, **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "insertar_eventos_batch", lambda *_a, **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "actualizar_heartbeat_corrida", lambda *_a, **_kw: None)
    monkeypatch.setattr(ejecutor.r_corrida, "corrida_fue_cancelada", lambda _cid: False)
    monkeypatch.setattr(ejecutor.r_lock, "actualizar_heartbeat_lock", lambda **_kw: None)
    monkeypatch.setattr(ejecutor.EventBus.task_failed, "send", lambda *_a, **_kw: None)
    monkeypatch.setattr(ejecutor, "_terminar_arbol_proceso", lambda proc: terminado.append(proc.pid))

    class SilentStdout:
        def __iter__(self):
            time.sleep(2.5)
            return iter([])

    fake_proc = MagicMock()
    fake_proc.pid = 77777
    fake_proc.stdout = SilentStdout()
    fake_proc.returncode = 1
    fake_proc.wait.return_value = 1
    monkeypatch.setattr(ejecutor.subprocess, "Popen", lambda *_a, **_kw: fake_proc)

    estado = ejecutor.ejecutar_corrida(
        id_corrida="cid-hang-1",
        iniciado_por="carlos.admin",
        timeout_segundos=60,
        heartbeat_intervalo_seg=30,
        timeout_arranque_segundos=1,
    )

    assert estado == "TIMEOUT"
    assert terminado == [77777]
    assert fin_auditoria[-1]["estado"] == "TIMEOUT"


def test_runner_sobrevive_error_transitorio_al_consultar_cola(monkeypatch):
    from runner import runner as runner_mod

    intentos = {"n": 0}
    esperas: list[float] = []

    def fake_tomar():
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise RuntimeError("SQL Server reiniciándose")
        runner_mod._continuar = False
        return None

    monkeypatch.setattr(runner_mod, "_limpiar_corridas_huerfanas", lambda: None)
    monkeypatch.setattr(runner_mod.r_cmd, "tomar_comando_pendiente", fake_tomar)
    monkeypatch.setattr(runner_mod.time, "sleep", lambda seg: esperas.append(seg))
    monkeypatch.setattr(runner_mod, "_continuar", True)

    runner_mod._ciclo_principal()

    assert intentos["n"] == 2
    assert esperas and esperas[0] == 5


def test_rutas_etl_detecta_xlsx_case_insensitive_e_ignora_temporales(tmp_path):
    _dir_etl = Path(__file__).resolve().parents[2] / "ETL"
    if str(_dir_etl) not in sys.path:
        sys.path.insert(0, str(_dir_etl))

    from bronce.rutas import obtener_archivo_mas_reciente

    (tmp_path / "~$Bloqueado.xlsx").write_bytes(b"temp")
    mayus = tmp_path / "REPORTE_CAMPO.XLSX"
    mayus.write_bytes(b"real")

    encontrado = obtener_archivo_mas_reciente(tmp_path)
    assert encontrado is not None
    assert encontrado.name == "REPORTE_CAMPO.XLSX"


def test_conexion_soporta_odbc_driver_18_con_trust_cert(tmp_path, monkeypatch):
    from comun import configuracion, conexion

    monkeypatch.setattr(configuracion, "ENV_GLOBAL", tmp_path / "absent.env")
    cs = conexion._construir_cadena_pyodbc(
        servidor="sqlserver,1433",
        base="ACP_DWH",
        usuario="sa",
        clave="Secret123!",
        driver="ODBC Driver 18 for SQL Server",
    )
    assert "DRIVER={ODBC Driver 18 for SQL Server};" in cs
    assert "SERVER=sqlserver,1433;" in cs
    assert "TrustServerCertificate=yes;" in cs


def test_terminar_arbol_proceso_en_posix_usa_killpg(monkeypatch):
    sent_signals: list[tuple[int, int]] = []
    fake_proc = MagicMock()
    fake_proc.pid = 4321
    fake_proc.poll.return_value = None
    fake_proc.wait.return_value = 0

    monkeypatch.setattr(ejecutor.sys, "platform", "linux")
    monkeypatch.setattr(ejecutor.os, "getpgid", lambda pid: pid + 1000, raising=False)
    monkeypatch.setattr(
        ejecutor.os,
        "killpg",
        lambda pgid, sig: sent_signals.append((pgid, sig)),
        raising=False,
    )

    ejecutor._terminar_arbol_proceso(fake_proc)
    assert sent_signals == [(5321, ejecutor.signal.SIGTERM)]

