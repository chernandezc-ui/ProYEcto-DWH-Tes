"""
nucleo/conexion.py
==================
Compatibilidad: este modulo delega en comun/conexion.py.

La logica canonica vive en `comun/conexion.py` (compartida con ETL).
Mantenemos las firmas existentes para no tocar los call sites del backend.
"""

from __future__ import annotations

import sys
from pathlib import Path
from functools import lru_cache

_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine, resetear_engine, verificar_conexion  # noqa: E402


__all__ = ["obtener_engine", "resetear_engine", "verificar_conexion"]
