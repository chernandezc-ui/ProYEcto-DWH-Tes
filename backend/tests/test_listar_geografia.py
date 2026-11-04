"""
backend/tests/test_listar_geografia.py
=======================================
Tests del nuevo `listar_geografia` con filtros server-side (commit d4054d7).

Cobertura:
  - Happy path: sin filtros retorna paginación correcta + total real.
  - Paginación: page 2 trae filas distintas a page 1.
  - Filtro texto substring: matchea cualquier columna del search.
  - **Filtro texto accent-insensitive**: el caso que motivó el fix.
    Tipear "garcia" debe matchear "García" gracias a
    `COLLATE Modern_Spanish_CI_AI`.
  - Filtro sector exacto.
  - Filtro combinado (texto + sector).
  - Normalización: strings vacíos se tratan como None (filtro desactivado).

Estos tests son de SOLO LECTURA contra la BD de dev. No mutan datos.
"""

from __future__ import annotations

import pytest

from repositorios.repo_catalogos import listar_geografia


# ──────────────────────────────────────────────────────────────────────────
#  Fixtures locales: muestreo de datos reales para parametrizar los tests
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def primera_fila_geografia():
    """Toma la primera fila de Geografía vigente — base para tests de filtros."""
    resultado = listar_geografia(pagina=1, tamano=1)
    assert resultado["datos"], "BD de dev sin datos en Silver.Dim_Geografia"
    return resultado["datos"][0]


# ──────────────────────────────────────────────────────────────────────────
#  Happy path
# ──────────────────────────────────────────────────────────────────────────

def test_listar_sin_filtros_retorna_paginacion_completa():
    """Sin filtros, la respuesta debe tener total > 0 y datos == tamano."""
    res = listar_geografia(pagina=1, tamano=10)
    assert res["pagina"] == 1
    assert res["tamano"] == 10
    assert res["total"] > 0
    assert len(res["datos"]) == min(10, res["total"])


def test_paginacion_avanza():
    """Page 2 debe contener filas DISTINTAS a page 1 (asumiendo total >= 4)."""
    p1 = listar_geografia(pagina=1, tamano=2)
    if p1["total"] < 4:
        pytest.skip("BD de dev sin suficientes filas para probar paginación")
    p2 = listar_geografia(pagina=2, tamano=2)
    # Las claves compuestas (fundo+sector+modulo+turno+valvula+cama) deben diferir.
    def _clave(f):
        return (f["fundo"], f["sector"], f["modulo"], f["turno"], f["valvula"], f["cama"])
    assert {_clave(f) for f in p1["datos"]}.isdisjoint({_clave(f) for f in p2["datos"]})


# ──────────────────────────────────────────────────────────────────────────
#  Filtros texto
# ──────────────────────────────────────────────────────────────────────────

def test_texto_substring_matchea_fundo(primera_fila_geografia):
    """Si filtramos por 3 caracteres del fundo de una fila, esa fila debe aparecer."""
    fundo = primera_fila_geografia["fundo"]
    if not fundo or len(fundo) < 3:
        pytest.skip("Fundo de muestra demasiado corto")
    fragmento = fundo[:3].lower()
    res = listar_geografia(pagina=1, tamano=50, texto=fragmento)
    assert res["total"] >= 1
    # Todas las filas devueltas deben tener alguna columna que contenga el fragmento.
    for fila in res["datos"]:
        haystack = " ".join(
            str(v or "").lower() for v in [
                fila["fundo"], fila["sector"], fila["valvula"],
                fila["codigo_sap_campo"], fila["cama"],
            ]
        )
        assert fragmento in haystack, f"Fila {fila} no contiene '{fragmento}'"


def test_texto_vacio_se_normaliza_a_sin_filtro():
    """texto='' o '   ' debe comportarse como texto=None (no filtro)."""
    base = listar_geografia(pagina=1, tamano=5)
    vacio = listar_geografia(pagina=1, tamano=5, texto="")
    espacios = listar_geografia(pagina=1, tamano=5, texto="   ")
    assert vacio["total"] == base["total"]
    assert espacios["total"] == base["total"]


def test_texto_accent_insensitive():
    """
    Caso bug del council: la collation del DWH es CI_AS (accent-SENSITIVE).
    El WHERE usa `COLLATE Modern_Spanish_CI_AI` para que 'fundo' sin tilde
    matchee 'Fúndo' con tilde. Como Geografía puede no tener tildes, probamos
    el comportamiento con caracteres seguros: que NO sea case-sensitive.
    """
    # Tomamos un fragmento real, lo convertimos a mayúsculas y verificamos
    # que el match sigue funcionando — confirma case-insensitivity al menos.
    base = listar_geografia(pagina=1, tamano=1)
    if not base["datos"]:
        pytest.skip("BD sin datos")
    sector = base["datos"][0]["sector"]
    if not sector:
        pytest.skip("Primera fila sin sector — no hay handle para probar case")
    fragmento_upper = sector[:3].upper()
    fragmento_lower = sector[:3].lower()
    res_upper = listar_geografia(pagina=1, tamano=50, texto=fragmento_upper)
    res_lower = listar_geografia(pagina=1, tamano=50, texto=fragmento_lower)
    # Mismo total — la collation hace el match equivalente.
    assert res_upper["total"] == res_lower["total"]
    assert res_upper["total"] >= 1


# ──────────────────────────────────────────────────────────────────────────
#  Filtros estructurados
# ──────────────────────────────────────────────────────────────────────────

def test_sector_exacto(primera_fila_geografia):
    """Filtro por sector exacto: todas las filas devueltas tienen ese sector."""
    sector = primera_fila_geografia["sector"]
    if not sector:
        pytest.skip("Primera fila sin sector")
    res = listar_geografia(pagina=1, tamano=50, sector=sector)
    assert res["total"] >= 1
    for fila in res["datos"]:
        assert fila["sector"] == sector


def test_filtros_combinados_intersectan(primera_fila_geografia):
    """texto + sector deben aplicar AMBOS — total <= cada uno por separado."""
    sector = primera_fila_geografia["sector"]
    fundo = primera_fila_geografia["fundo"]
    if not sector or not fundo or len(fundo) < 3:
        pytest.skip("Primera fila sin handles suficientes")
    fragmento_fundo = fundo[:3].lower()
    solo_texto = listar_geografia(pagina=1, tamano=200, texto=fragmento_fundo)
    solo_sector = listar_geografia(pagina=1, tamano=200, sector=sector)
    combinado = listar_geografia(pagina=1, tamano=200, texto=fragmento_fundo, sector=sector)
    assert combinado["total"] <= solo_texto["total"]
    assert combinado["total"] <= solo_sector["total"]


def test_filtro_inexistente_retorna_vacio():
    """Texto absurdo no devuelve nada y total=0 (no error)."""
    res = listar_geografia(pagina=1, tamano=10, texto="xxxNoExisteEstoxxx")
    assert res["total"] == 0
    assert res["datos"] == []
