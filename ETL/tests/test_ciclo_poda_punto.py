"""
test_ciclo_poda_punto.py
=========================
Regresion: Fact_Ciclo_Poda colapsaba 15,615 plantas a 57 filas (1 por
Modulo+Fecha+Variedad+Tipo) porque:

  1) Punto_Raw NO es columna tipada en Bronce.Evaluacion_Calidad_Poda; viaja
     embebido en Valores_Raw como "Punto_Raw=10". El processor lo rescataba
     DENTRO del loop del payload, pero pre_limpiar_duplicados_batch corria
     ANTES, con Punto_Raw=None -> dedupe colapsaba todo el grupo.
  2) El dedupe no incluia Valvula_Raw ni Turno_Raw -> distintas valvulas del
     mismo Modulo+Fecha+Variedad+Tipo+Punto chocaban entre si.
  3) Cuando Punto_Raw resultaba None se hacia 'continue' silencioso (sin
     registrar cuarentena), perdiendo la fila sin trazabilidad.

Fix: hidratar Punto_Raw en el DF antes del dedupe, incluir Valvula/Turno en
la clave, registrar cuarentena cuando el punto realmente falte.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from silver.facts.fact_ciclo_poda import ProcesadorCicloPoda


def _make_proc():
    """Procesador con stubs para no requerir BD."""
    proc = ProcesadorCicloPoda(MagicMock())

    def resolver_dims_stub(df, **kwargs):
        df_res = df.copy()
        df_res['ID_Tiempo'] = 20260316
        df_res['ID_Variedad'] = 22
        df_res['Fecha_Evento_dt'] = pd.to_datetime(df_res['Fecha_Raw']).map(lambda x: x.date())
        
        ids_geo = []
        ids_mod_cat = []
        for _, r in df_res.iterrows():
            modulo = r.get('Modulo_Raw')
            turno = r.get('Turno_Raw')
            valvula = r.get('Valvula_Raw')
            key = (str(modulo), str(turno), str(valvula))
            ids_geo.append(abs(hash(key)) % 100000)
            ids_mod_cat.append(14)
            
        df_res['ID_Geografia'] = ids_geo
        df_res['_id_modulo_catalogo'] = ids_mod_cat
        return df_res

    proc.resolver_dimensiones_batch = resolver_dims_stub
    return proc


def _fila(id_o, valvula, punto, valores_raw=None):
    base = {
        'ID_Evaluacion_Poda': id_o,
        'Fecha_Raw': '2026-03-16',
        'Fundo_Raw': 'ARANDANOS',
        'Modulo_Raw': '14',
        'Turno_Raw': '03',
        'Valvula_Raw': valvula,
        'Variedad_Raw': 'ROCIO',
        'Variedad_Canonica': 'ROCIO',
        'Tipo_Evaluacion_Raw': 'PODA GENERAL',
        'TallosPlanta_Raw': '19',
        'LongitudTallo_Raw': '15.33',
        'DiametroTallo_Raw': '0.92',
        'RamillaPlanta_Raw': '0',
        'ToconesPlanta_Raw': '0',
        'CortesDefectuosos_Raw': '0',
        'AlturaPoda_Raw': '39',
        'Fecha_Sistema': pd.Timestamp('2026-05-20'),
        'Valores_Raw': valores_raw if valores_raw is not None
                       else f'Punto_Raw={punto} | Tallos_Planta_Raw=19',
    }
    return base


def _hidratar_punto(proc, df):
    """Replica el hidratado que hace cargar_fact_ciclo_poda() antes del dedupe."""
    if 'Punto_Raw' not in df.columns or df['Punto_Raw'].isna().all():
        df['Punto_Raw'] = df['Valores_Raw'].apply(
            lambda v: proc.parsear_raw(v).get('Punto_Raw')
        )
    return df


class TestCicloPodaPunto(unittest.TestCase):
    def test_puntos_distintos_misma_valvula_no_se_colapsan(self):
        proc = _make_proc()
        df = pd.DataFrame([
            _fila(1, valvula='12', punto=1),
            _fila(2, valvula='12', punto=2),
            _fila(3, valvula='12', punto=3),
        ])
        df = _hidratar_punto(proc, df)
        df = proc.pre_limpiar_duplicados_batch(
            df,
            ['Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Fecha_Raw',
             'Variedad_Raw', 'Tipo_Evaluacion_Raw', 'Punto_Raw'],
        )
        self.assertEqual(len(df), 3,
                         "3 puntos distintos de la misma valvula deben sobrevivir")

        payload = proc._construir_payload(df)
        puntos = sorted(r['Punto'] for r in payload)
        self.assertEqual(puntos, [1, 2, 3])

    def test_valvulas_distintas_no_se_colapsan(self):
        # Misma fecha, modulo, variedad, tipo, punto -> distintas valvulas.
        # Antes: el dedupe sin Valvula_Raw las colapsaba a una sola.
        proc = _make_proc()
        df = pd.DataFrame([
            _fila(1, valvula='03', punto=5),
            _fila(2, valvula='07', punto=5),
            _fila(3, valvula='12', punto=5),
        ])
        df = _hidratar_punto(proc, df)
        df = proc.pre_limpiar_duplicados_batch(
            df,
            ['Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Fecha_Raw',
             'Variedad_Raw', 'Tipo_Evaluacion_Raw', 'Punto_Raw'],
        )
        self.assertEqual(len(df), 3,
                         "3 valvulas distintas con el mismo Punto deben sobrevivir")

    def test_punto_se_hidrata_desde_valores_raw(self):
        # Caso real: Punto_Raw no esta como columna, solo dentro de Valores_Raw.
        proc = _make_proc()
        df = pd.DataFrame([
            _fila(1, valvula='03', punto=7),
            _fila(2, valvula='03', punto=8),
        ])
        # Simular que la columna no existe (no llega del SELECT)
        self.assertNotIn('Punto_Raw', df.columns)

        df = _hidratar_punto(proc, df)
        self.assertIn('Punto_Raw', df.columns)
        self.assertEqual(list(df['Punto_Raw']), ['7', '8'])

    def test_fila_sin_punto_se_cuarentena_no_se_silencia(self):
        proc = _make_proc()
        df = pd.DataFrame([
            _fila(1, valvula='03', punto=None,
                  valores_raw='Tallos_Planta_Raw=19'),  # sin Punto_Raw
        ])
        df = _hidratar_punto(proc, df)
        payload = proc._construir_payload(df)

        self.assertEqual(len(payload), 0, "Fila sin punto no debe entrar al payload")
        self.assertEqual(len(proc.resumen['cuarentena']), 1,
                         "Falta de punto debe registrar cuarentena, no silenciarse")
        self.assertEqual(proc.resumen['cuarentena'][0]['columna'], 'Punto_Raw')

    def test_misma_combinacion_y_mismo_punto_si_dedupea(self):
        # Sanidad: el dedupe sigue funcionando para duplicados verdaderos.
        proc = _make_proc()
        df = pd.DataFrame([
            _fila(1, valvula='03', punto=5),
            _fila(2, valvula='03', punto=5),  # duplicado real
        ])
        df = _hidratar_punto(proc, df)
        df = proc.pre_limpiar_duplicados_batch(
            df,
            ['Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Fecha_Raw',
             'Variedad_Raw', 'Tipo_Evaluacion_Raw', 'Punto_Raw'],
        )
        self.assertEqual(len(df), 1,
                         "Duplicado real (mismo punto y valvula) debe deduplicarse a 1")


if __name__ == '__main__':
    unittest.main()
