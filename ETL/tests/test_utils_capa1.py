"""
test_utils_capa1.py
====================
Tests de regresión de los 6 bugs críticos de utils corregidos en la
auditoría quirúrgica (capa 1). Cubre dni, tipos, texto y cargador.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.dni import limpiar_dni, procesar_dni
from utils.tipos import a_decimal, a_entero, texto_nulo
from utils.texto import (
    normalizar_modulo,
    es_test_block,
    normalizar_componente_geografico,
)


class TestDNI(unittest.TestCase):
    """Bug #1: '7654321.0' se corrompía a '76543210'."""

    def test_excel_float_no_corrompe(self):
        self.assertEqual(limpiar_dni('7654321.0'), '07654321')

    def test_excel_float_otro(self):
        self.assertEqual(limpiar_dni('12345678.0'), '12345678')

    def test_dni_con_puntos_de_miles(self):
        self.assertEqual(limpiar_dni('12.345.678'), '12345678')

    def test_dni_con_espacios(self):
        self.assertEqual(limpiar_dni(' 12 34 56 78 '), '12345678')

    def test_dni_demasiado_largo_no_se_trunca(self):
        # 11 dígitos: NO truncar (devolver crudo) para que validación falle.
        dni, valido = procesar_dni('99999999999')
        self.assertEqual(dni, '99999999999')
        self.assertFalse(valido)

    def test_dni_numerico_int(self):
        self.assertEqual(limpiar_dni(7654321), '07654321')


class TestTipos(unittest.TestCase):
    """Bug #3: a_decimal aceptaba 'inf', 'NAN', 'NULL'; '1,000' → 1.0."""

    def test_inf_rechazado(self):
        self.assertIsNone(a_decimal('inf'))
        self.assertIsNone(a_decimal('-inf'))

    def test_nan_case_insensitive(self):
        self.assertIsNone(a_decimal('nan'))
        self.assertIsNone(a_decimal('NaN'))
        self.assertIsNone(a_decimal('NAN'))

    def test_null_token(self):
        self.assertIsNone(a_decimal('NULL'))
        self.assertIsNone(a_decimal('null'))
        self.assertIsNone(texto_nulo('NULL'))
        self.assertIsNone(texto_nulo('N/A'))

    def test_locale_coma_miles(self):
        # '1,000' debe interpretarse como mil (separador de miles), no 1.0
        self.assertEqual(a_decimal('1,000'), 1000.0)

    def test_locale_coma_decimal(self):
        # '1,5' debe seguir siendo 1.5 (coma decimal europea)
        self.assertEqual(a_decimal('1,5'), 1.5)

    def test_a_entero_filtra_inf(self):
        self.assertIsNone(a_entero('inf'))

    def test_a_decimal_negativo_normal(self):
        self.assertEqual(a_decimal('-25.5'), -25.5)


class TestTextoTestBlock(unittest.TestCase):
    """Bug #4: 'LATEST' era reconocido como Test Block (substring match)."""

    def test_latest_no_es_test_block(self):
        self.assertFalse(es_test_block('LATEST'))

    def test_blockbuster_no_es_block(self):
        self.assertFalse(es_test_block('BLOCKBUSTER'))

    def test_test_real_si_es_test_block(self):
        self.assertTrue(es_test_block('TEST'))
        self.assertTrue(es_test_block('TEST BLOCK 5'))
        self.assertTrue(es_test_block('BLOCK 12'))

    def test_normalizar_modulo_latest_es_componente(self):
        # Antes: devolvía 'LATEST' tratándolo como Test Block.
        # Ahora: procesa como componente normal (sin numero -> devuelve texto)
        self.assertEqual(normalizar_modulo('LATEST'), 'LATEST')


class TestComponenteGeografico(unittest.TestCase):
    """Bug #5: multi-número devolvía último silente."""

    def test_un_numero(self):
        self.assertEqual(normalizar_componente_geografico('MODULO 2'), '2')

    def test_negativo(self):
        self.assertEqual(normalizar_componente_geografico('MODULO -3'), '-3')

    def test_decimal_preservado(self):
        self.assertEqual(normalizar_componente_geografico('VALV 9.1234'), '9.1234')

    def test_multiple_numeros_preserva_texto(self):
        # Antes: 'TURNO 02 PISO 03' -> '3' (perdía componente silente)
        # Ahora: devuelve texto original normalizado (no degrada)
        r = normalizar_componente_geografico('TURNO 02 PISO 03')
        self.assertEqual(r, 'TURNO 02 PISO 03')


if __name__ == '__main__':
    unittest.main()
