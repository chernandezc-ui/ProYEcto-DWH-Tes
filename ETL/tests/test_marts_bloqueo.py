"""
test_marts_bloqueo.py
=====================
Bloqueo de Gold por mart: una fact bloqueante fallida solo debe frenar los
marts que ella alimenta (más los marts sin fact declarada, de forma conservadora).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gold.marts import FUNCIONES_MARTS, MARTS, marts_bloqueados_por_fallas
from utils.ejecucion import CONFIG_FACTS

TODAS = frozenset(CONFIG_FACTS)


class TestMartsBloqueadosPorFallas(unittest.TestCase):
    def test_sin_fallas_no_bloquea_nada(self):
        self.assertEqual(marts_bloqueados_por_fallas([], TODAS), set())

    def test_falla_no_bloqueante_no_bloquea(self):
        self.assertEqual(
            marts_bloqueados_por_fallas(['Fact_Cosecha_SAP'], frozenset({'Fact_Tareo'})),
            set(),
        )

    def test_falla_bloquea_solo_su_mart_y_los_sin_fact(self):
        bloqueados = marts_bloqueados_por_fallas(['Fact_Telemetria_Clima'], TODAS)
        self.assertIn('Gold.Mart_Clima', bloqueados)
        # Un mart ajeno con fact declarada sigue disponible.
        self.assertNotIn('Gold.Mart_Cosecha', bloqueados)
        self.assertNotIn('Gold.Mart_Fisiologia', bloqueados)

    def test_marts_sin_fact_se_bloquean_ante_cualquier_falla(self):
        con_fact = {m for meta in CONFIG_FACTS.values() for m in meta['marts']}
        sin_fact = {m for m in MARTS if m not in con_fact}
        self.assertTrue(sin_fact, 'se espera al menos un mart sin fact (Mart_Proyecciones)')
        bloqueados = marts_bloqueados_por_fallas(['Fact_Tareo'], TODAS)
        self.assertTrue(sin_fact <= bloqueados)

    def test_fact_sin_marts_solo_bloquea_los_sin_fact(self):
        bloqueados = marts_bloqueados_por_fallas(['Fact_Peladas'], TODAS)
        con_fact = {m for meta in CONFIG_FACTS.values() for m in meta['marts']}
        self.assertEqual(bloqueados, {m for m in MARTS if m not in con_fact})

    def test_todos_los_marts_con_funcion_estan_en_la_lista(self):
        self.assertTrue(set(FUNCIONES_MARTS) <= set(MARTS))


if __name__ == '__main__':
    unittest.main()
