"""
test_cargador_cosecha_kg.py
============================
Regresion del bug donde el cargador Bronce de Cosecha_SAP enviaba el kg neto
a Valores_Raw en lugar de a la columna tipada Kg_Total_Raw.

Causa: alias 'Kg_Total' -> 'KgNeto' produce header KgNeto_Raw, pero
Bronce.Cosecha_SAP tiene Kg_Total_Raw (Reporte_Cosecha usa KgNeto_Raw).
Fix: rename target-aware KgNeto_Raw -> Kg_Total_Raw en
_alinear_dataframe_a_tabla cuando la tabla destino es Cosecha_SAP.
"""

import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bronce.cargador as cargador


COLUMNAS_COSECHA_SAP = {
    'Campana_Raw', 'Fecha_Raw', 'Semana_Raw', 'Sector_Raw', 'Modulo_Raw',
    'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw', 'Kg_Total_Raw', 'Area_Raw',
    'Plantas_Raw', 'SemCal_Raw', 'Semana_Cosecha_Raw', 'Valores_Raw',
    'Nombre_Archivo', 'Fecha_Sistema', 'Estado_Carga',
}

COLUMNAS_REPORTE_COSECHA = {
    'Fecha_Raw', 'Modulo_Raw', 'Variedad_Raw', 'KgNeto_Raw', 'Jabas_Raw',
    'Valores_Raw', 'Nombre_Archivo',
}


class _StubEngine:
    pass


class TestCargadorCosechaKg(unittest.TestCase):
    def setUp(self):
        # Monkeypatch del lookup de columnas para no requerir BD.
        self._orig = cargador._obtener_columnas_bronce
        self._tabla_actual = None

        def fake(tabla_destino, engine):
            return self._tabla_actual

        cargador._obtener_columnas_bronce = fake

    def tearDown(self):
        cargador._obtener_columnas_bronce = self._orig

    def _df_cosecha(self):
        # Simula el resultado de normalizar_columnas() tras el alias
        # Kg_Total -> KgNeto -> KgNeto_Raw.
        return pd.DataFrame({
            'Fecha_Raw':    ['2019-07-04', '2019-07-04', '2019-07-05'],
            'Modulo_Raw':   ['1', '1', '1'],
            'Valvula_Raw':  ['1', '1', '1'],
            'Variedad_Raw': ['VENTURA', 'VENTURA', 'VENTURA'],
            'Turno_Raw':    ['1', '1', '1'],
            'KgNeto_Raw':   ['12.525', '5.9', '8.35'],
            'Plantas_Raw':  ['8589', '8589', '8589'],
        })

    def test_kg_va_a_columna_tipada_en_cosecha_sap(self):
        self._tabla_actual = COLUMNAS_COSECHA_SAP
        df_alineado, extras = cargador._alinear_dataframe_a_tabla(
            self._df_cosecha(), 'Bronce.Cosecha_SAP', _StubEngine()
        )

        self.assertIn('Kg_Total_Raw', df_alineado.columns,
                      "Kg_Total_Raw debe estar presente tras el alineado")
        self.assertEqual(
            list(df_alineado['Kg_Total_Raw']),
            ['12.525', '5.9', '8.35'],
            "El kg neto debe quedar en Kg_Total_Raw, no en Valores_Raw"
        )
        self.assertNotIn('KgNeto_Raw', df_alineado.columns,
                         "KgNeto_Raw no debe persistir en Cosecha_SAP")

    def test_valores_raw_no_contiene_kgneto_en_cosecha_sap(self):
        self._tabla_actual = COLUMNAS_COSECHA_SAP
        df_alineado, _ = cargador._alinear_dataframe_a_tabla(
            self._df_cosecha(), 'Bronce.Cosecha_SAP', _StubEngine()
        )

        if 'Valores_Raw' in df_alineado.columns:
            for val in df_alineado['Valores_Raw'].fillna(''):
                self.assertNotIn(
                    'KgNeto_Raw', val,
                    f"Valores_Raw no debe contener 'KgNeto_Raw=...', obtuvo: {val!r}"
                )

    def test_reporte_cosecha_conserva_kgneto_raw(self):
        # Sanidad: NO romper el otro layout (Reporte_Cosecha usa KgNeto_Raw).
        self._tabla_actual = COLUMNAS_REPORTE_COSECHA
        df = pd.DataFrame({
            'Fecha_Raw':    ['2026-05-20'],
            'Modulo_Raw':   ['3'],
            'Variedad_Raw': ['BILOXI'],
            'KgNeto_Raw':   ['14.2'],
            'Jabas_Raw':    ['2'],
        })
        df_alineado, _ = cargador._alinear_dataframe_a_tabla(
            df, 'Bronce.Reporte_Cosecha', _StubEngine()
        )

        self.assertIn('KgNeto_Raw', df_alineado.columns,
                      "Reporte_Cosecha conserva KgNeto_Raw (es la columna real)")
        self.assertEqual(list(df_alineado['KgNeto_Raw']), ['14.2'])
        self.assertNotIn('Kg_Total_Raw', df_alineado.columns)


if __name__ == '__main__':
    unittest.main()
