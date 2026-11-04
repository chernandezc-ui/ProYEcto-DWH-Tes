"""Resultados históricos de Six-Week con datos sintéticos, sin SQL Server."""

from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest

from servicios import servicio_proyecciones as servicio


@pytest.fixture
def muestra_estados():
    conteo = pd.DataFrame([
        {
            "id_geografia": 101, "id_variedad": 5, "id_fundo": 1,
            "fundo": "Fundo A", "modulo": 1, "turno": 2, "valvula": 3,
            "variedad": "V", "condicion": "Orgánico", "certificacion": "X",
            "puntos": 1, "id_estado": estado, "total_organos": organos,
        }
        for estado, organos in [(9, 10), (6, 20), (5, 30), (4, 40), (3, 50)]
    ])
    plantas = pd.DataFrame([
        {"id_geografia": 101, "plantas_sampleadas": 100, "pct_productivas_s1": .8}
    ])
    pesos = pd.DataFrame(columns=[
        "id_fundo", "modulo", "variedad", "semana_iso", "peso_baya_kg",
    ])
    return conteo, plantas, pesos


@pytest.mark.asyncio
async def test_caracterizacion_seis_semanas_margenes_y_redondeo(muestra_estados, monkeypatch):
    lectura = Mock(return_value=muestra_estados)
    guardado = Mock(side_effect=lambda detalle, *_: {
        "insertados": len(detalle), "saltados": 0, "errores": [],
    })
    monkeypatch.setattr(servicio.repo, "extraer_datos_granulares", lectura)
    monkeypatch.setattr(servicio.repo, "guardar_proyeccion", guardado)

    resultado = await servicio.ejecutar_proyeccion(
        20260101, margen_pesimista=.85, margen_optimista=1.25,
        modulo=1, variedad="V", condicion="Orgánico", fundo="Fundo A",
    )

    detalle = resultado["df_detalle"]
    assert detalle["kg_base"].tolist() == [.30, .19, .23, .33, .28, .13]
    assert detalle["kg_pesimista"].tolist() == [.25, .16, .20, .28, .24, .11]
    assert detalle["kg_optimista"].tolist() == [.37, .24, .29, .41, .36, .16]
    assert detalle["id_tiempo_proy"].tolist() == [
        20260108, 20260115, 20260122, 20260129, 20260205, 20260212,
    ]
    assert detalle["fecha_semana"].tolist() == [
        date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 22),
        date(2026, 1, 29), date(2026, 2, 5), date(2026, 2, 12),
    ]
    assert detalle["semana_label"].tolist() == [
        "W1 (08/01)", "W2 (15/01)", "W3 (22/01)",
        "W4 (29/01)", "W5 (05/02)", "W6 (12/02)",
    ]
    assert set(detalle["id_geografia"]) == {101}
    assert set(detalle["id_variedad"]) == {5}
    assert set(detalle["condicion"]) == {"Orgánico"}
    assert set(detalle["certificacion"]) == {"X"}
    assert resultado["kpis"] == {
        "total_base": pytest.approx(1.46), "total_opt": pytest.approx(1.83),
        "total_pes": pytest.approx(1.24), "variedad_top": "V", "total_plantas": 100,
        "kg_por_planta": pytest.approx(.0146), "unidades_cubiertas": 1,
        "unidades_totales": 1,
    }
    pd.testing.assert_frame_equal(
        resultado["df_semanal"][["kg_base", "kg_pesimista", "kg_optimista"]],
        detalle[["kg_base", "kg_pesimista", "kg_optimista"]],
    )
    lectura.assert_called_once_with(20260101, 1, "V", "Orgánico", "Fundo A")
    guardado.assert_called_once()
    pd.testing.assert_frame_equal(guardado.call_args.args[0], detalle)
    assert guardado.call_args.args[1:] == (20260101, .85, 1.25)


@pytest.mark.parametrize("filas,esperados", [
    (
        [(1, 1, "V", 2, .002), (1, 1, "V", 2, .004),
         (1, 2, "V", 3, .004), (1, 1, "V", 1, .001),
         (2, 1, "V", 4, .9)],
        [.003, .004, .001, .001, .001, .001],
    ),
    (
        [(1, 2, "V", 2, .002), (1, 2, "V", 10, .004),
         (2, 1, "V", 4, .9)],
        [.002, .003, .003, .003, .003, .003],
    ),
    ([(2, 1, "V", 2, .9)], [.00289] * 6),
    ([(1, 1, "V", 2, 0.)], [.00289] * 6),
])
def test_caracterizacion_prioridad_y_fallbacks_del_peso(filas, esperados):
    pesos = pd.DataFrame(filas, columns=[
        "id_fundo", "modulo", "variedad", "semana_iso", "peso_baya_kg",
    ])
    resultado = servicio.lookup_peso_baya(1, "V", pesos, 1, 2026, 1)
    assert list(resultado) == [1, 2, 3, 4, 5, 6]
    assert list(resultado.values()) == pytest.approx(esperados)


def test_caracterizacion_ajuste_productivas_y_limites():
    assert servicio.calcular_pct_productivas(.8) == pytest.approx([.8, .82, .82, .79, .8, .81])
    assert servicio.calcular_pct_productivas(1.) == pytest.approx([1., 1., 1., .97, .98, .99])
    assert servicio.calcular_pct_productivas(float("nan")) == pytest.approx([0., .02, .02, 0., .01, .02])


@pytest.mark.asyncio
async def test_caracterizacion_vacio_no_intenta_guardar(monkeypatch):
    lectura = Mock(return_value=(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()))
    guardado = Mock()
    monkeypatch.setattr(servicio.repo, "extraer_datos_granulares", lectura)
    monkeypatch.setattr(servicio.repo, "guardar_proyeccion", guardado)
    resultado = await servicio.ejecutar_proyeccion(20260101)
    assert set(resultado) == {"df_semanal", "df_detalle", "kpis"}
    assert resultado["df_semanal"].empty
    assert resultado["df_detalle"].empty
    assert resultado["kpis"] == {}
    guardado.assert_not_called()
