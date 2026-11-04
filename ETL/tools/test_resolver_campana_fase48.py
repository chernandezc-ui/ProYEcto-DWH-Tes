"""
test_resolver_campana_fase48.py
==============================
Tests de la cadena de resolucion de ID_Campana tras fase48a + cambio en lookup.py.

Verifica:
  1. La funcion SQL MDM.fn_Resolver_ID_Campana_Por_Fecha responde a fechas clave.
  2. obtener_id_campana_anual (Python) ahora delega a la SQL y retorna lo mismo.
  3. obtener_id_campana (Python) sigue priorizando Bridge_Modulo_Campana y cae
     a la nueva resolucion por fecha cuando no hay match en el bridge.
  4. Las 96,360 filas actuales de Fact_Evaluacion_Vegetativa siguen mapeando a
     ID_Campana=3 (Campania 2026) — no debe haber regresion.

Ejecutar:
    python -m ETL.tools.test_resolver_campana_fase48
o desde la raiz:
    python ETL/tools/test_resolver_campana_fase48.py
"""
from __future__ import annotations
import os, sys, pandas as pd
from sqlalchemy import text

# Permitir ejecucion como script suelto: anadir ETL/ al path
_AQUI = os.path.dirname(os.path.abspath(__file__))
_ETL  = os.path.dirname(_AQUI)
if _ETL not in sys.path:
    sys.path.insert(0, _ETL)

from config.conexion import obtener_engine
from mdm.lookup import obtener_id_campana_anual, obtener_id_campana
import pytest


@pytest.fixture
def engine():
    return obtener_engine()


CASOS_FECHA = [
    # (fecha, anio_esperado, descripcion)
    ('2024-06-15', 2024, 'mitad campania 2024-2025'),
    ('2025-03-15', 2025, 'solape: cierre eval 2024 vs inicio poda 2025 - debe ganar 2025'),
    ('2026-02-15', 2026, 'inicio operativa 2026-2027'),
    ('2020-08-15', 2020, 'campania 2020-2021'),
    ('2015-01-01', None, 'antes de cualquier campania - debe retornar None'),
]


def _anio_de(engine, id_campana):
    if id_campana is None:
        return None
    with engine.connect() as c:
        r = c.execute(
            text("SELECT Anio_Cosecha FROM Silver.Dim_Campana WHERE ID_Campana = :i"),
            {"i": int(id_campana)},
        ).fetchone()
    return int(r[0]) if r else None


def test_sql_function(engine):
    print('=== Test 1: Funcion SQL MDM.fn_Resolver_ID_Campana_Por_Fecha ===')
    fallos = 0
    with engine.connect() as c:
        for fecha, anio_esperado, desc in CASOS_FECHA:
            r = c.execute(
                text("SELECT MDM.fn_Resolver_ID_Campana_Por_Fecha(:f)"),
                {"f": fecha},
            ).fetchone()
            id_c = int(r[0]) if r and r[0] is not None else None
            anio_real = _anio_de(engine, id_c)
            ok = (anio_real == anio_esperado)
            estado = 'OK' if ok else 'FAIL'
            if not ok:
                fallos += 1
            print(f'  [{estado}] {fecha}  -> ID={id_c} Anio={anio_real}  (esperado {anio_esperado}) -- {desc}')
    return fallos


def test_python_anual(engine):
    print('\n=== Test 2: obtener_id_campana_anual (Python) ===')
    fallos = 0
    for fecha, anio_esperado, desc in CASOS_FECHA:
        id_c = obtener_id_campana_anual(fecha, engine)
        anio_real = _anio_de(engine, id_c)
        ok = (anio_real == anio_esperado)
        estado = 'OK' if ok else 'FAIL'
        if not ok:
            fallos += 1
        print(f'  [{estado}] {fecha}  -> ID={id_c} Anio={anio_real}  (esperado {anio_esperado}) -- {desc}')
    return fallos


def test_python_via_obtener_id_campana(engine):
    """obtener_id_campana sin ID_Modulo y sin ID_Variedad cae al fallback (=anual)."""
    print('\n=== Test 3: obtener_id_campana sin modulo/variedad (debe caer al fallback) ===')
    fallos = 0
    for fecha, anio_esperado, desc in CASOS_FECHA:
        id_c = obtener_id_campana(None, None, fecha, engine, id_modulo_catalogo=None)
        anio_real = _anio_de(engine, id_c)
        ok = (anio_real == anio_esperado)
        estado = 'OK' if ok else 'FAIL'
        if not ok:
            fallos += 1
        print(f'  [{estado}] {fecha}  -> ID={id_c} Anio={anio_real}  (esperado {anio_esperado}) -- {desc}')
    return fallos


def test_no_regresion_fact_actual(engine):
    """Las 96,360 filas existentes deben seguir mapeando a ID_Campana=3 (Camp 2026)."""
    print('\n=== Test 4: No-regresion sobre Fact_Evaluacion_Vegetativa actual ===')
    with engine.connect() as c:
        dist = c.execute(text("""
            SELECT
                MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(Fecha_Evento AS DATE)) AS id_calc,
                COUNT(*) AS n
              FROM Silver.Fact_Evaluacion_Vegetativa
             GROUP BY MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(Fecha_Evento AS DATE))
        """)).fetchall()
    total = sum(n for _, n in dist)
    a_2026 = sum(n for id_c, n in dist if id_c == 3)
    ok = (a_2026 == total)
    estado = 'OK' if ok else 'FAIL'
    print(f'  [{estado}] Total={total}  ->  ID_Campana=3 (Camp 2026): {a_2026}  (debe ser igual al total)')
    if not ok:
        for id_c, n in dist:
            print(f'    ID_Campana={id_c} -> {n} filas')
    return 0 if ok else 1


def main():
    engine = obtener_engine()
    total_fallos = 0
    total_fallos += test_sql_function(engine)
    total_fallos += test_python_anual(engine)
    total_fallos += test_python_via_obtener_id_campana(engine)
    total_fallos += test_no_regresion_fact_actual(engine)
    print(f'\n{"=" * 60}')
    if total_fallos == 0:
        print('OK: TODOS LOS TESTS PASARON.')
        sys.exit(0)
    else:
        print(f'FAIL: {total_fallos} test(s) fallaron.')
        sys.exit(1)


if __name__ == '__main__':
    main()
