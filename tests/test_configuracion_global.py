"""Configuración de conexión única: precedencia, directorios y credenciales."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def clean_db_environment(monkeypatch):
    for key in ('DB_SERVIDOR', 'DB_NOMBRE', 'DB_USUARIO', 'DB_CLAVE', 'DB_DRIVER'):
        monkeypatch.delenv(key, raising=False)


def test_archivo_global_y_override_de_entorno(tmp_path, monkeypatch, clean_db_environment):
    from comun.configuracion import ConfiguracionBD

    env = tmp_path / '.env'
    env.write_text('DB_SERVIDOR=file-server\nDB_NOMBRE=file-db\nDB_USUARIO=file-user\nDB_CLAVE=synthetic-file-password\n', encoding='utf-8')
    monkeypatch.setenv('DB_NOMBRE', 'environment-db')
    config = ConfiguracionBD(_env_file=env)
    assert config.db_servidor == 'file-server'
    assert config.db_nombre == 'environment-db'
    assert config.db_usuario == 'file-user'
    assert config.db_clave == 'synthetic-file-password'
    assert 'synthetic-file-password' not in repr(config)
    assert 'DB_SERVIDOR' not in os.environ


def test_overrides_completos_no_necesitan_un_env(tmp_path, monkeypatch, clean_db_environment):
    from comun import configuracion, conexion

    monkeypatch.setattr(configuracion, 'ENV_GLOBAL', tmp_path / 'absent.env')
    sql = conexion._construir_cadena_pyodbc(servidor='explicit-server', base='explicit-db', usuario='')
    assert 'SERVER=explicit-server;' in sql and 'DATABASE=explicit-db;' in sql


def test_conexion_respeta_overrides_y_autenticacion_windows_explicita(tmp_path, monkeypatch, clean_db_environment):
    from comun import configuracion, conexion

    env = tmp_path / '.env'
    env.write_text('DB_SERVIDOR=file-server\nDB_NOMBRE=file-db\nDB_USUARIO=file-user\nDB_CLAVE=synthetic-file-password\n', encoding='utf-8')
    monkeypatch.setattr(configuracion, 'ENV_GLOBAL', env)
    configuracion.obtener_configuracion_bd.cache_clear()
    try:
        sql = conexion._construir_cadena_pyodbc(base='explicit-db', usuario='')
        assert 'DATABASE=explicit-db;' in sql
        assert 'SERVER=file-server;' in sql
        assert 'Trusted_Connection=yes;' in sql
        assert 'UID=' not in sql and 'PWD=' not in sql
    finally:
        configuracion.obtener_configuracion_bd.cache_clear()


@pytest.mark.parametrize('directory', ['.', 'backend', 'ETL'])
def test_backend_y_etl_resuelven_mismo_env_desde_cualquier_cwd(tmp_path, directory):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / 'comun', tmp_path / 'comun', ignore=shutil.ignore_patterns('__pycache__'))
    backend = tmp_path / 'backend'
    (backend / 'nucleo').mkdir(parents=True)
    shutil.copyfile(root / 'backend/nucleo/settings.py', backend / 'nucleo/settings.py')
    (tmp_path / 'ETL').mkdir()
    (tmp_path / '.env').write_text('DB_SERVIDOR=global-server\nDB_NOMBRE=global-db\nACP_JWT_SECRETO=synthetic-test-signing-key-at-least-32-chars\n', encoding='utf-8')
    (backend / '.env').write_text('DB_SERVIDOR=legacy-server\nDB_NOMBRE=legacy-db\n', encoding='utf-8')
    env = {key: value for key, value in os.environ.items() if not key.startswith(('DB_', 'ACP_'))}
    script = '''
import sys
sys.path[:0] = [sys.argv[1], sys.argv[1]+'/backend']
from comun.configuracion import obtener_configuracion_bd
from nucleo.settings import settings
db = obtener_configuracion_bd()
assert (db.db_servidor, db.db_nombre) == ('global-server', 'global-db')
assert (settings.db_servidor, settings.db_nombre) == (db.db_servidor, db.db_nombre)
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)], cwd=tmp_path / directory, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
