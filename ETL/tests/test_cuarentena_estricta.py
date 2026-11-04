"""
test_cuarentena_estricta.py
============================
Tests del modulo mdm/cuarentena.py:
- es_modo_estricto() lee y cachea el flag
- resetear_cache_modo_estricto() forza relectura
- helpers _to_str normalizan correctamente
- registrar_cuarentena_* construye los parametros esperados (mock engine)

Estos tests usan MagicMock para el engine SQLAlchemy: NO requieren SQL Server.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestFlagModoEstricto(unittest.TestCase):
    def setUp(self):
        # Limpiar cache del flag antes de cada test
        from mdm.cuarentena import resetear_cache_modo_estricto
        resetear_cache_modo_estricto()

    def _mock_engine_con_valor(self, valor):
        """Engine mock que devuelve `valor` para SELECT del flag."""
        eng = MagicMock()
        ctx = MagicMock()
        eng.connect.return_value.__enter__.return_value = ctx
        ctx.execute.return_value.scalar.return_value = valor
        return eng

    def test_flag_on_devuelve_true(self):
        from mdm.cuarentena import es_modo_estricto
        eng = self._mock_engine_con_valor('ON')
        self.assertTrue(es_modo_estricto(eng))

    def test_flag_off_devuelve_false(self):
        from mdm.cuarentena import es_modo_estricto
        eng = self._mock_engine_con_valor('OFF')
        self.assertFalse(es_modo_estricto(eng))

    def test_flag_ausente_devuelve_false(self):
        # SELECT devuelve None (parametro no existe)
        from mdm.cuarentena import es_modo_estricto
        eng = self._mock_engine_con_valor(None)
        self.assertFalse(es_modo_estricto(eng))

    def test_flag_case_insensitive_y_trim(self):
        from mdm.cuarentena import es_modo_estricto, resetear_cache_modo_estricto
        for valor in ('on', ' On ', 'ON', 'oN'):
            resetear_cache_modo_estricto()
            eng = self._mock_engine_con_valor(valor)
            self.assertTrue(es_modo_estricto(eng), f'fallo con {valor!r}')

    def test_cache_evita_segunda_query(self):
        from mdm.cuarentena import es_modo_estricto
        eng = self._mock_engine_con_valor('ON')
        es_modo_estricto(eng)
        es_modo_estricto(eng)
        es_modo_estricto(eng)
        # solo una llamada a connect (cacheado)
        self.assertEqual(eng.connect.call_count, 1)

    def test_falla_sql_devuelve_false_y_no_crashea(self):
        from mdm.cuarentena import es_modo_estricto
        eng = MagicMock()
        eng.connect.side_effect = RuntimeError('conexion caida')
        self.assertFalse(es_modo_estricto(eng))


class TestToStr(unittest.TestCase):
    def test_none(self):
        from mdm.cuarentena import _to_str
        self.assertIsNone(_to_str(None))

    def test_string_vacio(self):
        from mdm.cuarentena import _to_str
        self.assertIsNone(_to_str(''))
        self.assertIsNone(_to_str('   '))

    def test_tokens_nulos(self):
        from mdm.cuarentena import _to_str
        for token in ('none', 'NONE', 'nan', 'NaN', 'null', 'NULL', '<NA>'):
            self.assertIsNone(_to_str(token), f'fallo con {token!r}')

    def test_valor_real(self):
        from mdm.cuarentena import _to_str
        self.assertEqual(_to_str('  Fundo Norte '), 'Fundo Norte')
        self.assertEqual(_to_str(123), '123')


class TestRegistrarCuarentenaGeografia(unittest.TestCase):
    """Verifica el flujo UPSERT (UPDATE primero, INSERT si no afectó)."""

    def _engine_con_upsert(self, update_id, insert_id):
        eng = MagicMock()
        ctx = MagicMock()
        eng.begin.return_value.__enter__.return_value = ctx
        # Primera llamada = UPDATE devuelve update_id, segunda = INSERT
        ctx.execute.return_value.scalar.side_effect = [update_id, insert_id]
        return eng, ctx

    def test_update_hit_no_inserta(self):
        from mdm.cuarentena import registrar_cuarentena_geografia
        eng, ctx = self._engine_con_upsert(update_id=42, insert_id=99)
        result = registrar_cuarentena_geografia(
            eng, fundo='F', sector='S', modulo='M', turno='T',
            origen_tabla='X',
        )
        self.assertEqual(result, 42)
        # Solo se llamó execute UNA vez (el UPDATE), no se llegó al INSERT.
        self.assertEqual(ctx.execute.call_count, 1)

    def test_update_miss_dispara_insert(self):
        from mdm.cuarentena import registrar_cuarentena_geografia
        eng, ctx = self._engine_con_upsert(update_id=None, insert_id=99)
        result = registrar_cuarentena_geografia(
            eng, fundo='Nuevo', origen_tabla='X',
        )
        self.assertEqual(result, 99)
        # Se llamó execute 2 veces: UPDATE (miss) + INSERT
        self.assertEqual(ctx.execute.call_count, 2)


class TestRegistrarCuarentenaVariedad(unittest.TestCase):
    def test_upsert_basico(self):
        from mdm.cuarentena import registrar_cuarentena_variedad
        eng = MagicMock()
        ctx = MagicMock()
        eng.begin.return_value.__enter__.return_value = ctx
        ctx.execute.return_value.scalar.side_effect = [None, 7]
        rid = registrar_cuarentena_variedad(
            eng, nombre_recibido='FCM15-005 (2022)', origen_tabla='Fact_X',
        )
        self.assertEqual(rid, 7)


class TestRegistrarCuarentenaPersonal(unittest.TestCase):
    def test_upsert_basico(self):
        from mdm.cuarentena import registrar_cuarentena_personal
        eng = MagicMock()
        ctx = MagicMock()
        eng.begin.return_value.__enter__.return_value = ctx
        ctx.execute.return_value.scalar.side_effect = [None, 3]
        rid = registrar_cuarentena_personal(
            eng, dni='12345678', nombre='Juan Perez',
            origen_tabla='Fiscalizacion',
        )
        self.assertEqual(rid, 3)


if __name__ == '__main__':
    unittest.main()
