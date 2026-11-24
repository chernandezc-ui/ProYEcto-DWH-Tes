"""
reglas.py
=========
Acceso a las reglas de negocio CONFIGURABLES del ETL.

Principio: los valores que cambian con el tiempo (umbrales, ventanas de campana,
listas de dominios, mapeos de vocabulario ...) viven en la base de datos, no en
el codigo. Todo se guarda en la tabla que ya existia: Config.Parametros_Pipeline.

  * escalar  -> Valor = "0.85"
  * lista    -> Valor = JSON array o texto separado por , ; |   ["a", "b"]
  * mapeo    -> Valor = JSON object                              {"BUENAS": "1"}

Este modulo NO tiene valores por defecto: si falta una regla requerida lanza
ErrorConfiguracion con el nombre exacto y como sembrarla. Nada se lee al importar;
todo se resuelve al momento de uso.

La semilla de instalacion (config/reglas_semilla.json) solo se usa para poblar la
base con 'py tools/sembrar_reglas.py' y como fuente en memoria en las pruebas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import text

RUTA_SEMILLA = Path(__file__).with_name('reglas_semilla.json')
AYUDA_SEMBRAR = "Ejecute 'py tools/sembrar_reglas.py' (desde ETL/) para cargar las reglas faltantes."
MAX_LONGITUD_VALOR = 500          # Config.Parametros_Pipeline.Valor es NVARCHAR(500)

_fuente_memoria: dict[str, str] | None = None   # solo pruebas
_cache_parseados: dict[tuple[str, str], Any] = {}  # listas/mapeos ya interpretados


class ErrorConfiguracion(RuntimeError):
    """Falta o es invalida una regla de negocio requerida."""


# ── fuente de datos ────────────────────────────────────────────────────────

def cargar_semilla() -> dict:
    with open(RUTA_SEMILLA, encoding='utf-8') as archivo:
        return json.load(archivo)


def serializar_valor(valor: Any) -> str:
    """Texto que se guarda en Parametros_Pipeline.Valor para un valor de la semilla."""
    if isinstance(valor, (list, dict)):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def usar_fuente_en_memoria(parametros: dict[str, Any] | None = None) -> None:
    """Reemplaza la base por un diccionario en memoria (pruebas)."""
    global _fuente_memoria
    _fuente_memoria = {k: serializar_valor(v) for k, v in (parametros or {}).items()}
    limpiar_cache()


def usar_semilla_en_memoria() -> None:
    """Pruebas: la semilla de instalacion actua como si fuera la base."""
    usar_fuente_en_memoria({p['nombre']: p['valor'] for p in cargar_semilla()['parametros']})


def restaurar_fuente() -> None:
    global _fuente_memoria
    _fuente_memoria = None
    limpiar_cache()


def limpiar_cache() -> None:
    """Descarta las listas/mapeos ya interpretados. Se llama junto con config.parametros.limpiar_cache()."""
    _cache_parseados.clear()


# ── lectura ────────────────────────────────────────────────────────────────

def _todos_los_parametros() -> dict[str, str]:
    if _fuente_memoria is not None:
        return _fuente_memoria
    from config.parametros import cargar_parametros
    return cargar_parametros()


def parametro_opcional(nombre: str) -> str | None:
    valor = _todos_los_parametros().get(nombre)
    if valor is None or str(valor).strip() == '':
        return None
    return str(valor).strip()


def parametro(nombre: str) -> str:
    valor = parametro_opcional(nombre)
    if valor is None:
        raise ErrorConfiguracion(
            f"Falta el parametro '{nombre}' en Config.Parametros_Pipeline. {AYUDA_SEMBRAR}")
    return valor


def _convertir(nombre: str, valor: str, convertir: Callable[[float], Any]):
    try:
        return convertir(float(valor.replace(',', '.')))
    except (ValueError, TypeError, OverflowError) as error:
        raise ErrorConfiguracion(
            f"El parametro '{nombre}'='{valor}' no es numerico valido.") from error


def parametro_float(nombre: str) -> float:
    return _convertir(nombre, parametro(nombre), float)


def parametro_int(nombre: str) -> int:
    return _convertir(nombre, parametro(nombre), int)


def lista(nombre: str) -> list[str]:
    """Parametro de tipo lista (JSON array o separadores , ; |)."""
    clave = ('lista', nombre)
    if clave not in _cache_parseados:
        crudo = parametro(nombre)
        items = None
        if crudo.startswith('['):
            try:                                   # JSON: conserva elementos vacios ("")
                datos = json.loads(crudo)
                if isinstance(datos, list):
                    items = [str(x) for x in datos]
            except json.JSONDecodeError:
                pass
        if items is None:
            from config.parametros import parsear_lista
            items = parsear_lista(crudo)
        if not items:
            raise ErrorConfiguracion(f"El parametro '{nombre}' no contiene elementos.")
        _cache_parseados[clave] = tuple(items)
    return list(_cache_parseados[clave])


def conjunto(nombre: str) -> frozenset[str]:
    clave = ('conjunto', nombre)
    if clave not in _cache_parseados:
        _cache_parseados[clave] = frozenset(lista(nombre))
    return _cache_parseados[clave]


def _objeto_json(nombre: str) -> dict:
    try:
        datos = json.loads(parametro(nombre))
    except json.JSONDecodeError as error:
        raise ErrorConfiguracion(f"El parametro '{nombre}' no es un JSON valido: {error}") from error
    if not isinstance(datos, dict) or not datos:
        raise ErrorConfiguracion(f"El parametro '{nombre}' debe ser un objeto JSON no vacio.")
    return datos


def mapeo(nombre: str) -> dict[str, str]:
    """Parametro de tipo mapeo: JSON object clave -> valor (texto)."""
    clave = ('mapeo', nombre)
    if clave not in _cache_parseados:
        _cache_parseados[clave] = {str(k): str(v) for k, v in _objeto_json(nombre).items()}
    return dict(_cache_parseados[clave])


# ── verificacion y siembra ─────────────────────────────────────────────────

def verificar_completitud(engine) -> None:
    """
    Comprueba contra la BASE que existan todas las reglas requeridas por la
    semilla y que los umbrales del breaker sean coherentes para cada fact.
    Lanza ErrorConfiguracion con TODO lo que falte, para corregirlo de una vez.
    """
    semilla = cargar_semilla()
    with engine.connect() as conexion:
        parametros = {
            str(n): str(v) for n, v in conexion.execute(
                text("SELECT Nombre_Parametro, Valor FROM Config.Parametros_Pipeline")).fetchall()
        }

    faltantes = [
        p['nombre'] for p in semilla['parametros']
        if p.get('requerido', True) and not parametros.get(p['nombre'], '').strip()
    ]
    if faltantes:
        raise ErrorConfiguracion(
            "Reglas de negocio faltantes en Config.Parametros_Pipeline:\n  - "
            + "\n  - ".join(faltantes) + f"\n{AYUDA_SEMBRAR}")

    # Coherencia con los datos reales de la base (no con la semilla).
    usar_fuente_en_memoria(parametros)
    try:
        from utils.circuit_breaker import resolver_umbrales
        from utils.ejecucion import CONFIG_FACTS
        problemas = []
        for nombre in CONFIG_FACTS:
            try:
                resolver_umbrales(nombre)
            except ErrorConfiguracion as error:
                problemas.append(f"{nombre}: {error}")
        for p in semilla['parametros']:
            if isinstance(p['valor'], (list, dict)):
                try:
                    (lista if isinstance(p['valor'], list) else mapeo)(p['nombre'])
                except ErrorConfiguracion as error:
                    problemas.append(str(error))
        if problemas:
            raise ErrorConfiguracion("Reglas invalidas:\n  - " + "\n  - ".join(problemas))
    finally:
        restaurar_fuente()


def sembrar(engine) -> int:
    """
    Inserta en Config.Parametros_Pipeline los parametros de la semilla que falten.
    Nunca modifica ni borra uno existente. Devuelve cuantos inserto.
    """
    insertados = 0
    with engine.begin() as conexion:
        existentes = {r[0] for r in conexion.execute(
            text("SELECT Nombre_Parametro FROM Config.Parametros_Pipeline")).fetchall()}
        for p in cargar_semilla()['parametros']:
            if p['nombre'] in existentes:
                continue
            valor = serializar_valor(p['valor'])
            if len(valor) > MAX_LONGITUD_VALOR:
                raise ErrorConfiguracion(
                    f"El valor de '{p['nombre']}' mide {len(valor)} caracteres (maximo {MAX_LONGITUD_VALOR}).")
            conexion.execute(text("""
                INSERT INTO Config.Parametros_Pipeline
                    (Nombre_Parametro, Valor, Descripcion, Fecha_Modificacion, Modificado_Por)
                VALUES (:n, :v, :d, SYSDATETIME(), 'SEMILLA')
            """), {'n': p['nombre'], 'v': valor, 'd': p.get('descripcion')})
            insertados += 1
    return insertados
