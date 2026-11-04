"""
parametros.py
=============
Lee Config.Parametros_Pipeline desde SQL Server.
El pipeline usa estos valores en tiempo de ejecución.
Cambiarlos en Streamlit afecta el comportamiento del ETL
sin tocar código.
"""

import json
import re

from sqlalchemy import text
import threading
from typing import Dict, Optional
from config.conexion import obtener_engine


_cache_parametros: Dict[str, str] = {}
_columna_param_cache: Optional[str] = None
_config_lock = threading.Lock()


def _resolver_columna_parametro(conexion) -> str:
    global _columna_param_cache
    if _columna_param_cache:
        return _columna_param_cache

    resultado = conexion.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Config'
          AND TABLE_NAME = 'Parametros_Pipeline'
    """))
    columnas = {
        str(fila[0]).strip()
        for fila in resultado.fetchall()
        if fila and fila[0]
    }

    if 'Parametro' in columnas:
        _columna_param_cache = 'Parametro'
    elif 'Nombre_Parametro' in columnas:
        _columna_param_cache = 'Nombre_Parametro'
    else:
        raise RuntimeError(
            'Config.Parametros_Pipeline no expone columna Parametro ni Nombre_Parametro.'
        )
    return _columna_param_cache


def cargar_parametros() -> dict[str, str]:
    """
    Carga todos los parámetros activos desde Config.Parametros_Pipeline.
    Thread-safe via _config_lock.
    """
    global _cache_parametros

    with _config_lock:
        if _cache_parametros:
            return _cache_parametros

        engine = obtener_engine()
        with engine.connect() as conexion:
            columna_parametro = _resolver_columna_parametro(conexion)
            resultado = conexion.execute(text(f"""
                SELECT {columna_parametro} AS Parametro, Valor
                FROM Config.Parametros_Pipeline
            """))
            _cache_parametros = {
                fila.Parametro: fila.Valor
                for fila in resultado.fetchall()
            }

    return _cache_parametros


def obtener(parametro: str, default: str = '') -> str:
    """
    Retorna el valor de un parámetro.
    Si no existe retorna el default indicado.
    """
    parametros = cargar_parametros()
    return parametros.get(parametro, default)


def obtener_int(parametro: str, default: int = 0) -> int:
    """
    Retorna el valor de un parámetro como entero.
    """
    try:
        return int(obtener(parametro, str(default)))
    except (ValueError, TypeError):
        return default


def obtener_float(parametro: str, default: float = 0.0) -> float:
    """
    Retorna el valor de un parámetro como float.
    """
    try:
        return float(obtener(parametro, str(default)))
    except (ValueError, TypeError):
        return default


def obtener_bool(parametro: str, default: bool = False) -> bool:
    """
    Retorna el valor de un parametro como booleano flexible.
    """
    valor = str(obtener(parametro, str(default))).strip().casefold()
    if valor in {'1', 'true', 't', 'si', 'sí', 'yes', 'y', 'on'}:
        return True
    if valor in {'0', 'false', 'f', 'no', 'n', 'off'}:
        return False
    return bool(default)


def obtener_lista(parametro: str, default: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """
    Retorna el valor de un parametro como lista de textos.

    Acepta JSON array o separadores comunes.
    """
    valor = obtener(parametro, '')
    if valor is None or str(valor).strip() == '':
        return [str(item).strip() for item in (default or []) if str(item).strip()]

    texto = str(valor).strip()
    if texto.startswith('[') and texto.endswith(']'):
        try:
            lista = json.loads(texto)
            if isinstance(lista, list):
                return [str(item).strip() for item in lista if str(item).strip()]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    partes = re.split(r'[\n,;|]+', texto)
    return [parte.strip() for parte in partes if parte and parte.strip()]


def limpiar_cache() -> None:
    """
    Limpia el cache — llamar al inicio de cada ejecución del pipeline.
    """
    global _cache_parametros
    _cache_parametros = {}


# ── Tokens de detección de filas no operativas en formularios de campo ──────
# Frágiles ante cambios en el Excel; centralizar aquí facilita el ajuste sin
# tocar la lógica de cada fact.

# Valores en la columna Fecha_Raw que indican una fila de encabezado/subtotal.
TOKENS_FECHA_NO_OPERATIVA: frozenset[str] = frozenset({
    '', 'NONE', 'PERSONAS', 'HORAS',
})

# Valores en la columna de supervisor/personal que indican fila administrativa.
TOKENS_SUPERVISOR_NO_OPERATIVO: frozenset[str] = frozenset({
    'AREA:', 'FECHA:', 'TURNO:', 'DIA:', 'DÍA:', 'NOCHE:', 'TOTAL',
})
