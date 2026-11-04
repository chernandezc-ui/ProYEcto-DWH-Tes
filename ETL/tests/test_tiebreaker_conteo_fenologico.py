"""
Pruebas unitarias para la política "último timestamp gana".

Testea directamente la lógica de deduplicación extraída como función pura,
sin necesidad de SQL Server ni del BaseFactProcessor completo.
"""

import datetime
import unittest

# ── Lógica pura del tiebreaker (extraída del método _limpiar_duplicados_internos) ──

EPOCH = datetime.datetime(1900, 1, 1)


def dedup_tiebreaker(lista_dicts: list[dict], columnas_clave: list[str], col_ts: str) -> list[dict]:
    """
    Política 'último timestamp gana': entre filas con la misma clave, conserva
    la de mayor valor en col_ts. NULL se trata como EPOCH (el más antiguo posible).
    Equivale al bloque 'if tiebreaker:' de BaseFactProcessor._limpiar_duplicados_internos.
    """
    mejor: dict[tuple, dict] = {}
    for row in lista_dicts:
        clave = tuple(row.get(c) for c in columnas_clave)
        ts = row.get(col_ts) or EPOCH
        if clave not in mejor:
            mejor[clave] = row
        else:
            ts_actual = mejor[clave].get(col_ts) or EPOCH
            if ts > ts_actual:
                mejor[clave] = row
    return list(mejor.values())


def dedup_primero_gana(lista_dicts: list[dict], columnas_clave: list[str]) -> tuple[list[dict], list[dict]]:
    """
    Política original sin tiebreaker: conserva el primer visto, devuelve
    (lista_limpia, lista_descartados).
    """
    vistos: set[tuple] = set()
    limpios, descartados = [], []
    for row in lista_dicts:
        clave = tuple(row.get(c) for c in columnas_clave)
        if clave in vistos:
            descartados.append(row)
        else:
            vistos.add(clave)
            limpios.append(row)
    return limpios, descartados


# ── Helpers ──

CLAVE = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Estado_Fenologico', 'Punto']
T1 = datetime.datetime(2026, 3, 19, 16, 19, 12)   # más antiguo
T2 = datetime.datetime(2026, 3, 19, 16, 23, 18)   # más reciente


def _fila(geo, tiempo, variedad, estado, punto, ts, cantidad, id_origen):
    return {
        'ID_Geografia': geo, 'ID_Tiempo': tiempo, 'ID_Variedad': variedad,
        'ID_Estado_Fenologico': estado, 'Punto': punto,
        'Fecha_Registro': ts, 'Cantidad_Organos': cantidad,
        'id_origen_rastreo': id_origen,
    }


# ── Tests con tiebreaker ──

