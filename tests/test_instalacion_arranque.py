"""Instalación compartida y arranque de servicios sin efectos al importar."""

import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_instalador_crea_env_una_vez_y_no_sobrescribe(tmp_path, monkeypatch):
    import instalar

    monkeypatch.setattr(instalar, 'RAIZ', tmp_path)
    (tmp_path / '.env.example').write_text('ACP_JWT_SECRETO=\nDB_SERVIDOR=offline-test\n', encoding='utf-8')
    assert instalar.crear_env_si_falta()
    original = (tmp_path / '.env').read_bytes()
    assert len(original.splitlines()[0].split(b'=', 1)[1]) >= 32
    assert not instalar.crear_env_si_falta()
    assert (tmp_path / '.env').read_bytes() == original


def test_instalacion_invoca_solo_requirements_global(tmp_path, monkeypatch):
    import instalar

    monkeypatch.setattr(instalar, 'RAIZ', tmp_path)
    monkeypatch.setattr(instalar, 'python_compartido', lambda: Path(sys.executable))
    monkeypatch.setattr(instalar, 'crear_env_si_falta', lambda: False)
    monkeypatch.setattr(sys, 'argv', ['instalar.py', '--no-index'])
    run = Mock()
    monkeypatch.setattr(instalar.subprocess, 'run', run)
    instalar.main()
    assert run.call_args_list[0].args[0] == [sys.executable, '-m', 'pip', 'install', '-r', str(tmp_path / 'requirements.txt'), '--no-index']
    assert run.call_args_list[1].args[0] == [sys.executable, '-m', 'pip', 'check']
    assert run.call_count == 2


def config(**overrides):
    values = dict(host='127.0.0.1', puerto=8810, runner_activo=False, db_driver='ACP_OFFLINE_NO_DATABASE', reload=False, workers=1)
    return SimpleNamespace(**(values | overrides))


def test_importar_lanzador_no_inicia_procesos_ni_instala_senales(monkeypatch):
    import logging.handlers
    import signal

    forbidden = Mock(side_effect=AssertionError('efecto durante importación'))
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(signal, 'signal', forbidden)
    monkeypatch.setattr(logging.handlers, 'RotatingFileHandler', forbidden)
    runpy.run_path(str(ROOT / 'acp_start.py'))
    forbidden.assert_not_called()


def test_servicios_comparten_interprete_y_no_presuponen_portal():
    import acp_start

    services = acp_start.construir_servicios(config(runner_activo=True, db_driver='ODBC Driver 17 for SQL Server'))
    assert [service['nombre'] for service in services] == ['Backend FastAPI', 'Runner ETL']
    assert all(service['cmd'][0] == sys.executable for service in services)
    assert len(acp_start.construir_servicios(config())) == 1
    with pytest.raises(ValueError, match='SQL Server real'):
        acp_start.construir_servicios(config(runner_activo=True))


def test_runner_espera_readiness_antes_de_iniciar(monkeypatch):
    import acp_start

    services = acp_start.construir_servicios(config(runner_activo=True, db_driver='ODBC Driver 17 for SQL Server'))
    monkeypatch.setattr(acp_start, 'SERVICIOS', services)
    start = Mock(return_value=True)
    monkeypatch.setattr(acp_start, 'iniciar_servicio', start)
    monkeypatch.setattr(acp_start, 'esperar_health', Mock(side_effect=[True, False]))
    assert not acp_start.arrancar_servicios()
    start.assert_called_once_with(services[0])


def test_no_termina_procesos_ajenos_si_el_puerto_esta_ocupado(monkeypatch):
    import acp_start

    monkeypatch.setattr(acp_start, 'puerto_en_uso', lambda port: True)
    spawn = Mock()
    monkeypatch.setattr(acp_start.subprocess, 'Popen', spawn)
    assert not acp_start.iniciar_servicio(acp_start.construir_servicios(config())[0])
    spawn.assert_not_called()


def test_etl_usa_python_del_runner_aunque_virtual_env_sea_otro(tmp_path, monkeypatch):
    from runner.ejecutor import _resolver_python

    other = tmp_path / 'other'
    (other / 'bin').mkdir(parents=True)
    (other / 'bin/python').touch()
    monkeypatch.setenv('VIRTUAL_ENV', str(other))
    assert _resolver_python() == sys.executable


def test_lanzador_real_comprueba_api_sin_bd_y_cierra_proceso():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    env = os.environ | {'ACP_PUERTO': str(port), 'ACP_HOST': '127.0.0.1', 'ACP_RUNNER_ACTIVO': 'false', 'DB_DRIVER': 'ACP_OFFLINE_NO_DATABASE'}
    result = subprocess.run([sys.executable, 'acp_start.py', '--comprobar'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Backend FastAPI' in result.stdout and 'Servicios detenidos' in result.stdout
    with pytest.raises(OSError):
        socket.create_connection(('127.0.0.1', port), timeout=1)
