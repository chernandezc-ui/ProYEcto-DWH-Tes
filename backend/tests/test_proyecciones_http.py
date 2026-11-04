"""Contratos HTTP reales de proyecciones con identidad y repositorios sintéticos."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pandas as pd
import pytest

from dominio.proyecciones import ErrorValidacionProyeccion
from nucleo.auth import UsuarioActual, obtener_usuario_actual
from nucleo.excepciones import ErrorBaseDatos
from servicios import servicio_proyecciones as servicio


BASE = "/api/v1/proyecciones"
SQL_PRIVADO = "SELECT SQL_SINTETICO_PRIVADO FROM tabla_interna"


@pytest.fixture
def api_proyecciones(monkeypatch):
    # Usar la aplicación y sus handlers reales sin ejecutar su lifespan SQL.
    from main import aplicacion

    usuario = UsuarioActual("pruebas-proyeccion", "analista_mdm", "Pruebas locales")

    async def usuario_sintetico():
        return usuario

    monkeypatch.setitem(aplicacion.dependency_overrides, obtener_usuario_actual, usuario_sintetico)
    return aplicacion, usuario


@pytest.fixture
def repositorio_http(monkeypatch):
    conteo = pd.DataFrame([{
        "id_geografia": 101, "id_variedad": 5, "id_fundo": 1,
        "fundo": "A", "modulo": 1, "turno": 2, "valvula": 3,
        "variedad": "V", "condicion": "C", "certificacion": "X",
        "puntos": 1, "id_estado": 9, "total_organos": 10,
    }])
    plantas = pd.DataFrame([{
        "id_geografia": 101, "plantas_sampleadas": 100, "pct_productivas_s1": 1.,
    }])
    pesos = pd.DataFrame([{
        "id_fundo": 1, "modulo": 1, "variedad": "V", "semana_iso": 2,
        "peso_baya_kg": .002,
    }])
    mocks = SimpleNamespace(
        extraer=Mock(return_value=(conteo, plantas, pesos)),
        guardar=Mock(side_effect=lambda detalle, *_: {
            "insertados": len(detalle), "saltados": 0, "errores": [],
        }),
        leer_matriz=Mock(return_value={"cosechable": {"1": 1.}}),
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


async def _peticion(aplicacion, metodo, ruta, cuerpo=None):
    parametros = {"headers": {"X-Request-ID": "pruebas-proyecciones"}}
    if cuerpo is not None:
        # Incluye NaN/Infinity crudos para comprobar su rechazo antes del SQL.
        parametros["content"] = json.dumps(cuerpo)
        parametros["headers"]["Content-Type"] = "application/json"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=aplicacion, raise_app_exceptions=False),
        base_url="http://test",
    ) as cliente:
        return await cliente.request(metodo, BASE + ruta, **parametros)


def _error_seguro(respuesta, codigo):
    assert respuesta.status_code == codigo, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["success"] is False
    assert cuerpo["data"] is None
    assert isinstance(cuerpo["error"], str)
    assert cuerpo["metadata"]["codigo_http"] == codigo
    assert cuerpo["metadata"]["request_id"] == "pruebas-proyecciones"
    assert "timestamp" in cuerpo["metadata"]
    assert "SQL_SINTETICO_PRIVADO" not in respuesta.text
    assert "tabla_interna" not in respuesta.text


@pytest.mark.asyncio
@pytest.mark.parametrize("cuerpo", [
    {"id_tiempo": 20260229},
    {"id_tiempo": True},
    {"id_tiempo": 20260101, "margen_pesimista": True},
    {"id_tiempo": 20260101, "margen_optimista": float("inf")},
    {"id_tiempo": 20260101, "margen_pesimista": 1.2, "margen_optimista": 1.1},
    {"id_tiempo": 20260101, "matriz_inputs": {}},
    {"id_tiempo": 20260101, "matriz_inputs": {"cosechable": {"1": True}}},
    {"id_tiempo": 20260101, "matriz_inputs": {"cosechable": {"1": float("nan")}}},
    {"id_tiempo": 20260101, "matriz_inputs": {"cosechable": {"1": None, "2": .2}}},
])
async def test_ejecutar_http_422_antes_de_lecturas_y_escrituras(api_proyecciones, repositorio_http, cuerpo):
    respuesta = await _peticion(api_proyecciones[0], "POST", "/ejecutar", cuerpo)
    _error_seguro(respuesta, 422)
    repositorio_http.extraer.assert_not_called()
    repositorio_http.guardar.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("matriz", [
    {}, {"ajeno": {"1": 1.}}, {"cosechable": {"7": 0.}},
    {"cosechable": {"1": True}},
    {"cosechable": {"1": float("nan")}},
    {"cosechable": {"1": .6, "2": .5}},
    {"cosechable": {"1": None, "2": .2}},
])
async def test_matriz_http_422_antes_de_escribir(api_proyecciones, repositorio_http, matriz):
    respuesta = await _peticion(api_proyecciones[0], "POST", "/matriz", matriz)
    _error_seguro(respuesta, 422)
    repositorio_http.guardar_matriz.assert_not_called()
    repositorio_http.leer_matriz.assert_not_called()


@pytest.mark.asyncio
async def test_ejecutar_http_conserva_respuesta_filtros_y_guardado(api_proyecciones, repositorio_http):
    respuesta = await _peticion(api_proyecciones[0], "POST", "/ejecutar", {
        "id_tiempo": "20260101", "matriz_inputs": {"cosechable": {"1": 1.}},
        "margen_pesimista": .9, "margen_optimista": 1.1,
        "modulo": 1, "variedad": "V", "condicion": "C", "fundo": "A",
    })
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"df_semanal", "df_detalle", "kpis"}
    assert len(cuerpo["df_semanal"]) == len(cuerpo["df_detalle"]) == 6
    assert cuerpo["df_semanal"][0] == {
        "semana": 1, "semana_label": "W1 (08/01)", "fecha_semana": "2026-01-08",
        "kg_proyectados": .2, "kg_pesimista": .18, "kg_optimista": .22,
        "kg_anterior": 0., "pct_variacion": 0., "tendencia": "Estable",
    }
    detalle = cuerpo["df_detalle"][0]
    assert (detalle["id_geografia"], detalle["id_variedad"], detalle["id_fundo"]) == (101, 5, 1)
    assert (detalle["fundo"], detalle["condicion"], detalle["certificacion"]) == ("A", "C", "X")
    assert cuerpo["kpis"]["total_base"] == .2
    assert cuerpo["kpis"]["total_plantas"] == 100
    repositorio_http.extraer.assert_called_once_with(20260101, 1, "V", "C", "A")
    repositorio_http.guardar.assert_called_once()
    assert len(repositorio_http.guardar.call_args.args[0]) == 6


@pytest.mark.asyncio
async def test_ejecutar_http_vacio_conserva_contrato_y_no_guarda(api_proyecciones, repositorio_http):
    repositorio_http.extraer.return_value = (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    respuesta = await _peticion(api_proyecciones[0], "POST", "/ejecutar", {"id_tiempo": 20260101})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"df_semanal": [], "df_detalle": [], "kpis": {}}
    repositorio_http.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_matriz_http_guardado_exitoso_y_lectura_compatible(api_proyecciones, repositorio_http):
    lectura = await _peticion(api_proyecciones[0], "GET", "/matriz")
    assert lectura.status_code == 200
    assert lectura.json() == {"cosechable": {"1": 1.}}
    escritura = await _peticion(api_proyecciones[0], "POST", "/matriz", {"fase_2": {"1": .14, "2": .40}})
    assert escritura.status_code == 200
    assert escritura.json() == {"ok": True}
    normalizada = repositorio_http.guardar_matriz.call_args.args[1]
    assert normalizada["fase_2"][1] == .14
    assert normalizada["fase_2"][2] == .40
    assert all(type(semana) is int for semana in normalizada["fase_2"])


@pytest.mark.asyncio
@pytest.mark.parametrize("ruta,cuerpo", [
    ("/ejecutar", {"id_tiempo": 20260101}),
    ("/matriz", {"cosechable": {"1": 1.}}),
])
async def test_viewer_no_puede_escribir_ni_ejecutar(api_proyecciones, repositorio_http, ruta, cuerpo):
    aplicacion, usuario = api_proyecciones
    usuario.rol = "viewer"
    respuesta = await _peticion(aplicacion, "POST", ruta, cuerpo)
    _error_seguro(respuesta, 403)
    repositorio_http.extraer.assert_not_called()
    repositorio_http.guardar.assert_not_called()
    repositorio_http.guardar_matriz.assert_not_called()


@pytest.mark.asyncio
async def test_viewer_conserva_acceso_a_lectura_matriz(api_proyecciones, repositorio_http):
    aplicacion, usuario = api_proyecciones
    usuario.rol = "viewer"
    respuesta = await _peticion(aplicacion, "GET", "/matriz")
    assert respuesta.status_code == 200
    repositorio_http.leer_matriz.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("metodo,ruta,atributo,cuerpo", [
    ("POST", "/ejecutar", "extraer", {"id_tiempo": 20260101}),
    ("GET", "/matriz", "leer_matriz", None),
    ("POST", "/matriz", "guardar_matriz", {"cosechable": {"1": 1.}}),
])
async def test_http_preserva_503_de_repositorio(api_proyecciones, repositorio_http, metodo, ruta, atributo, cuerpo):
    getattr(repositorio_http, atributo).side_effect = ErrorBaseDatos()
    respuesta = await _peticion(api_proyecciones[0], metodo, ruta, cuerpo)
    _error_seguro(respuesta, 503)


@pytest.mark.asyncio
async def test_guardado_incompleto_http_503_sin_sql_crudo(api_proyecciones, repositorio_http):
    repositorio_http.guardar.side_effect = None
    repositorio_http.guardar.return_value = {"insertados": 5, "saltados": 0, "errores": [SQL_PRIVADO]}
    respuesta = await _peticion(api_proyecciones[0], "POST", "/ejecutar", {"id_tiempo": 20260101})
    _error_seguro(respuesta, 503)


@pytest.mark.asyncio
async def test_matriz_no_guardada_http_503(api_proyecciones, repositorio_http):
    repositorio_http.guardar_matriz.return_value = False
    respuesta = await _peticion(api_proyecciones[0], "POST", "/matriz", {"cosechable": {"1": 1.}})
    _error_seguro(respuesta, 503)


@pytest.mark.asyncio
@pytest.mark.parametrize("metodo,ruta,atributo,cuerpo", [
    ("POST", "/ejecutar", "extraer", {"id_tiempo": 20260101}),
    ("GET", "/matriz", "leer_matriz", None),
    ("POST", "/matriz", "guardar_matriz", {"cosechable": {"1": 1.}}),
])
async def test_http_error_imprevisto_no_expone_sql(api_proyecciones, repositorio_http, metodo, ruta, atributo, cuerpo):
    getattr(repositorio_http, atributo).side_effect = RuntimeError(SQL_PRIVADO)
    respuesta = await _peticion(api_proyecciones[0], metodo, ruta, cuerpo)
    _error_seguro(respuesta, 500)


@pytest.mark.asyncio
async def test_error_de_dominio_del_servicio_se_traduce_a_422(api_proyecciones, repositorio_http, monkeypatch):
    ejecutar = AsyncMock(side_effect=ErrorValidacionProyeccion("Parámetros inválidos."))
    monkeypatch.setattr(servicio, "ejecutar_proyeccion", ejecutar)
    respuesta = await _peticion(api_proyecciones[0], "POST", "/ejecutar", {"id_tiempo": 20260101})
    _error_seguro(respuesta, 422)
    repositorio_http.extraer.assert_not_called()
    repositorio_http.guardar.assert_not_called()
