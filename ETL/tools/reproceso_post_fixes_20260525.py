"""
reproceso_post_fixes_20260525.py
================================
Orquesta el reproceso despues de aplicar los 3 fixes (Cosecha_SAP / Censo /
Ciclo_Poda) y de ejecutar el SQL de reparacion:
    ETL/sql_migrations/2026_05_25_repair_post_fixes.sql

Pasos:
  1. Verifica conexion a la BD.
  2. Ejecuta el SQL de reparacion (si --aplicar-sql).
  3. Re-corre los 3 procesadores Silver con la logica corregida.
  4. Refresca los Marts Gold afectados.
  5. Imprime un resumen con conteos antes/despues.

Uso (desde la carpeta ACP Proyecciones/):

    # Ver solo el plan, sin tocar nada:
    python ETL\\tools\\reproceso_post_fixes_20260525.py --dry-run

    # Aplicar SQL de reparacion + re-procesar:
    python ETL\\tools\\reproceso_post_fixes_20260525.py --aplicar-sql

    # Solo re-procesar (si ya corriste el SQL aparte):
    python ETL\\tools\\reproceso_post_fixes_20260525.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter

DIR_ETL = Path(__file__).resolve().parent.parent
DIR_PROYECTO = DIR_ETL.parent
sys.path.insert(0, str(DIR_ETL))
sys.path.insert(0, str(DIR_PROYECTO))

from sqlalchemy import text  # noqa: E402

from comun.conexion import obtener_engine  # noqa: E402


SQL_REPARACION = DIR_ETL / 'sql_migrations' / '2026_05_25_repair_post_fixes.sql'

FACTS_A_REPROCESAR = [
    ('Fact_Cosecha_SAP',    'silver.facts.fact_cosecha_sap',    'cargar_fact_cosecha_sap'),
    ('Fact_Censo_Plantas',  'silver.facts.fact_censo_plantas',  'cargar_fact_censo_plantas'),
    ('Fact_Ciclo_Poda',     'silver.facts.fact_ciclo_poda',     'cargar_fact_ciclo_poda'),
]

MARTS_A_REFRESCAR = [
    'Gold.Mart_Cosecha',
    'Gold.Mart_Ciclo_Poda',
    # Mart_Censo no existe en marts.py; si en el futuro se crea, agregarlo aqui.
]


def _conteos(engine) -> dict[str, int]:
    """Snapshot de conteos clave para comparar antes/despues."""
    sql = text("""
        SELECT 'Bronce.Cosecha_SAP'             AS t, COUNT(*) AS n FROM Bronce.Cosecha_SAP
        UNION ALL SELECT 'Bronce.Cosecha_SAP con Kg', COUNT(*) FROM Bronce.Cosecha_SAP WHERE Kg_Total_Raw IS NOT NULL
        UNION ALL SELECT 'Bronce.Censo_Plantas',       COUNT(*) FROM Bronce.Censo_Plantas
        UNION ALL SELECT 'Bronce.Evaluacion_Calidad_Poda', COUNT(*) FROM Bronce.Evaluacion_Calidad_Poda
        UNION ALL SELECT 'Silver.Fact_Cosecha_SAP',    COUNT(*) FROM Silver.Fact_Cosecha_SAP
        UNION ALL SELECT 'Silver.Fact_Censo_Plantas',  COUNT(*) FROM Silver.Fact_Censo_Plantas
        UNION ALL SELECT 'Silver.Fact_Ciclo_Poda',     COUNT(*) FROM Silver.Fact_Ciclo_Poda
        UNION ALL SELECT 'Gold.Mart_Cosecha',          COUNT(*) FROM Gold.Mart_Cosecha
        UNION ALL SELECT 'Gold.Mart_Ciclo_Poda',       COUNT(*) FROM Gold.Mart_Ciclo_Poda
        UNION ALL SELECT 'MDM.Cuarentena PENDIENTE',
            COUNT(*) FROM MDM.Cuarentena WHERE Estado='PENDIENTE'
    """)
    with engine.connect() as c:
        return {fila[0]: int(fila[1]) for fila in c.execute(sql)}


def _imprimir_conteos(titulo: str, datos: dict[str, int]) -> None:
    print(f'\n--- {titulo} ---')
    for k, v in datos.items():
        print(f'  {k:<40} {v:>10,}')


def _ejecutar_sql_reparacion(engine) -> None:
    if not SQL_REPARACION.exists():
        raise FileNotFoundError(f'No existe {SQL_REPARACION}')

    print(f'\n== Ejecutando: {SQL_REPARACION.name} ==')
    sql_completo = SQL_REPARACION.read_text(encoding='utf-8')

    # SQL Server requiere ejecutar batch por batch separados por GO. Este script
    # no usa GO, asi que lo pasamos entero como una sola sentencia.
    with engine.begin() as c:
        c.execute(text(sql_completo))


def _reprocesar_silver(engine) -> None:
    import importlib

    for nombre, mod_path, func_name in FACTS_A_REPROCESAR:
        print(f'\n== Reprocesando Silver.{nombre} ==')
        t0 = perf_counter()
        modulo = importlib.import_module(mod_path)
        cargar = getattr(modulo, func_name)
        resumen = cargar(engine)
        dt = perf_counter() - t0
        leidos    = resumen.get('leidos', 0) if isinstance(resumen, dict) else '?'
        insertados = resumen.get('insertados', resumen.get('inserted', '?')) if isinstance(resumen, dict) else '?'
        cuarentena = len(resumen.get('cuarentena', [])) if isinstance(resumen, dict) else '?'
        print(f'  Leidos={leidos} | Insertados={insertados} | Cuarentena={cuarentena} | {dt:.1f}s')


def _refrescar_marts(engine) -> None:
    from gold.marts import REGISTRO_REFRESCO_MART  # mapa: 'Gold.Mart_X' -> funcion

    for mart in MARTS_A_REFRESCAR:
        if mart not in REGISTRO_REFRESCO_MART:
            print(f'  [WARN] {mart} no esta en REGISTRO_REFRESCO_MART, salto.')
            continue
        print(f'\n== Refrescando {mart} ==')
        t0 = perf_counter()
        with engine.begin() as c:
            n = REGISTRO_REFRESCO_MART[mart](c)
        print(f'  Filas en {mart}: {n} ({perf_counter() - t0:.1f}s)')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--aplicar-sql', action='store_true',
                    help='Ejecutar el SQL de reparacion antes del reproceso.')
    ap.add_argument('--dry-run', action='store_true',
                    help='Solo muestra conteos actuales, no toca nada.')
    args = ap.parse_args()

    engine = obtener_engine()

    print('=== Reproceso post-fixes 2026-05-25 ===')
    antes = _conteos(engine)
    _imprimir_conteos('Conteos ANTES', antes)

    if args.dry_run:
        print('\n[dry-run] Nada se modifica.')
        return 0

    if args.aplicar_sql:
        _ejecutar_sql_reparacion(engine)

    _reprocesar_silver(engine)
    _refrescar_marts(engine)

    despues = _conteos(engine)
    _imprimir_conteos('Conteos DESPUES', despues)

    print('\n=== Listo. ===')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
