"""
comun/conexion.py
=================
Engine SQLAlchemy compartido por ETL y backend.

Reemplaza dos implementaciones divergentes que existian:
- ETL/config/conexion.py (singleton manual + os.getenv + pool tuned)
- backend/nucleo/conexion.py (lru_cache + settings)

Configuración canónica en comun/configuracion.py; un .env en la raíz y
overrides explícitos para tests. Cada proceso conserva su propio pool.
"""

from __future__ import annotations

import threading
import urllib
import warnings
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning

from comun import configuracion

warnings.filterwarnings(
    "ignore",
    message=r"Unrecognized server version info '17\..*'\.  ?Some SQL Server features may not function properly\.",
    category=SAWarning,
)

_engine: Engine | None = None
_engine_lock = threading.Lock()


def _construir_cadena_pyodbc(
    *,
    servidor: str | None = None,
    base: str | None = None,
    usuario: str | None = None,
    clave: str | None = None,
    driver: str | None = None,
) -> str:
    overrides = {key: value for key, value in {
        'DB_SERVIDOR': servidor, 'DB_NOMBRE': base, 'DB_USUARIO': usuario,
        'DB_CLAVE': clave, 'DB_DRIVER': driver,
    }.items() if value is not None}
    config = (
        configuracion.ConfiguracionBD(_env_file=configuracion.ENV_GLOBAL, **overrides)
        if overrides else configuracion.obtener_configuracion_bd()
    )
    servidor, base = config.db_servidor, config.db_nombre
    usuario, clave, driver = config.db_usuario, config.db_clave, config.db_driver

    # El driver legacy "SQL Server" (el que viene preinstalado en Windows)
    # NO soporta `TrustServerCertificate`. Si alguien lo configura, pyodbc
    # devuelve "Atributo de cadena de conexión no válido (0)" + login
    # timeout. Lo detectamos por nombre y omitimos el atributo en ese caso.
    es_driver_legacy = driver.strip().lower() == "sql server"
    trust_cert = "" if es_driver_legacy else "TrustServerCertificate=yes;"

    if not usuario:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={servidor};"
            f"DATABASE={base};"
            f"Trusted_Connection=yes;"
            f"{trust_cert}"
        )
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={servidor};"
        f"DATABASE={base};"
        f"UID={usuario};"
        f"PWD={clave};"
        f"{trust_cert}"
    )


def obtener_engine(**override: Any) -> Engine:
    """
    Retorna el engine singleton del proceso. Thread-safe.

    Pool calibrado para una corrida ETL larga (pool_recycle=1800 evita
    desconexiones por idle del SQL Server) y backend concurrente.

    Llamar con kwargs solo en tests; en produccion pasa por env vars.
    """
    global _engine
    if _engine is not None and not override:
        return _engine

    with _engine_lock:
        if _engine is not None and not override:
            return _engine

        cadena_pyodbc = _construir_cadena_pyodbc(**override)
        cadena_url = (
            "mssql+pyodbc:///?odbc_connect="
            + urllib.parse.quote_plus(cadena_pyodbc)
        )
        engine = create_engine(
            cadena_url,
            fast_executemany=True,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        if not override:
            _engine = engine
        return engine


def resetear_engine() -> None:
    """Descarta el singleton y cierra el pool. Usar solo en tests."""
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
        configuracion.obtener_configuracion_bd.cache_clear()


def verificar_conexion() -> dict:
    """
    Ping liviano contra la BD.
    Retorna dict con estado, latencia y version. Nunca propaga excepciones.
    """
    import time
    info: dict = {"conectado": False, "base_datos": "-", "latencia_ms": "-"}
    try:
        inicio = time.perf_counter()
        with obtener_engine().connect() as conexion:
            fila = conexion.execute(
                text(
                    "SELECT DB_NAME() AS base_activa, "
                    "SERVERPROPERTY('ProductVersion') AS version_sql"
                )
            ).fetchone()
        fin = time.perf_counter()

        info["conectado"] = True
        info["base_datos"] = fila.base_activa  # type: ignore[union-attr]
        info["version"] = str(fila.version_sql)  # type: ignore[union-attr]
        info["latencia_ms"] = round((fin - inicio) * 1000, 1)
    except Exception as error:  # noqa: BLE001
        info["error"] = str(error)
    return info
