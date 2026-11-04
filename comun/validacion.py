"""
comun/validacion.py
===================
Re-export de validadores canonicos del ETL para uso del backend.

Las implementaciones canonicas viven en ETL/utils/. Este modulo expone los
helpers a quien no esta dentro del paquete ETL (backend, scripts ad-hoc) sin
duplicar logica.
"""

from __future__ import annotations

import sys
from pathlib import Path

_DIR_ETL = Path(__file__).resolve().parent.parent / "ETL"
if str(_DIR_ETL) not in sys.path:
    sys.path.insert(0, str(_DIR_ETL))

from utils.dni import procesar_dni  # noqa: E402
from utils.fechas import (  # noqa: E402
    describir_rango_campana,
    obtener_politica_fecha,
    parsear_fecha,
    procesar_fecha,
    resolver_dominio_fecha,
)

__all__ = [
    "procesar_dni",
    "parsear_fecha",
    "procesar_fecha",
    "obtener_politica_fecha",
    "describir_rango_campana",
    "resolver_dominio_fecha",
]
