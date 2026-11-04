"""
nucleo/etl_catalogo.py
======================
Carga el manifiesto de facts del ETL sin duplicar configuración dentro del backend.
"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path


_RUTA_ETL_EJECUCION = Path(__file__).resolve().parents[2] / "ETL" / "utils" / "ejecucion.py"


@lru_cache(maxsize=1)
def _cargar_modulo_ejecucion():
    spec = importlib.util.spec_from_file_location("acp_etl_utils_ejecucion", _RUTA_ETL_EJECUCION)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el manifiesto ETL desde {_RUTA_ETL_EJECUCION}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def listar_facts_disponibles() -> list[dict]:
    modulo = _cargar_modulo_ejecucion()
    catalogo = []
    for nombre, meta in modulo.CONFIG_FACTS.items():
        catalogo.append({
            "nombre_fact": nombre,
            "orden": int(meta["orden"]),
            "tabla_destino": str(meta["tabla_destino"]),
            "fuentes_bronce": list(meta.get("fuentes_bronce", ())),
            "dependencias": list(meta.get("dependencias", ())),
            "marts": list(meta.get("marts", ())),
            "releer_bronce_por_estado": bool(meta.get("releer_bronce_por_estado", True)),
            "estrategia_rerun": str(meta.get("estrategia_rerun", "NO_DECLARADA")),
        })
    return catalogo


@lru_cache(maxsize=1)
def tablas_consultables() -> frozenset[str]:
    """
    Whitelist de tablas que un usuario puede previsualizar o exportar.

    Se deriva del propio manifiesto ETL: fuentes Bronce, tablas destino Silver
    y marts Gold declarados en CONFIG_FACTS. Esto excluye por diseño los
    esquemas sensibles (Seguridad, Auditoria, Control, MDM), cerrando el
    acceso indirecto a hashes de contraseñas o bitácoras (V-03 / IDOR).

    Los nombres se normalizan a minúsculas para comparación case-insensitive
    (SQL Server no distingue mayúsculas en identificadores por defecto).
    """
    permitidas: set[str] = set()
    for fact in listar_facts_disponibles():
        permitidas.add(fact["tabla_destino"].strip().lower())
        for origen in fact["fuentes_bronce"]:
            permitidas.add(str(origen).strip().lower())
        for mart in fact["marts"]:
            permitidas.add(str(mart).strip().lower())
    return frozenset(permitidas)


def es_tabla_consultable(tabla: str) -> bool:
    """True si `tabla` está en la whitelist derivada del catálogo ETL."""
    return tabla.strip().lower() in tablas_consultables()
