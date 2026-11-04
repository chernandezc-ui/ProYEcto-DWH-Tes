"""Regresión de descubrimiento, bloqueo SQL y selección del destino de prueba."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def policy_project(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ("conftest.py", "pytest.ini"):
        shutil.copyfile(root / name, tmp_path / name)
    (tmp_path / "tests").mkdir()
    return tmp_path


def run_pytest(project, *args):
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *args], cwd=project,
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "DB_SERVIDOR": "pretend-production", "DB_NOMBRE": "pretend-production", "ACP_TEST_DB": "1"},
    )


def test_default_no_importa_herramientas_ni_permite_sqlserver(policy_project):
    (policy_project / "tests" / "test_policy.py").write_text('''
import os
import pyodbc
import pytest
from sqlalchemy import create_engine, text

def test_local():
    assert os.environ['DB_SERVIDOR'] == 'offline-test'
    assert os.environ['DB_NOMBRE'] == 'offline-test'
    with pytest.raises(RuntimeError, match='SQL Server bloqueado'):
        pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=unused')
    with pytest.raises(RuntimeError, match='SQL Server bloqueado'):
        create_engine('mssql+pyodbc:///?odbc_connect=SERVER%3Dunused').connect()
    with create_engine('sqlite://').begin() as connection:
        connection.execute(text('CREATE TABLE example (value INTEGER)'))
        connection.execute(text('INSERT INTO example VALUES (7)'))
        assert connection.execute(text('SELECT value FROM example')).scalar_one() == 7

@pytest.mark.sqlserver
def test_sql():
    pytest.fail('La integración no debe ejecutarse por defecto')
''', encoding="utf-8")
    tools = policy_project / "ETL" / "tools"
    tools.mkdir(parents=True)
    (tools / "test_manual.py").write_text("raise AssertionError('Se importó una herramienta manual')", encoding="utf-8")
    result = run_pytest(policy_project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed, 1 skipped" in result.stdout


@pytest.mark.parametrize("options", [
    ["--run-sqlserver"],
    ["--run-sqlserver", "--sqlserver-server", "test-host"],
    ["--run-sqlserver", "--sqlserver-server", "test-host", "--sqlserver-database", "production"],
    ["--sqlserver-server", "test-host", "--sqlserver-database", "ACP_TEST_fixture"],
    ["--run-sqlserver", "--sqlserver-server", "test-host;DATABASE=other", "--sqlserver-database", "ACP_TEST_fixture"],
])
def test_destino_ausente_o_no_aislado_es_error_de_uso(policy_project, options):
    result = run_pytest(policy_project, "--collect-only", *options)
    assert result.returncode == 4, result.stdout + result.stderr
    assert "ERROR:" in result.stderr


@pytest.mark.parametrize("actual, expected_code", [("ACP_TEST_fixture", 0), ("other_database", 1)])
def test_verifica_base_efectiva_antes_de_ejecutar_integracion(policy_project, actual, expected_code):
    # Adaptador sintético: estas pruebas nunca se conectan a una instancia SQL.
    common = policy_project / "comun"
    common.mkdir()
    (common / "__init__.py").write_text("", encoding="utf-8")
    (common / "conexion.py").write_text(f'''
from contextlib import contextmanager
from types import SimpleNamespace
class Engine:
    @contextmanager
    def connect(self):
        yield self
    def exec_driver_sql(self, sql):
        assert sql == 'SELECT DB_NAME()'
        return SimpleNamespace(scalar_one=lambda: {actual!r})
def obtener_engine():
    return Engine()
''', encoding="utf-8")
    (policy_project / "tests" / "test_sql.py").write_text('''
from pathlib import Path
import pytest
@pytest.mark.sqlserver
def test_sql():
    Path('test-body-ran').touch()
''', encoding="utf-8")
    result = run_pytest(
        policy_project, "--run-sqlserver", "--sqlserver-server", "test-host",
        "--sqlserver-database", "ACP_TEST_fixture",
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    assert (policy_project / "test-body-ran").exists() == (expected_code == 0)
    if expected_code:
        assert "base distinta" in result.stdout
