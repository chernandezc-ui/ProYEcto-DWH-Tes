"""
test_circuit_breaker.py
========================
Tests del módulo centralizado utils/circuit_breaker.py.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.circuit_breaker import (
    UmbralesCircuitBreaker,
    evaluar,
    lanzar_si_bloqueado,
)
from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError


def _procesador(total=100, rechazados=10, insertados=90):
    from silver.facts import _base_processor as bp

    with patch.object(bp, "obtener_parametros_pipeline", return_value={}), patch.object(bp, "obtener_reglas_validacion", return_value={}):
        processor = bp.BaseFactProcessor(None, 'Bronce.Test', 'Silver.Test')
    processor.resumen.update(
        leidos=total, insertados=insertados,
        rechazados_ids=[{'id': i} for i in range(rechazados)],
    )
    return processor


class TestEvaluacionUmbrales(unittest.TestCase):
    def test_muestra_pequena_no_dispara(self):
        # Con < 50 filas el breaker no aplica
        r = evaluar(total_leidos=20, rechazados=10, tabla='X')
        self.assertIsNone(r.nivel)
        self.assertEqual(r.porcentaje_rechazo, 50.0)

    def test_nivel_critico(self):
        # 5% sobre 100 filas dispara CRITICO (default 5.0)
        r = evaluar(total_leidos=100, rechazados=6, tabla='X')
        self.assertEqual(r.nivel, 'CRITICO')

    def test_nivel_error(self):
        # 3% sobre 100 dispara ERROR (default 2.0) pero NO crítico (5.0)
        r = evaluar(total_leidos=100, rechazados=3, tabla='X')
        self.assertEqual(r.nivel, 'ERROR')

    def test_nivel_warning(self):
        # 1.5% sobre 100 dispara WARNING (default 1.0) pero NO error
        r = evaluar(total_leidos=200, rechazados=3, tabla='X')
        self.assertEqual(r.nivel, 'WARNING')

    def test_sin_rechazos(self):
        r = evaluar(total_leidos=1000, rechazados=0, tabla='X')
        self.assertIsNone(r.nivel)
        self.assertEqual(r.porcentaje_rechazo, 0.0)

    def test_umbrales_custom(self):
        # FactCensoPlantas usa thresholds más permisivos
        umbrales = UmbralesCircuitBreaker(warning=50.0, error=95.0, critico=99.0)
        r = evaluar(total_leidos=1000, rechazados=600, umbrales=umbrales, tabla='X')
        self.assertEqual(r.nivel, 'WARNING')  # 60% > 50% warning
        r = evaluar(total_leidos=1000, rechazados=960, umbrales=umbrales, tabla='X')
        self.assertEqual(r.nivel, 'ERROR')

    def test_umbrales_invalidos_lanzan(self):
        # warning > error -> incoherente
        with self.assertRaises(ValueError):
            UmbralesCircuitBreaker(warning=10.0, error=5.0, critico=20.0)


class TestLanzarSiBloqueado(unittest.TestCase):
    def test_lanza_critico(self):
        r = evaluar(total_leidos=100, rechazados=10, tabla='X')
        with self.assertRaises(ErrorCircuitBreakerCritico):
            lanzar_si_bloqueado(r)

    def test_lanza_error(self):
        r = evaluar(total_leidos=100, rechazados=3, tabla='X')
        with self.assertRaises(ErrorCircuitBreakerError):
            lanzar_si_bloqueado(r)

    def test_no_lanza_warning(self):
        r = evaluar(total_leidos=200, rechazados=3, tabla='X')
        self.assertEqual(r.nivel, 'WARNING')
        lanzar_si_bloqueado(r)  # no debe lanzar

    def test_no_lanza_sin_nivel(self):
        r = evaluar(total_leidos=1000, rechazados=0, tabla='X')
        lanzar_si_bloqueado(r)



class TestBreakerNoDestructivo(unittest.TestCase):
    """
    Bug 2 (fix 2026-05-26): el breaker no debe romper la transaccion al
    evaluar. La excepcion la lanza el orquestador DESPUES de commit.

    Estos tests verifican el contrato funcional:
      1. evaluar() NUNCA lanza, devuelve resultado.
      2. lanzar_si_bloqueado() es opt-in (se llama explicitamente fuera de tx).
      3. El payload de finalizar_proceso lleva 'breaker_*' keys para que
         el pipeline pueda lanzar fuera de la transaccion.
    """

    def test_evaluar_no_lanza_nunca(self):
        # Aun con 100% rechazo, evaluar() solo devuelve resultado.
        r = evaluar(total_leidos=1000, rechazados=1000, tabla='X')
        self.assertEqual(r.nivel, 'CRITICO')
        # No debe haber lanzado nada al llegar aqui.

    def test_payload_keys_contrato_pipeline(self):
        payload = _procesador().finalizar_proceso(MagicMock())
        self.assertEqual(payload['breaker_nivel'], 'CRITICO')
        self.assertEqual(payload['breaker_porcentaje'], 10.0)
        self.assertIsNotNone(payload['breaker_mensaje'])


class TestBasePayloadIncluyeBreaker(unittest.TestCase):
    """Smoke test: el modulo _base_processor expone breaker_* en su contrato
    Y NO lanza excepciones del breaker dentro de la transaccion (Bug 2)."""

    def test_finalizar_proceso_devuelve_breaker_keys(self):
        payload = _procesador().finalizar_proceso(MagicMock())
        for key in ('breaker_nivel', 'breaker_mensaje', 'breaker_total_leidos', 'breaker_rechazados'):
            self.assertIn(key, payload)

    def test_finalizar_proceso_no_levanta_error_breaker_inline(self):
        processor = _procesador()
        processor.ids_procesados = [1]
        processor.ids_rechazados = [2]
        processor.resumen['cuarentena'] = [{'id': 2}]
        context = MagicMock()
        payload = processor.finalizar_proceso(context)
        self.assertEqual(payload['breaker_nivel'], 'CRITICO')
        self.assertEqual(context.marcar_estado_carga.call_count, 2)
        context.enviar_cuarentena.assert_called_once_with('Bronce.Test', [{'id': 2}])
        context.commit.assert_not_called()
        context.rollback.assert_not_called()

    def test_finalizar_proceso_excluye_duplicados_internos(self):
        processor = _procesador(rechazados=0)
        processor.resumen['rechazados_ids'] = [
            {'id': 1}, {'id': 1},
            {'id': 2, 'es_duplicado_interno': True},
            {'id': 3, 'es_duplicado_externo': True},
        ]
        payload = processor.finalizar_proceso(MagicMock())
        self.assertEqual(payload['breaker_rechazados'], 1)
        self.assertEqual(payload['breaker_porcentaje'], 1.0)
        self.assertEqual(payload['breaker_nivel'], 'WARNING')


@pytest.mark.parametrize('total,rejected,expected', [
    (0, 0, None), (49, 49, None), (50, 0, None),
    (100, 1, 'WARNING'), (100, 2, 'ERROR'), (100, 5, 'CRITICO'),
])
def test_procesador_real_respeta_limites_y_muestra(total, rejected, expected):
    payload = _procesador(total, rejected).finalizar_proceso(MagicMock())
    assert payload['breaker_nivel'] == expected
    assert payload['breaker_total_leidos'] == total
    assert payload['breaker_rechazados'] == rejected
    assert payload['Bloqueo_Integridad'] == (expected == 'WARNING')
    if expected is None:
        assert payload['breaker_mensaje'] is None


@pytest.mark.parametrize('module,class_name,expected', [
    ('fact_censo_plantas', 'ProcesadorCensoPlantas', 'WARNING'),
    ('fact_evaluacion_pesos', 'ProcesadorEvaluacionPesos', 'WARNING'),
    ('fact_telemetria_clima', 'ProcesadorTelemetriaClima', 'WARNING'),
    ('fact_areas_plantas', 'ProcesadorAreasPlantas', 'WARNING'),
    ('fact_induccion_floral', 'ProcesadorInduccionFloral', 'CRITICO'),
    ('fact_evaluacion_vegetativa', 'ProcesadorEvaluacionVegetativa', 'CRITICO'),
])
def test_umbrales_de_subclases_reales_se_conservan(module, class_name, expected):
    import importlib
    from silver.facts import _base_processor as bp

    cls = getattr(importlib.import_module(f'silver.facts.{module}'), class_name)
    with patch.object(bp, 'obtener_parametros_pipeline', return_value={}), patch.object(bp, 'obtener_reglas_validacion', return_value={}):
        processor = cls(None, columna_id='ID_Test') if module == 'fact_induccion_floral' else cls(None)
    processor.resumen.update(leidos=100, insertados=0, rechazados_ids=[{'id': i} for i in range(100)])
    payload = processor.finalizar_proceso(MagicMock())
    assert payload['breaker_nivel'] == expected


@pytest.mark.parametrize('total,inserted,rejected,expected', [(49, 0, 0, False), (50, 0, 0, True), (100, 1, 0, False), (100, 0, 1, False)])
def test_deteccion_de_perdida_silenciosa_no_cambia(total, inserted, rejected, expected):
    payload = _procesador(total, rejected, inserted).finalizar_proceso(MagicMock())
    assert payload['posible_perdida_silenciosa'] is expected


def test_produccion_delega_en_el_evaluador_canonico():
    from utils import circuit_breaker

    processor = _procesador()
    with patch.object(circuit_breaker, 'evaluar', wraps=circuit_breaker.evaluar) as evaluation:
        payload = processor.finalizar_proceso(MagicMock())
    evaluation.assert_called_once_with(
        100, 10, umbrales=UmbralesCircuitBreaker(), tabla='Silver.Test',
    )
    assert payload['breaker_nivel'] == 'CRITICO'


@pytest.mark.parametrize('rejected,exception', [(2, ErrorCircuitBreakerError), (5, ErrorCircuitBreakerCritico)])
@pytest.mark.parametrize('rebuild', [False, True])
def test_evaluacion_real_conserva_commit_incremental_y_rollback_reproceso(tmp_path, monkeypatch, rejected, exception, rebuild):
    from sqlalchemy import create_engine, text
    import pipeline
    from utils.metricas import normalizar_resultado_fact
    from utils.reproceso_atomico import reconstruir_fact_atomica

    engine = create_engine('sqlite:///' + str(tmp_path / 'breaker.db'))
    try:
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE fact (value INTEGER)'))
            connection.execute(text('INSERT INTO fact VALUES (7)'))

        def load(scoped):
            with scoped.begin() as connection:
                connection.execute(text('INSERT INTO fact VALUES (9)'))
                payload = _procesador(100, rejected, 1).finalizar_proceso(MagicMock())
            return normalizar_resultado_fact(payload)

        def prepare(scoped):
            with scoped.begin() as connection:
                count = connection.execute(text('DELETE FROM fact')).rowcount
            return {'filas_destino_eliminadas': count}

        if rebuild:
            with pytest.raises(exception):
                reconstruir_fact_atomica(engine, prepare, load)
        else:
            monkeypatch.setattr(pipeline, 'registrar_inicio', MagicMock(return_value=1))
            monkeypatch.setattr(pipeline, 'registrar_fin', MagicMock())
            monkeypatch.setattr(pipeline, '_imprimir', MagicMock())
            summary = {}
            if exception is ErrorCircuitBreakerCritico:
                with pytest.raises(exception):
                    pipeline._ejecutar_fact('Test', 'Silver.Test', load, engine, summary)
            else:
                assert pipeline._ejecutar_fact('Test', 'Silver.Test', load, engine, summary)
            assert 'Test CIRCUIT_BREAKER' in summary

        with engine.connect() as connection:
            assert connection.execute(text('SELECT value FROM fact ORDER BY value')).scalars().all() == ([7] if rebuild else [7, 9])
    finally:
        engine.dispose()


if __name__ == '__main__':
    unittest.main()
