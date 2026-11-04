"""
test_circuit_breaker.py
========================
Tests del módulo centralizado utils/circuit_breaker.py.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.circuit_breaker import (
    UmbralesCircuitBreaker,
    evaluar,
    lanzar_si_bloqueado,
)
from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError


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
        # Simula lo que finalizar_proceso debe poner en su return dict
        # para que pipeline._ejecutar_fact pueda decidir lanzar.
        r = evaluar(total_leidos=100, rechazados=10, tabla='X')
        payload = {
            'insertados': 90,
            'breaker_nivel': r.nivel,
            'breaker_mensaje': r.mensaje,
            'breaker_resultado': r,
            'breaker_porcentaje': r.porcentaje_rechazo,
        }
        # El pipeline debe poder detectar el nivel y disponer del objeto.
        self.assertEqual(payload['breaker_nivel'], 'CRITICO')
        self.assertIsNotNone(payload['breaker_resultado'])
        # Y al pasarle el objeto a lanzar_si_bloqueado, ahora si lanza.
        with self.assertRaises(ErrorCircuitBreakerCritico):
            lanzar_si_bloqueado(payload['breaker_resultado'])


class TestBasePayloadIncluyeBreaker(unittest.TestCase):
    """Smoke test: el modulo _base_processor expone breaker_* en su contrato
    Y NO lanza excepciones del breaker dentro de la transaccion (Bug 2)."""

    def test_finalizar_proceso_devuelve_breaker_keys(self):
        # Verificacion ligera: el codigo fuente declara las keys.
        import inspect
        from silver.facts import _base_processor as bp
        src = inspect.getsource(bp.BaseFactProcessor.finalizar_proceso)
        for key in (
            "'breaker_nivel'",
            "'breaker_mensaje'",
        ):
            self.assertIn(key, src, f'finalizar_proceso debe exponer {key} (Bug 2 fix).')

    def test_finalizar_proceso_no_levanta_error_breaker_inline(self):
        # NO debe haber lineas activas con `raise ErrorCircuitBreaker...`
        # dentro de finalizar_proceso (Bug 2: la transaccion no debe romperse).
        import inspect
        from silver.facts import _base_processor as bp
        src = inspect.getsource(bp.BaseFactProcessor.finalizar_proceso)
        lineas_activas_raise = [
            ln for ln in src.splitlines()
            if 'raise ErrorCircuitBreaker' in ln and not ln.lstrip().startswith('#')
        ]
        self.assertEqual(
            lineas_activas_raise, [],
            f'finalizar_proceso NO debe levantar ErrorCircuitBreaker* dentro de '
            f'la transaccion (Bug 2). Lineas activas: {lineas_activas_raise}',
        )

    def test_finalizar_proceso_excluye_duplicados_internos(self):
        # Bug 3 fix: duplicados intra-batch (DUPLICADO_INTERNO) no deben
        # contar como rechazos DQ en el circuit breaker.
        import inspect
        from silver.facts import _base_processor as bp
        src = inspect.getsource(bp.BaseFactProcessor.finalizar_proceso)
        self.assertIn(
            'es_duplicado_interno', src,
            'finalizar_proceso debe excluir duplicados internos del circuit breaker (Bug 3 fix).',
        )


if __name__ == '__main__':
    unittest.main()
