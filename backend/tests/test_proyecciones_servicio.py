"""La validación debe anteceder a las lecturas y escrituras del repositorio."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from dominio.proyecciones import ErrorValidacionProyeccion
from nucleo.excepciones import ErrorBaseDatos
from servicios import servicio_proyecciones as servicio


@pytest.fixture
def repositorio_simulado(monkeypatch):
    mocks = SimpleNamespace(
        extraer=Mock(return_value=(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())),
        guardar=Mock(side_effect=lambda detalle, *_: {
            "insertados": len(detalle), "saltados": 0, "errores": [],
        }),
        leer_matriz=Mock(return_value=None),
        guardar_matriz=Mock(return_value=True),
    )
    for nombre, doble in [
        ("extraer_datos_granulares", mocks.extraer),
        ("guardar_proyeccion", mocks.guardar),
        ("leer_param_json", mocks.leer_matriz),
        ("guardar_param_json", mocks.guardar_matriz),
    ]:
        monkeypatch.setattr(servicio.repo, nombre, doble)
    return mocks


@pytest.mark.asyncio
@pytest.mark.parametrize("parametros", [
    {"id_tiempo": 20260229},
    {"id_tiempo": True},
    {"matriz_inputs": {}},
    {"matriz_inputs": {"ajeno": {1: 1.}}},
    {"matriz_inputs": {"cosechable": {1: True}}},
    {"matriz_inputs": {"cosechable": {1: float("nan")}}},
    {"matriz_inputs": {"cosechable": {1: None, 2: .2}}},
    {"margen_pesimista": float("inf")},
    {"margen_optimista": True},
    {"margen_pesimista": -.1},
    {"margen_pesimista": 1.2, "margen_optimista": 1.1},
])
async def test_ejecutar_valida_antes_de_consultar_o_guardar(repositorio_simulado, parametros):
    argumentos = {"id_tiempo": 20260101, **parametros}
    with pytest.raises(ErrorValidacionProyeccion):
        await servicio.ejecutar_proyeccion(**argumentos)
    repositorio_simulado.extraer.assert_not_called()
    repositorio_simulado.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_error_de_lectura_no_intenta_guardado(repositorio_simulado):
    repositorio_simulado.extraer.side_effect = ErrorBaseDatos()
    with pytest.raises(ErrorBaseDatos):
        await servicio.ejecutar_proyeccion(20260101)
    repositorio_simulado.guardar.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("resumen", [
    None,
    {},
    {"insertados": 5, "saltados": 0, "errores": []},
    {"insertados": 6, "saltados": 1, "errores": []},
    {"insertados": 6, "saltados": 0, "errores": ["SELECT SQL_SINTETICO_PRIVADO"]},
    {"insertados": 6, "saltados": 0, "errores": None},
    Mock(),
])
async def test_guardado_incompleto_no_se_reporta_como_exito(repositorio_simulado, resumen):
    repositorio_simulado.guardar.side_effect = None
    repositorio_simulado.guardar.return_value = resumen
    detalle = pd.DataFrame({"kg_base": [1.] * 6})
    with pytest.raises(ErrorBaseDatos) as error:
        await servicio.guardar_resultado_proyeccion(detalle, 20260101, .9, 1.1)
    assert error.value.status_code == 503
    assert "SQL_SINTETICO_PRIVADO" not in error.value.detail
    repositorio_simulado.guardar.assert_called_once()


@pytest.mark.asyncio
async def test_guardado_exige_resumen_completo_y_conserva_datos(repositorio_simulado):
    detalle = pd.DataFrame({"kg_base": [1., 2.]})
    resultado = await servicio.guardar_resultado_proyeccion(detalle, 20260101, .9, 1.1)
    assert resultado is None
    repositorio_simulado.guardar.assert_called_once()
    pd.testing.assert_frame_equal(repositorio_simulado.guardar.call_args.args[0], detalle)
    assert repositorio_simulado.guardar.call_args.args[1:] == (20260101, .9, 1.1)


@pytest.mark.asyncio
@pytest.mark.parametrize("matriz", [
    {}, {"ajeno": {1: 1.}}, {"cosechable": {"1": True}},
    {"cosechable": {"1": None, "2": .2}},
])
async def test_guardar_matriz_valida_antes_de_escribir(repositorio_simulado, matriz):
    with pytest.raises(ErrorValidacionProyeccion):
        await servicio.guardar_matriz_proyeccion(matriz)
    repositorio_simulado.leer_matriz.assert_not_called()
    repositorio_simulado.guardar_matriz.assert_not_called()


@pytest.mark.asyncio
async def test_guardar_matriz_normaliza_claves_sin_mutar_payload(repositorio_simulado):
    matriz = {"fase_2": {"1": .14, "2": .40, "3": None}}
    original = deepcopy(matriz)
    assert await servicio.guardar_matriz_proyeccion(matriz) == {"ok": True}
    assert matriz == original
    repositorio_simulado.guardar_matriz.assert_called_once()
    clave, guardada, descripcion = repositorio_simulado.guardar_matriz.call_args.args
    assert clave == "PROY_SIXWEEK_MATRIZ_INPUTS"
    assert guardada == {"fase_2": {1: .14, 2: .40, 3: None, 4: None, 5: None, 6: None}}
    assert descripcion == "Matriz de inputs % maduración Six-Week"


@pytest.mark.asyncio
async def test_guardar_matriz_fallida_no_devuelve_ok_false(repositorio_simulado):
    repositorio_simulado.guardar_matriz.return_value = False
    with pytest.raises(ErrorBaseDatos) as error:
        await servicio.guardar_matriz_proyeccion({"cosechable": {"1": 1.}})
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("almacenada", [None, {}, {"fase_2": {"1": .14, "2": .40, "3": None}}])
async def test_leer_matriz_conserva_formato_historico(repositorio_simulado, almacenada):
    repositorio_simulado.leer_matriz.return_value = almacenada
    assert await servicio.obtener_matriz_proyeccion() == (almacenada or {})
    repositorio_simulado.leer_matriz.assert_called_once_with("PROY_SIXWEEK_MATRIZ_INPUTS")
    repositorio_simulado.guardar_matriz.assert_not_called()
