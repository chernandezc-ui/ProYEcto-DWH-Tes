"""
nucleo/cache.py
===============
Caché SQLite en modo WAL con protección asyncio.

- Las operaciones de lectura/escritura son síncronas (SQLite no tiene driver async).
- Se protegen con threading.Lock para acceso concurrente seguro desde múltiples
  threads del threadpool de FastAPI (asyncio.to_thread).
- limpiar_todo() es thread-safe y no genera condiciones de carrera bajo carga.
"""

import json
import os
import sqlite3
import threading
import time
from typing import Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cache_portal.db")


class CacheAlpha:
    """
    Caché de alta velocidad basada en SQLite (WAL Mode).
    Thread-safe mediante threading.Lock + conexión persistente por thread.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._local = threading.local()
        self._inicializar_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return self._local.conn

    def _inicializar_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_sistema (
                    clave      TEXT PRIMARY KEY,
                    valor      TEXT,
                    expiracion INTEGER
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expiracion ON cache_sistema (expiracion)"
            )
            conn.execute(
                "DELETE FROM cache_sistema WHERE expiracion < ?",
                (int(time.time()),),
            )

    def guardar(self, clave: str, valor: Any, ttl_segundos: int = 3600) -> None:
        expiracion = int(time.time()) + ttl_segundos
        valor_json = json.dumps(valor, default=str)
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache_sistema (clave, valor, expiracion) VALUES (?, ?, ?)",
                (clave, valor_json, expiracion),
            )

    def obtener(self, clave: str) -> Optional[Any]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT valor FROM cache_sistema WHERE clave = ? AND expiracion > ?",
                (clave, int(time.time())),
            )
            fila = cursor.fetchone()
        return json.loads(fila[0]) if fila else None

    def eliminar(self, clave: str) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM cache_sistema WHERE clave = ?", (clave,))

    def limpiar_todo(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM cache_sistema")

    def limpiar_por_prefijo(self, prefijo: str) -> int:
        """
        Borra todas las claves que empiecen por `prefijo`.
        Útil para invalidación granular: tras un PATCH de cuarentena
        no necesitamos tirar la caché de ETL/catálogos/auditoría.
        Retorna la cantidad de filas borradas.
        """
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM cache_sistema WHERE clave LIKE ?",
                (f"{prefijo}%",),
            )
            return cursor.rowcount or 0


cache = CacheAlpha()
