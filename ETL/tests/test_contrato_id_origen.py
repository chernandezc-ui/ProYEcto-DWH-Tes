"""
test_contrato_id_origen.py
==========================
Red de seguridad (Fase 0) para el contrato del identificador de rastreo.

Bug histórico (corregido en Fase 1): leer_bronce_dinamico devolvía la PK con su
nombre físico (ID_Induccion_Floral, ID_Floracion, ID_Tasa_Crecimiento), pero
varios _construir_payload leían fila.get('ID_Registro_Origen'). Resultado:
id_origen=None en cada fila → los rechazos no marcaban RECHAZADO y los
insertados no marcaban PROCESADO → reproceso perpetuo sin avance.

Estos tests garantizan que la PK SIEMPRE se exponga también como
'ID_Registro_Origen' tras leer Bronce.
"""

import unittest

import pandas as pd
import pytest

from silver.facts._helpers_fact_comunes import asegurar_id_registro_origen


class TestAsegurarIdRegistroOrigen(unittest.TestCase):
    """Lógica pura del espejo de PK → ID_Registro_Origen."""

    def test_agrega_espejo_desde_pk_real(self):
        df = pd.DataFrame({'ID_Induccion_Floral': [10, 20, 30], 'Fecha_Raw': ['a', 'b', 'c']})
        salida = asegurar_id_registro_origen(df, 'ID_Induccion_Floral')
        self.assertIn('ID_Registro_Origen', salida.columns)
        self.assertEqual(salida['ID_Registro_Origen'].tolist(), [10, 20, 30])

    def test_no_pierde_la_columna_pk_original(self):
        df = pd.DataFrame({'ID_Floracion': [1, 2]})
        salida = asegurar_id_registro_origen(df, 'ID_Floracion')
        self.assertIn('ID_Floracion', salida.columns)
        self.assertIn('ID_Registro_Origen', salida.columns)

    def test_no_sobrescribe_si_ya_existe(self):
        df = pd.DataFrame({'ID_X': [1, 2], 'ID_Registro_Origen': [99, 98]})
        salida = asegurar_id_registro_origen(df, 'ID_X')
        self.assertEqual(salida['ID_Registro_Origen'].tolist(), [99, 98])

    def test_no_falla_si_pk_ausente(self):
        df = pd.DataFrame({'Otra': [1]})
        salida = asegurar_id_registro_origen(df, 'ID_Inexistente')
        self.assertNotIn('ID_Registro_Origen', salida.columns)

    def test_df_vacio_con_columnas(self):
        df = pd.DataFrame(columns=['ID_Tasa_Crecimiento', 'Fecha_Raw'])
        salida = asegurar_id_registro_origen(df, 'ID_Tasa_Crecimiento')
        self.assertIn('ID_Registro_Origen', salida.columns)
        self.assertEqual(len(salida), 0)

    def test_no_muta_el_df_de_entrada(self):
        df = pd.DataFrame({'ID_Peladas': [1, 2]})
        _ = asegurar_id_registro_origen(df, 'ID_Peladas')
        self.assertNotIn('ID_Registro_Origen', df.columns)


@pytest.mark.sqlserver
def test_peladas_expone_id_registro_origen(sqlserver_engine):
    """Smoke SQL explícito: comprobar el espejo de PK leyendo una tabla Bronce."""
    from silver.facts._helpers_fact_comunes import leer_bronce_dinamico

    df = leer_bronce_dinamico(
        sqlserver_engine, 'Bronce.Peladas', 'ID_Peladas', ['Fecha_Raw'], filtro_estado=False
    )
    assert 'ID_Registro_Origen' in df.columns
    if len(df):
        assert df['ID_Registro_Origen'].tolist() == df['ID_Peladas'].tolist()
        assert not df['ID_Registro_Origen'].isnull().any()


if __name__ == '__main__':
    unittest.main()
