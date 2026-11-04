"""
test_base_processor_puro.py
===========================
Tests unitarios de lógica pura extraída de _base_processor.py.
Sin dependencia de SQL Server ni conexiones de red.

Cubre:
- Inferencia de tipos SQL
- Construcción de cláusulas MERGE/WHERE NOT EXISTS
- Normalización de claves únicas
- Deduplicación intra-batch (con y sin tiebreaker)
"""

import datetime
import unittest


# ── Lógica pura extraída / espejada de _base_processor.py ──────────────────

def inferir_tipo_sql(valor) -> str:
    """Espejo de BaseFactProcessor._tipo_sql_para_valor()"""
    if isinstance(valor, bool):
        return "BIT"
    if isinstance(valor, int):
        return "BIGINT"
    if isinstance(valor, float):
        return "FLOAT"
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return "DATETIME2"
    return "NVARCHAR(MAX)"


def construir_clausula_on(columnas_clave: list[str], alias_src: str = "src", alias_dest: str = "dest") -> str:
    """
    Construye la cláusula ON para un MERGE o JOIN de deduplicación.
    Espejo de la lógica inline en _ejecutar_insercion_masiva_segura.
    """
    if not columnas_clave:
        raise ValueError("columnas_clave vacías — no se puede construir cláusula ON.")
    return " AND ".join([f"{alias_src}.[{c}] = {alias_dest}.[{c}]" for c in columnas_clave])


def filtrar_columnas_fisicas(todas_cols: list[str], columnas_clave: list[str]) -> list[str]:
    """
    Filtra columnas clave para quedarse solo con las que existen en el payload
    y no son auxiliares (como id_origen_rastreo).
    Espejo de la lógica de filtrado en _ejecutar_insercion_masiva_segura.
    """
    return [c for c in columnas_clave if c in todas_cols and c != 'id_origen_rastreo']


def filtrar_columnas_destino(todas_cols: list[str]) -> list[str]:
    """
    Filtra columnas para INSERT/UPDATE excluyendo auxiliares.
    Espejo de la lógica de columnas_dest en _ejecutar_insercion_masiva_segura.
    """
    return [c for c in todas_cols if c != 'id_origen_rastreo' and not c.endswith('_Virtual')]


EPOCH = datetime.datetime(1900, 1, 1)


def dedup_tiebreaker(lista_dicts: list[dict], columnas_clave: list[str], col_ts: str) -> tuple[list[dict], int]:
    """
    Política 'último timestamp gana'. Retorna (lista_limpia, resueltos_por_tiebreaker).
    """
    mejor: dict[tuple, dict] = {}
    resueltos = 0
    for row in lista_dicts:
        clave = tuple(row.get(c) for c in columnas_clave)
        ts = row.get(col_ts) or EPOCH
        if clave not in mejor:
            mejor[clave] = row
        else:
            ts_actual = mejor[clave].get(col_ts) or EPOCH
            if ts > ts_actual:
                mejor[clave] = row
            resueltos += 1
    return list(mejor.values()), resueltos