class TestTiebreakerIntraBatch(unittest.TestCase):

    def _dedup(self, lote):
        return dedup_tiebreaker(lote, CLAVE, 'Fecha_Registro')

    def test_gana_timestamp_mayor(self):
        lote = [
            _fila(1, 100, 5, 3, '2', T1, cantidad=3,   id_origen=10),
            _fila(1, 100, 5, 3, '2', T2, cantidad=165, id_origen=11),
        ]
        resultado = self._dedup(lote)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['Cantidad_Organos'], 165)
        self.assertEqual(resultado[0]['id_origen_rastreo'], 11)

    def test_gana_timestamp_mayor_orden_inverso(self):
        """El más reciente llega primero en el batch; el segundo (más antiguo) se descarta."""
        lote = [
            _fila(1, 100, 5, 3, '2', T2, cantidad=165, id_origen=11),
            _fila(1, 100, 5, 3, '2', T1, cantidad=3,   id_origen=10),
        ]
        resultado = self._dedup(lote)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['Cantidad_Organos'], 165)

    def test_sin_duplicados_pasa_todo(self):
        lote = [
            _fila(1, 100, 5, 3, '1', T1, cantidad=100, id_origen=1),
            _fila(1, 100, 5, 3, '2', T1, cantidad=200, id_origen=2),
            _fila(2, 100, 5, 3, '1', T2, cantidad=300, id_origen=3),
        ]
        self.assertEqual(len(self._dedup(lote)), 3)

    def test_null_pierde_contra_timestamp_real(self):
        lote = [
            _fila(1, 100, 5, 3, '2', None, cantidad=99, id_origen=20),
            _fila(1, 100, 5, 3, '2', T1,   cantidad=3,  id_origen=21),
        ]
        resultado = self._dedup(lote)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['Cantidad_Organos'], 3)

    def test_descartados_no_generan_cuarentena(self):
        """La función pura no llama a registrar_rechazo — no hay cuarentena por diseño."""
        lote = [
            _fila(1, 100, 5, 3, '2', T1, cantidad=3,   id_origen=10),
            _fila(1, 100, 5, 3, '2', T2, cantidad=165, id_origen=11),
        ]
        resultado = self._dedup(lote)
        # Solo 1 fila sobrevive y no hay estructura de error asociada
        self.assertEqual(len(resultado), 1)

    def test_tres_filas_misma_clave_gana_la_mayor(self):
        T0   = datetime.datetime(2026, 3, 16, 16, 47, 17)
        T_mid = datetime.datetime(2026, 3, 16, 16, 50, 33)
        T_max = datetime.datetime(2026, 3, 16, 16, 52, 2)
        lote = [
            _fila(1, 100, 5, 3, '2', T0,    cantidad=17, id_origen=30),
            _fila(1, 100, 5, 3, '2', T_mid, cantidad=17, id_origen=31),
            _fila(1, 100, 5, 3, '2', T_max, cantidad=4,  id_origen=32),
        ]
        resultado = self._dedup(lote)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['id_origen_rastreo'], 32)
        self.assertEqual(resultado[0]['Cantidad_Organos'], 4)

    def test_ejemplo_real_ej1_valvula43_punto2(self):
        """Ej. 1 del análisis: BGV=165 (16:23:18) debe ganar a BGV=3 (16:19:12)."""
        T_menor = datetime.datetime(2026, 3, 19, 16, 19, 12)
        T_mayor = datetime.datetime(2026, 3, 19, 16, 23, 18)
        lote = [
            {**_fila(43, 20260319, 1, 7, '2', T_menor, 1,  id_origen=100), 'BGV': 3},
            {**_fila(43, 20260319, 1, 7, '2', T_mayor, 13, id_origen=101), 'BGV': 165},
        ]
        resultado = self._dedup(lote)
        self.assertEqual(resultado[0]['BGV'], 165)

    def test_ejemplo_real_ej2_valvula50_punto2(self):
        """Ej. 2 del análisis: BF=81 (17:09:00) debe ganar a BF=39 (17:08:08)."""
        T_menor = datetime.datetime(2026, 3, 18, 17, 8, 8)
        T_mayor = datetime.datetime(2026, 3, 18, 17, 9, 0)
        lote = [
            {**_fila(50, 20260318, 1, 3, '2', T_menor, 39, id_origen=200), 'BF': 39},
            {**_fila(50, 20260318, 1, 3, '2', T_mayor, 81, id_origen=201), 'BF': 81},
        ]
        resultado = self._dedup(lote)
        self.assertEqual(resultado[0]['BF'], 81)


# ── Tests sin tiebreaker (comportamiento original) ──

class TestSinTiebreaker(unittest.TestCase):

    def test_primer_llegado_gana(self):
        lote = [
            _fila(1, 100, 5, 3, '2', T1, cantidad=3,   id_origen=10),
            _fila(1, 100, 5, 3, '2', T2, cantidad=165, id_origen=11),
        ]
        limpios, descartados = dedup_primero_gana(lote, CLAVE)
        self.assertEqual(len(limpios), 1)
        self.assertEqual(limpios[0]['Cantidad_Organos'], 3)
        self.assertEqual(len(descartados), 1)

    def test_sin_duplicados_sin_tiebreaker(self):
        lote = [
            _fila(1, 100, 5, 3, '1', T1, cantidad=10, id_origen=1),
            _fila(1, 100, 5, 3, '2', T1, cantidad=20, id_origen=2),
        ]
        limpios, descartados = dedup_primero_gana(lote, CLAVE)
        self.assertEqual(len(limpios), 2)
        self.assertEqual(len(descartados), 0)


if __name__ == '__main__':
    unittest.main()
