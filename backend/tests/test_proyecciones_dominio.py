"""Validación canónica y cálculo puro de escenarios, sin repositorios."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from dominio import proyecciones as dominio


def test_importar_dominio_no_requiere_repositorios_ni_configuracion():
    backend = Path(__file__).resolve().parents[1]
    programa = """
import importlib.abc
import sys

class SinInfraestructura(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'repositorios', 'servicios', 'nucleo', 'comun', 'sqlalchemy', 'pyodbc'}:
            raise AssertionError('El dominio depende de infraestructura: ' + fullname)

sys.meta_path.insert(0, SinInfraestructura())
sys.path.insert(0, sys.argv[1])
from dominio.proyecciones import calcular_proyeccion
import pandas as pd
resultado = calcular_proyeccion(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 20260101)
assert resultado['df_detalle'].empty
assert resultado['df_semanal'].empty
assert resultado['kpis'] == {}
"""
    resultado = subprocess.run(
        [sys.executable, "-I", "-c", programa, str(backend)],
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_normalizar_claves_json_y_matriz_parcial_sin_mutar_entrada():
    matriz = {"fase_2": {"1": .14, "2": .40, "3": None}}
    original = deepcopy(matriz)
    normalizada = dominio.normalizar_matriz_inputs(matriz)
    assert matriz == original
    assert set(normalizada) == {"fase_2"}
    assert all(type(semana) is int for semana in normalizada["fase_2"])
    assert dominio.cerrar_matriz(normalizada) == {"fase_2": [.14, .40, .46, 0., 0., 0.]}
    assert normalizada == dominio.normalizar_matriz_inputs({"fase_2": {1: .14, 2: .40, 3: None}})


@pytest.mark.parametrize("matriz", [
    None,
    {},
    [],
    {"desconocido": {1: 1.}},
    {"cosechable": []},
    {"cosechable": {0: 0.}},
    {"cosechable": {7: 0.}},
    {"cosechable": {True: 0.}},
    {"cosechable": {"01": 0.}},
    {"cosechable": {1: .1, "1": .1}},
    {"cosechable": {1: True}},
    {"cosechable": {1: float("nan")}},
    {"cosechable": {1: float("inf")}},
    {"cosechable": {1: float("-inf")}},
    {"cosechable": {1: -.01}},
    {"cosechable": {1: 1.01}},
    {"cosechable": {1: "no numérico"}},
    {"cosechable": {1: .6, 2: .5}},
    {"cosechable": {1: None, 2: .2}},
])
def test_matriz_invalida_rechazada_por_el_dominio(matriz):
    with pytest.raises(dominio.ErrorValidacionProyeccion):
        dominio.normalizar_matriz_inputs(matriz)


@pytest.mark.parametrize("matriz", [
    {"cosechable": {1: .5, 2: .5000005}},
    {"cosechable": {1: None, 2: .0000005}},
])
def test_suma_y_cierre_conservan_tolerancia_numerica_existente(matriz):
    normalizada = dominio.normalizar_matriz_inputs(matriz)
    assert sum(dominio.cerrar_matriz(normalizada)["cosechable"]) == pytest.approx(1., abs=1e-6)


@pytest.mark.parametrize("matriz", [
    {"cosechable": {1: .5, 2: .500002}},
    {"cosechable": {1: None, 2: .000002}},
])
def test_suma_y_cierre_superiores_a_tolerancia_se_rechazan(matriz):
    with pytest.raises(dominio.ErrorValidacionProyeccion):
        dominio.normalizar_matriz_inputs(matriz)


@pytest.mark.parametrize("fecha", [
    20260229, 20261301, 20260010, 2026011, 202601011,
    True, 20260101.0, "2026-01-01", "٢٠٢٦٠١٠١",
])
def test_fecha_debe_ser_real_y_tener_formato_yyyymmdd(fecha):
    with pytest.raises(dominio.ErrorValidacionProyeccion):
        dominio.preparar_parametros(fecha)


def test_fecha_bisiesta_y_default_no_comparten_diccionarios_mutables():
    original = deepcopy(dominio.MATRIZ_INPUTS_DEFAULT)
    fecha, matriz = dominio.preparar_parametros(20240229)
    assert fecha == datetime(2024, 2, 29)
    matriz["cosechable"][1] = 0.
    assert dominio.MATRIZ_INPUTS_DEFAULT == original
    assert dominio.preparar_parametros(20240229)[1]["cosechable"][1] == 1.


@pytest.mark.parametrize("margenes", [
    {"margen_pesimista": True},
    {"margen_optimista": False},
    {"margen_pesimista": float("nan")},
    {"margen_optimista": float("inf")},
    {"margen_pesimista": float("-inf")},
    {"margen_pesimista": -.01},
    {"margen_optimista": -.01},
    {"margen_pesimista": 1.2, "margen_optimista": 1.1},
    {"margen_pesimista": None},
])
def test_margenes_finitos_no_negativos_y_ordenados(margenes):
    with pytest.raises(dominio.ErrorValidacionProyeccion):
        dominio.preparar_parametros(20260101, **margenes)


@pytest.mark.parametrize("margenes", [(0., 0.), (1.1, 1.2)])
def test_margenes_validos_admiten_cero_y_factores_superiores_a_uno(margenes):
    fecha, matriz = dominio.preparar_parametros(
        20260101, margen_pesimista=margenes[0], margen_optimista=margenes[1],
    )
    assert fecha == datetime(2026, 1, 1)
    assert matriz


def _conteos_dos_fundos():
    return pd.DataFrame([
        {
            "id_geografia": geo, "id_variedad": 5, "id_fundo": fundo,
            "fundo": nombre, "modulo": 1, "turno": 1, "valvula": 1,
            "variedad": "V", "condicion": "C", "certificacion": "X",
            "puntos": 1, "id_estado": 9, "total_organos": 10,
        }
        for geo, fundo, nombre in [(101, 1, "A"), (202, 2, "B")]
    ])


def test_calculo_puro_conserva_identidades_y_pesos_de_cada_fundo():
    conteo = _conteos_dos_fundos()
    plantas = pd.DataFrame([
        {"id_geografia": 101, "plantas_sampleadas": 100, "pct_productivas_s1": 1.},
        {"id_geografia": 202, "plantas_sampleadas": 200, "pct_productivas_s1": 1.},
    ])
    pesos = pd.DataFrame([
        {"id_fundo": 1, "modulo": 1, "variedad": "V", "semana_iso": 2, "peso_baya_kg": .002},
        {"id_fundo": 2, "modulo": 1, "variedad": "V", "semana_iso": 2, "peso_baya_kg": .004},
    ])
    originales = [frame.copy(deep=True) for frame in (conteo, plantas, pesos)]

    resultado = dominio.calcular_proyeccion(conteo, plantas, pesos, 20260101)

    detalle = resultado["df_detalle"]
    assert len(detalle) == 12
    assert set(zip(detalle.id_geografia, detalle.id_fundo, detalle.id_variedad)) == {
        (101, 1, 5), (202, 2, 5),
    }
    w1 = detalle[detalle.semana == 1].set_index("id_geografia")
    assert w1.loc[101, "kg_base"] == .2
    assert w1.loc[202, "kg_base"] == .8
    assert resultado["df_semanal"].kg_base.tolist() == [1., 0., 0., 0., 0., 0.]
    assert resultado["kpis"]["total_plantas"] == 300
    assert resultado["kpis"]["unidades_cubiertas"] == 2
    assert resultado["kpis"]["unidades_totales"] == 2
    for original, actual in zip(originales, (conteo, plantas, pesos)):
        pd.testing.assert_frame_equal(actual, original)


def test_calculo_puro_vacio_y_validacion_incluso_sin_datos():
    vacios = [pd.DataFrame(), pd.DataFrame(), pd.DataFrame()]
    resultado = dominio.calcular_proyeccion(*vacios, 20260101)
    assert resultado["df_semanal"].empty
    assert resultado["df_detalle"].empty
    assert resultado["kpis"] == {}
    with pytest.raises(dominio.ErrorValidacionProyeccion):
        dominio.calcular_proyeccion(*vacios, 20260229)
