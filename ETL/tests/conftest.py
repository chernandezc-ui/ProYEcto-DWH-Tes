"""
conftest.py (ETL/tests)
=======================
Las reglas de negocio configurables viven en Config.Parametros_Pipeline y el
codigo no trae valores por defecto. En las pruebas, la semilla de instalacion
(config/reglas_semilla.json) actua como si fuera esa tabla.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import reglas


@pytest.fixture(autouse=True)
def reglas_desde_semilla():
    reglas.usar_semilla_en_memoria()
    yield
    reglas.restaurar_fuente()
