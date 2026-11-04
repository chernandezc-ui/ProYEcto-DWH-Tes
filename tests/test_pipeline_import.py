"""El punto de entrada debe importar en un proceso nuevo sin ejecutar cargas."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_pipeline_importa_sin_conectar_ni_cargar():
    root = Path(__file__).resolve().parents[1]
    script = """
import sys
from unittest.mock import patch
sys.path.insert(0, 'ETL')
with patch('sqlalchemy.create_engine', side_effect=AssertionError('SQL no permitido')) as engine, \\
     patch('pyodbc.connect', side_effect=AssertionError('ODBC no permitido')) as connect, \\
     patch('bronce.cargador.ejecutar_carga_bronce') as carga:
    import pipeline
    assert callable(pipeline.ejecutar)
    engine.assert_not_called()
    connect.assert_not_called()
    carga.assert_not_called()
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=root,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("path", ["ETL/test.py", "ETL/tools/test_campana_fisiologia.py"])
def test_importar_herramienta_manual_no_consulta_ni_carga(path):
    root = Path(__file__).resolve().parents[1]
    script = """
import runpy
import sys
from unittest.mock import patch
sys.path.insert(0, 'ETL')
with patch('sqlalchemy.create_engine') as engine, \\
     patch('pyodbc.connect') as connect, \\
     patch('silver.facts.fact_fisiologia.cargar_fact_fisiologia') as carga:
    runpy.run_path(sys.argv[1])
    engine.assert_not_called()
    connect.assert_not_called()
    carga.assert_not_called()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, path], cwd=root,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("path, failing_call", [
    ("ETL/test_sp_campana.py", "sql"),
    ("ETL/test_homologador_batch.py", "batch"),
])
def test_herramienta_manual_propaga_fallo(path, failing_call, monkeypatch):
    import runpy
    from unittest.mock import MagicMock

    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value.execute.side_effect = RuntimeError("fallo sintético")
    monkeypatch.setattr("config.conexion.obtener_engine", lambda: engine)
    if failing_call == "batch":
        monkeypatch.setattr("utils.contexto_transaccional.ContextoTransaccionalETL", MagicMock())
        monkeypatch.setattr(
            "mdm.homologador.registrar_homologaciones_batch",
            MagicMock(side_effect=RuntimeError("fallo sintético")),
        )
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / path))
    with pytest.raises(RuntimeError, match="fallo sintético"):
        namespace["main"]()
