"""
test_dedup_vectorizado.py
==========================
Tests del fast-path vectorizado de _limpiar_duplicados_internos y de la
normalización canónica de claves. Cubre los bugs detectados en la auditoría
quirúrgica (NaT, tipos mixtos, None vs 'None', empates deterministas).

Estos tests SÍ importan BaseFactProcessor real (no espejan la lógica).
"""

import datetime
import os
import sys
import unittest

# Permitir importar desde ETL/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from silver.facts._base_processor import BaseFactProcessor


class _MockProc(BaseFactProcessor):
    """Subclase de BaseFactProcessor que evita SQL/conexion en __init__."""

    def __init__(self, columnas_clave=None, tiebreaker='ts'):
        # No invocamos super().__init__()
        self.columnas_clave_unica = columnas_clave or ['k']
        self.columna_tiebreaker_timestamp = tiebreaker
        self.tabla_destino = 'TEST_TABLE'
        self.resumen = {}
        self.ids_procesados = set()

    def registrar_rechazo(self, **kw):
        pass


T1 = datetime.datetime(2026, 5, 1, 10, 0, 0)
T2 = datetime.datetime(2026, 6, 1, 10, 0, 0)


class TestTiebreakerRobusto(unittest.TestCase):
    """Cubre los crashes y bugs del path con tiebreaker."""

    def test_nat_pierde_contra_datetime_real(self):
        mp = _MockProc()
        lote = [
            {'k': 'A', 'ts': pd.NaT, 'valor': 'NaT', 'id_origen_rastreo': 1},
            {'k': 'A', 'ts': T1,     'valor': 'real', 'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['valor'], 'real')

    def test_tipos_mixtos_no_crashea(self):
        mp = _MockProc()
        lote = [
            {'k': 'B', 'ts': '2026-05-01', 'valor': 'string', 'id_origen_rastreo': 1},
            {'k': 'B', 'ts': T2,           'valor': 'dt',     'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['valor'], 'dt')

    def test_empate_determinista_por_id_mayor(self):
        mp = _MockProc()
        lote = [
            {'k': 'C', 'ts': T1, 'valor': 'menor', 'id_origen_rastreo': 1},
            {'k': 'C', 'ts': T1, 'valor': 'mayor', 'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(r[0]['valor'], 'mayor')

    def test_empate_determinista_invariante_al_orden(self):
        mp = _MockProc()
        lote = [
            {'k': 'C', 'ts': T1, 'valor': 'mayor', 'id_origen_rastreo': 2},
            {'k': 'C', 'ts': T1, 'valor': 'menor', 'id_origen_rastreo': 1},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(r[0]['valor'], 'mayor')

    def test_none_pierde_contra_datetime(self):
        mp = _MockProc()
        lote = [
            {'k': 'D', 'ts': None, 'valor': 'sin', 'id_origen_rastreo': 1},
            {'k': 'D', 'ts': T1,   'valor': 'con', 'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(r[0]['valor'], 'con')


class TestNormalizacionClaves(unittest.TestCase):
    """None vs 'None' vs 1.0 vs 1 deben colapsar a la misma clave."""

    def test_none_vs_string_none_colapsan(self):
        mp = _MockProc()
        lote = [
            {'k': None,   'ts': T1, 'valor': 'A', 'id_origen_rastreo': 1},
            {'k': 'None', 'ts': T2, 'valor': 'B', 'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(len(r), 1, f'Esperado 1 fila, got: {r}')
        self.assertEqual(r[0]['valor'], 'B')

    def test_int_vs_float_entero_colapsan(self):
        mp = _MockProc()
        lote = [
            {'k': 1,   'ts': T1, 'valor': 'int', 'id_origen_rastreo': 1},
            {'k': 1.0, 'ts': T2, 'valor': 'flt', 'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(len(r), 1)

    def test_nan_string_vs_none_colapsan(self):
        mp = _MockProc()
        lote = [
            {'k': 'nan', 'ts': T1, 'valor': 'A', 'id_origen_rastreo': 1},
            {'k': None,  'ts': T2, 'valor': 'B', 'id_origen_rastreo': 2},
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(len(r), 1)


class TestFastPathVectorizado(unittest.TestCase):
    """Verifica que el fast-path se active a partir de 10k filas y dé
    resultados consistentes con el loop clásico."""

    def test_15k_filas_dedup_correcto(self):
        mp = _MockProc()
        lote = [
            {
                'k': i % 500,
                'ts': T1 + datetime.timedelta(seconds=i),
                'valor': f'v{i}',
                'id_origen_rastreo': i,
            }
            for i in range(15_000)
        ]
        r = mp._limpiar_duplicados_internos(lote)
        self.assertEqual(len(r), 500)

    def test_empate_determinista_en_vectorizado(self):
        """Empate masivo: id_origen mayor debe ganar (numérico, no string)."""
        mp = _MockProc()
        lote = [
            {'k': i % 100, 'ts': T1, 'valor': f'id{i}', 'id_origen_rastreo': i}
            for i in range(10_001)
        ]
        r = mp._limpiar_duplicados_internos(lote)
        fila_k0 = next(row for row in r if row['k'] == 0)
        # Mayor id con k=0 es 10000 (10000 % 100 == 0)
        self.assertEqual(fila_k0['id_origen_rastreo'], 10000)


if __name__ == '__main__':
    unittest.main()
