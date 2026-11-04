"""
migration_runner.py
===================
Runner para aplicar migraciones SQL con trazabilidad.

Lee los archivos .sql de sql_migrations/, calcula su hash SHA-256,
verifica contra Admin.Migraciones_Aplicadas y solo aplica los pendientes.

Uso:
    py tools/migration_runner.py                     # Aplica todas las pendientes
    py tools/migration_runner.py --dry-run           # Solo lista pendientes
    py tools/migration_runner.py --only fase28       # Aplica solo las que contengan 'fase28'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

# Agregar el directorio padre al path para poder importar config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.conexion import obtener_engine


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql_migrations"

# Solo se ejecutan archivos declarados, nunca SQL nuevo descubierto por glob.
_MANIFEST = "manifest.json"
_PROHIBIDOS = {"clear_all_data.sql", "consultas_dq_operativas.sql", "fase71_habilitar_rcsi.sql"}


def _calcular_hash(ruta: Path) -> str:
    """SHA-256 del contenido del archivo."""
    contenido = ruta.read_bytes()
    return hashlib.sha256(contenido).hexdigest()


def _tabla_migraciones_existe(engine: Engine) -> bool:
    """Verifica si Admin.Migraciones_Aplicadas ya fue creada."""
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT CASE 
                WHEN OBJECT_ID('Admin.Migraciones_Aplicadas', 'U') IS NULL 
                THEN 0 ELSE 1 
            END
        """)).scalar_one()
    return bool(resultado)


def _obtener_aplicadas(engine: Engine) -> dict[str, str]:
    with engine.connect() as conn:
        filas = conn.execute(text("""
            SELECT Nombre_Archivo, Hash_SHA256
            FROM Admin.Migraciones_Aplicadas WHERE Estado = 'OK'
        """)).fetchall()
    return {fila[0]: fila[1] for fila in filas}


def _listar_migraciones_disponibles() -> list[Path]:
    manifiesto = json.loads((MIGRATIONS_DIR / _MANIFEST).read_text(encoding="utf-8"))
    nombres = manifiesto["migrations"]
    if not isinstance(nombres, list) or len(nombres) != len(set(nombres)):
        raise ValueError("Manifiesto de migraciones invalido o con duplicados.")
    rutas = []
    for nombre in nombres:
        if (not isinstance(nombre, str) or Path(nombre).name != nombre
                or "/" in nombre or "\\" in nombre or not nombre.endswith(".sql")
                or nombre.casefold() in _PROHIBIDOS
                or nombre in manifiesto.get("manual_only", [])):
            raise ValueError(f"Migracion no permitida: {nombre!r}")
        ruta = MIGRATIONS_DIR / nombre
        if not ruta.is_file():
            raise ValueError(f"Migracion declarada inexistente: {nombre}")
        rutas.append(ruta)
    return rutas


def _separar_batches(contenido: str) -> list[str]:
    # GO solo es separador fuera de literales y comentarios de bloque.
    bloques, actual = [], []
    en_literal = False
    profundidad = 0
    for linea in contenido.splitlines(keepends=True):
        if not en_literal and not profundidad and re.fullmatch(r"\s*GO\s*(?:--[^\r\n]*)?[\r\n]*", linea, re.I):
            if "".join(actual).strip():
                bloques.append("".join(actual).strip())
            actual = []
            continue
        actual.append(linea)
        i = 0
        while i < len(linea):
            par = linea[i:i+2]
            if profundidad:
                if par == "/*": profundidad += 1; i += 2; continue
                if par == "*/": profundidad -= 1; i += 2; continue
            elif en_literal:
                if par == "''": i += 2; continue
                if linea[i] == "'": en_literal = False
            else:
                if par == "--": break
                if par == "/*": profundidad = 1; i += 2; continue
                if linea[i] == "'": en_literal = True
            i += 1
    if en_literal or profundidad:
        raise ValueError("SQL con literal o comentario sin cerrar.")
    if "".join(actual).strip(): bloques.append("".join(actual).strip())
    return bloques


def _registrar_resultado(conn, ruta, hash_archivo, inicio, estado, error_msg):
    _ejecutar_batch(conn, """
        DECLARE @nombre NVARCHAR(255) = ?, @hash NVARCHAR(64) = ?,
                @duracion FLOAT = ?, @estado NVARCHAR(20) = ?, @error NVARCHAR(MAX) = ?;
        IF NOT EXISTS (
            SELECT 1 FROM Admin.Migraciones_Aplicadas WHERE Nombre_Archivo = @nombre
        )
        INSERT INTO Admin.Migraciones_Aplicadas
            (Nombre_Archivo, Hash_SHA256, Duracion_Segundos, Estado, Mensaje_Error)
        VALUES (@nombre, @hash, @duracion, @estado, @error)
        ELSE
        UPDATE Admin.Migraciones_Aplicadas
        SET Hash_SHA256 = @hash, Duracion_Segundos = @duracion,
            Estado = @estado, Mensaje_Error = @error, Fecha_Aplicacion = GETDATE()
        WHERE Nombre_Archivo = @nombre
    """, (ruta.name, hash_archivo, round(time.time() - inicio, 2), estado, error_msg))


