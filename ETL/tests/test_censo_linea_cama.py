"""
test_censo_linea_cama.py
========================
Regresion: el procesador Silver de Censo no pasaba Linea_Raw al resolver de
geografia. Resultado: todas las lineas de una valvula colapsaban al mismo
ID_Geografia y el deduplicador mandaba ~88% de filas a cuarentena como
"duplicado dentro del mismo archivo".

Fix: Linea_Raw -> cama= en _validar_y_resolver_geografia (Linea == Cama).
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import silver.facts.fact_censo_plantas as modulo_censo
from silver.facts.fact_censo_plantas import ProcesadorCensoPlantas


class TestCensoLineaCama(unittest.TestCase):
    """Verifica que el resolver de geografia se invoque con cama=Linea_Raw."""

    def setUp(self):
        # Evitamos abrir el engine de verdad.
        if hasattr(modulo_censo, '_cargar_lookup_estado_plantas'):
            self._orig_lookup = modulo_censo._cargar_lookup_estado_plantas
            modulo_censo._cargar_lookup_estado_plantas = lambda eng: {
                'BUENAS': 1, 'REGULARES': 2, 'MALAS': 3, 'HOYOS': 4,
            }
        else:
            self._orig_lookup = None

    def tearDown(self):
        if self._orig_lookup is not None:
            modulo_censo._cargar_lookup_estado_plantas = self._orig_lookup

    def _proc(self):
        proc = ProcesadorCensoPlantas(MagicMock())

        # Captura los kwargs con que se llama al resolver.
        proc.llamadas_geografia = []

        def resolver_dims_stub(df, **kwargs):
            df_res = df.copy()
            df_res['ID_Tiempo'] = 20260519
            df_res['ID_Variedad'] = 22
            df_res['Fecha_Evento_dt'] = pd.to_datetime(df_res['_Deriv_Fecha_Temp']).map(lambda x: x.date())
            
            ids_geo = []
            ids_mod_cat = []
            for _, r in df_res.iterrows():
                modulo = r.get('Modulo_Raw')
                turno = r.get('Turno_Raw')
                valvula = r.get('Valvula_Raw')
                cama = r.get('Linea_Raw')
                
                proc.llamadas_geografia.append({
                    'modulo': modulo, 'turno': turno,
                    'valvula': valvula, 'cama': cama,
                })
                
                key = (str(modulo), str(turno), str(valvula), str(cama))
                ids_geo.append(abs(hash(key)) % 100000)
                ids_mod_cat.append(14)
                
            df_res['ID_Geografia'] = ids_geo
            df_res['_id_modulo_catalogo'] = ids_mod_cat
            return df_res

        proc.resolver_dimensiones_batch = resolver_dims_stub
        proc._resolver_variedad_base = lambda rv: 22
        return proc

    def _df_dos_lineas_misma_valvula(self):
        # Reproduce el caso real: misma Fecha+Modulo+Valvula+Variedad+Turno,
        # diferente Linea (debe abrir el grano).
        return pd.DataFrame([
            {'ID_Censo_Plantas': 1, 'Fecha_Raw': '2026-05-19', 'Modulo_Raw': '14',
             'Turno_Raw': '7', 'Valvula_Raw': '26', 'Variedad_Raw': 'ROCIO',
             'Variedad_Canonica': 'ROCIO', 'Linea_Raw': '5',
             'Estado_Planta_Raw': 'Hoyos', 'Cantidad_Raw': '0'},
            {'ID_Censo_Plantas': 2, 'Fecha_Raw': '2026-05-19', 'Modulo_Raw': '14',
             'Turno_Raw': '7', 'Valvula_Raw': '26', 'Variedad_Raw': 'ROCIO',
             'Variedad_Canonica': 'ROCIO', 'Linea_Raw': '8',
             'Estado_Planta_Raw': 'Hoyos', 'Cantidad_Raw': '0'},
            {'ID_Censo_Plantas': 3, 'Fecha_Raw': '2026-05-19', 'Modulo_Raw': '14',
             'Turno_Raw': '7', 'Valvula_Raw': '26', 'Variedad_Raw': 'ROCIO',
             'Variedad_Canonica': 'ROCIO', 'Linea_Raw': '11',
             'Estado_Planta_Raw': 'Hoyos', 'Cantidad_Raw': '0'},
        ])

    def test_resolver_recibe_cama_desde_linea_raw(self):
        proc = self._proc()
        proc._construir_payload(self._df_dos_lineas_misma_valvula())

        camas_vistas = [l['cama'] for l in proc.llamadas_geografia]
        self.assertEqual(camas_vistas, ['5', '8', '11'],
                         "El resolver debe recibir cama=Linea_Raw para cada fila")

    def test_lineas_distintas_producen_ids_geografia_distintos(self):
        proc = self._proc()
        payload = proc._construir_payload(self._df_dos_lineas_misma_valvula())

        self.assertEqual(len(payload), 3, "Las 3 lineas deben sobrevivir el payload")
        ids_geo = [r['ID_Geografia'] for r in payload]
        self.assertEqual(len(set(ids_geo)), 3,
                         "Cada linea de la misma valvula debe resolver a un "
                         "ID_Geografia distinto, no colapsar a uno solo")

    def test_misma_linea_misma_valvula_mismo_id_geografia(self):
        # Sanidad: misma linea -> mismo ID_Geografia (deduplicacion correcta).
        proc = self._proc()
        df = pd.DataFrame([
            {'ID_Censo_Plantas': 1, 'Fecha_Raw': '2026-05-19', 'Modulo_Raw': '14',
             'Turno_Raw': '7', 'Valvula_Raw': '26', 'Variedad_Raw': 'ROCIO',
             'Variedad_Canonica': 'ROCIO', 'Linea_Raw': '5',
             'Estado_Planta_Raw': 'Plantas Buenas', 'Cantidad_Raw': '10'},
            {'ID_Censo_Plantas': 2, 'Fecha_Raw': '2026-05-19', 'Modulo_Raw': '14',
             'Turno_Raw': '7', 'Valvula_Raw': '26', 'Variedad_Raw': 'ROCIO',
             'Variedad_Canonica': 'ROCIO', 'Linea_Raw': '5',
             'Estado_Planta_Raw': 'Plantas Malas', 'Cantidad_Raw': '2'},
        ])
        payload = proc._construir_payload(df)
        self.assertEqual(payload[0]['ID_Geografia'], payload[1]['ID_Geografia'],
                         "Misma linea debe mantener el mismo ID_Geografia")
        # Distinto estado garantiza distinto grano completo.
        self.assertNotEqual(payload[0]['ID_Estado_Planta'],
                            payload[1]['ID_Estado_Planta'])


if __name__ == '__main__':
    unittest.main()