def dedup_primero_gana(lista_dicts: list[dict], columnas_clave: list[str]) -> tuple[list[dict], list[dict]]:
    """
    Política sin tiebreaker: primer visto gana.
    Retorna (limpios, descartados).
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


# ── Tests ──────────────────────────────────────────────────────────────────

class TestInferirTipoSQL(unittest.TestCase):
    """Validar que la inferencia de tipos SQL mapea correctamente Python → SQL Server."""

    def test_bool_a_bit(self):
        self.assertEqual(inferir_tipo_sql(True), "BIT")
        self.assertEqual(inferir_tipo_sql(False), "BIT")

    def test_int_a_bigint(self):
        self.assertEqual(inferir_tipo_sql(42), "BIGINT")
        self.assertEqual(inferir_tipo_sql(0), "BIGINT")

    def test_float_a_float(self):
        self.assertEqual(inferir_tipo_sql(3.14), "FLOAT")

    def test_date_a_datetime2(self):
        self.assertEqual(inferir_tipo_sql(datetime.date.today()), "DATETIME2")
        self.assertEqual(inferir_tipo_sql(datetime.datetime.now()), "DATETIME2")

    def test_str_a_nvarchar(self):
        self.assertEqual(inferir_tipo_sql("hola"), "NVARCHAR(MAX)")

    def test_none_a_nvarchar(self):
        self.assertEqual(inferir_tipo_sql(None), "NVARCHAR(MAX)")

    def test_bool_antes_de_int(self):
        """bool es subclase de int en Python; debe mapearse a BIT, no BIGINT."""
        self.assertEqual(inferir_tipo_sql(True), "BIT")


class TestConstruirClausulaON(unittest.TestCase):
    """Validar la generación de cláusulas ON para MERGE/JOIN."""

    def test_una_columna(self):
        resultado = construir_clausula_on(["ID_Geografia"])
        self.assertEqual(resultado, "src.[ID_Geografia] = dest.[ID_Geografia]")

    def test_multiples_columnas(self):
        columnas = ["ID_Geografia", "ID_Tiempo", "ID_Variedad"]
        resultado = construir_clausula_on(columnas)
        self.assertIn("src.[ID_Geografia] = dest.[ID_Geografia]", resultado)
        self.assertIn("src.[ID_Tiempo] = dest.[ID_Tiempo]", resultado)
        self.assertEqual(resultado.count(" AND "), 2)

    def test_aliases_personalizados(self):
        resultado = construir_clausula_on(["Punto"], alias_src="tmp", alias_dest="d")
        self.assertEqual(resultado, "tmp.[Punto] = d.[Punto]")

    def test_columnas_vacias_lanza_error(self):
        with self.assertRaises(ValueError):
            construir_clausula_on([])


class TestFiltrarColumnasPayload(unittest.TestCase):
    """Validar el filtrado de columnas auxiliares."""

    def test_excluye_id_origen_rastreo(self):
        todas = ["ID_Geografia", "ID_Tiempo", "id_origen_rastreo", "Cantidad"]
        clave = ["ID_Geografia", "ID_Tiempo", "id_origen_rastreo"]
        resultado = filtrar_columnas_fisicas(todas, clave)
        self.assertNotIn("id_origen_rastreo", resultado)
        self.assertEqual(resultado, ["ID_Geografia", "ID_Tiempo"])

    def test_excluye_columnas_no_en_payload(self):
        todas = ["ID_Geografia", "Cantidad"]
        clave = ["ID_Geografia", "ID_Tiempo", "Columna_Fantasma"]
        resultado = filtrar_columnas_fisicas(todas, clave)
        self.assertEqual(resultado, ["ID_Geografia"])

    def test_filtrar_columnas_destino(self):
        todas = ["ID_Geografia", "id_origen_rastreo", "Datos_Virtual", "Cantidad"]
        resultado = filtrar_columnas_destino(todas)
        self.assertNotIn("id_origen_rastreo", resultado)
        self.assertNotIn("Datos_Virtual", resultado)
        self.assertIn("ID_Geografia", resultado)
        self.assertIn("Cantidad", resultado)


class TestDedupTiebreaker(unittest.TestCase):
    """Tests para deduplicación con tiebreaker."""

    CLAVE = ["ID_Geografia", "ID_Tiempo"]
    T1 = datetime.datetime(2026, 3, 19, 16, 19, 12)
    T2 = datetime.datetime(2026, 3, 19, 16, 23, 18)

    def test_gana_mayor_timestamp(self):
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 100, "ts": self.T1, "valor": "viejo"},
            {"ID_Geografia": 1, "ID_Tiempo": 100, "ts": self.T2, "valor": "nuevo"},
        ]
        resultado, resueltos = dedup_tiebreaker(lote, self.CLAVE, "ts")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["valor"], "nuevo")
        self.assertEqual(resueltos, 1)

    def test_null_timestamp_pierde(self):
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 100, "ts": None, "valor": "sin_ts"},
            {"ID_Geografia": 1, "ID_Tiempo": 100, "ts": self.T1, "valor": "con_ts"},
        ]
        resultado, resueltos = dedup_tiebreaker(lote, self.CLAVE, "ts")
        self.assertEqual(resultado[0]["valor"], "con_ts")
        self.assertEqual(resueltos, 1)

    def test_sin_duplicados_resueltos_cero(self):
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 100, "ts": self.T1, "valor": "A"},
            {"ID_Geografia": 2, "ID_Tiempo": 100, "ts": self.T2, "valor": "B"},
        ]
        resultado, resueltos = dedup_tiebreaker(lote, self.CLAVE, "ts")
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resueltos, 0)

    def test_tres_filas_misma_clave(self):
        T0 = datetime.datetime(2026, 1, 1)
        T_mid = datetime.datetime(2026, 2, 1)
        T_max = datetime.datetime(2026, 3, 1)
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 1, "ts": T0, "valor": "A"},
            {"ID_Geografia": 1, "ID_Tiempo": 1, "ts": T_mid, "valor": "B"},
            {"ID_Geografia": 1, "ID_Tiempo": 1, "ts": T_max, "valor": "C"},
        ]
        resultado, resueltos = dedup_tiebreaker(lote, self.CLAVE, "ts")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["valor"], "C")
        self.assertEqual(resueltos, 2)


class TestDedupPrimeroGana(unittest.TestCase):
    """Tests para deduplicación sin tiebreaker."""

    CLAVE = ["ID_Geografia", "ID_Tiempo"]

    def test_primer_llegado_gana(self):
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 1, "valor": "primero"},
            {"ID_Geografia": 1, "ID_Tiempo": 1, "valor": "segundo"},
        ]
        limpios, descartados = dedup_primero_gana(lote, self.CLAVE)
        self.assertEqual(len(limpios), 1)
        self.assertEqual(limpios[0]["valor"], "primero")
        self.assertEqual(len(descartados), 1)

    def test_sin_duplicados(self):
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 1, "valor": "A"},
            {"ID_Geografia": 1, "ID_Tiempo": 2, "valor": "B"},
        ]
        limpios, descartados = dedup_primero_gana(lote, self.CLAVE)
        self.assertEqual(len(limpios), 2)
        self.assertEqual(len(descartados), 0)

    def test_multiples_duplicados(self):
        lote = [
            {"ID_Geografia": 1, "ID_Tiempo": 1, "valor": "A"},
            {"ID_Geografia": 1, "ID_Tiempo": 1, "valor": "B"},
            {"ID_Geografia": 1, "ID_Tiempo": 1, "valor": "C"},
        ]
        limpios, descartados = dedup_primero_gana(lote, self.CLAVE)
        self.assertEqual(len(limpios), 1)
        self.assertEqual(len(descartados), 2)


if __name__ == "__main__":
    unittest.main()