def _aplicar_migracion(engine: Engine, ruta: Path, hash_archivo: str) -> dict:
    """
    Ejecuta un archivo SQL contra la DB y registra el resultado.
    
    Nota: Los archivos con sentencias GO se separan en bloques
    ya que pyodbc no soporta GO nativamente.
    """
    contenido = ruta.read_text(encoding="utf-8-sig")
    bloques = _separar_batches(contenido)

    inicio = time.time()
    error_msg = None
    estado = "OK"
    try:
        with engine.begin() as conn:
            for bloque in bloques:
                _ejecutar_batch(conn, bloque)
            _registrar_resultado(conn, ruta, hash_archivo, inicio, "OK", None)
    except Exception as error:
        estado = "ERROR"
        error_msg = str(error)[:4000]
        # El error ya revirtio DDL/DML y su registro OK. Guardar diagnostico aparte.
        try:
            with engine.begin() as conn:
                _registrar_resultado(conn, ruta, hash_archivo, inicio, "ERROR", error_msg)
        except Exception as error_auditoria:
            error_msg += f" | No se pudo registrar auditoria: {error_auditoria}"
    return {
        "archivo": ruta.name,
        "estado": estado,
        "duracion": round(time.time() - inicio, 2),
        "error": error_msg,
    }


def _ejecutar_batch(conn, sql: str, parameters=None) -> None:
    """Consume todos los resultados: ODBC puede diferir errores a SQLMoreResults.

    Se usa el cursor de la misma transacción, sin commits DBAPI independientes.
    SQLAlchemy puede cerrar un resultado inicial sin filas antes de nextset().
    """
    cursor = conn.connection.cursor()
    try:
        if parameters is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, parameters)
        if hasattr(cursor, 'nextset'):
            while cursor.nextset():
                pass
    finally:
        cursor.close()


def ejecutar(
    dry_run: bool = False,
    filtro: str | None = None,
) -> list[dict]:
    """
    Punto de entrada principal del runner.
    
    Args:
        dry_run: Si True, solo lista pendientes sin aplicar.
        filtro: Substring para filtrar migraciones (ej. 'fase28').
    
    Returns:
        Lista de resultados por migración.
    """
    disponibles = _listar_migraciones_disponibles()
    engine = obtener_engine()
    
    # Verificar si la tabla de registro existe
    tabla_existe = _tabla_migraciones_existe(engine)
    
    if not tabla_existe:
        print("[WARN] Admin.Migraciones_Aplicadas no existe.")
        print("   Aplique primero: fase30_registro_migraciones.sql")
        if not dry_run:
            print("   Intentando aplicar fase30 automáticamente...")
            bootstrap = MIGRATIONS_DIR / "fase30_registro_migraciones.sql"
            if bootstrap in disponibles:
                resultado = _aplicar_migracion(engine, bootstrap, _calcular_hash(bootstrap))
                print(f"   Bootstrap: {resultado['estado']}")
                if resultado["estado"] != "OK":
                    print(f"   Error: {resultado['error']}")
                    return [resultado]
            else:
                print("   No se encontró fase30_registro_migraciones.sql")
                return []
    
    # Obtener estado actual
    aplicadas = _obtener_aplicadas(engine) if _tabla_migraciones_existe(engine) else {}
    for ruta in disponibles:
        previo = aplicadas.get(ruta.name)
        if previo and previo != "BOOTSTRAP" and previo != _calcular_hash(ruta):
            raise ValueError(f"Migracion aplicada modificada: {ruta.name}. Cree una nueva migracion.")
    
    # Filtrar si se especificó
    if filtro:
        disponibles = [d for d in disponibles if filtro.lower() in d.name.lower()]
    
    # Determinar pendientes
    pendientes = [d for d in disponibles if d.name not in aplicadas]
    
    if not pendientes:
        print("[OK] Todas las migraciones estan aplicadas.")
        return []
    
    print(f"\n{'=' * 60}")
    print(f"  Migraciones pendientes: {len(pendientes)}")
    print(f"{'=' * 60}")
    for p in pendientes:
        h = _calcular_hash(p)
        print(f"  [FILE] {p.name}  (SHA256: {h[:12]}...)")
    
    if dry_run:
        print(f"\n  [DRY RUN] No se aplicó ninguna migración.\n")
        return [{"archivo": p.name, "estado": "PENDIENTE"} for p in pendientes]
    
    print(f"\n  Aplicando migraciones...\n")
    resultados = []
    for ruta in pendientes:
        h = _calcular_hash(ruta)
        print(f"  [RUN] {ruta.name}...", end=" ", flush=True)
        resultado = _aplicar_migracion(engine, ruta, h)
        icono = "[OK]" if resultado["state" if "state" in resultado else "estado"] == "OK" else "[ERROR]"
        print(f"{icono} ({resultado['duracion']}s)")
        if resultado["error"]:
            print(f"     Error: {resultado['error'][:200]}")
        resultados.append(resultado)
        if resultado["estado"] != "OK":
            break  # No aplicar dependientes tras un fallo.
    
    ok = sum(1 for r in resultados if r["estado"] == "OK")
    err = sum(1 for r in resultados if r["estado"] == "ERROR")
    print(f"\n  Resultado: {ok} OK, {err} ERROR\n")
    
    return resultados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner de migraciones SQL con trazabilidad")
    parser.add_argument("--dry-run", action="store_true", help="Solo listar pendientes, no aplicar")
    parser.add_argument("--only", type=str, default=None, help="Filtrar por substring (ej. 'fase28')")
    args = parser.parse_args()
    
    resultados = ejecutar(dry_run=args.dry_run, filtro=args.only)
    
    errores = [r for r in resultados if r.get("estado") == "ERROR"]
    if errores:
        sys.exit(1)
