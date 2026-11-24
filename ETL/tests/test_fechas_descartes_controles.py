"""
test_fechas_descartes_controles.py
==================================
Regresiones de:
  - Ciclos Fenologicos: fecha inventada (2015), recorte a 2026-06-30 y filas
    marcadas PROCESADO sin insertarse.
  - resolver_dimensiones_batch: filas con fecha/variedad vacia que se perdian
    en silencio.
  - pipeline: auditoria sobrescrita por el breaker, falsa alarma de perdida
    silenciosa y breaker CRITICO dentro del pool paralelo.
Sin base de datos: todo se prueba con stubs.
"""

import os
import sys
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from silver.facts import _base_processor as bp
from silver.facts.fact_ciclos_fenologicos import ProcesadorCiclosFenologicos


# ── helpers ────────────────────────────────────────────────────────────────

def _proc_base():
    with patch.object(bp, 'obtener_parametros_pipeline', return_value={}), \
         patch.object(bp, 'obtener_reglas_validacion', return_value={}):
        return bp.BaseFactProcessor(None, 'Bronce.Test', 'Silver.Test', columna_id='ID')


def _proc_ciclos():
    with patch.object(bp, 'obtener_parametros_pipeline', return_value={}), \
         patch.object(bp, 'obtener_reglas_validacion', return_value={}):
        proc = ProcesadorCiclosFenologicos(MagicMock())

    def resolver_stub(df, **kwargs):
        res = df.copy()
        col = kwargs['col_fecha']
        res['Fecha_Evento_dt'] = pd.to_datetime(res[col])
        res['ID_Tiempo'] = res['Fecha_Evento_dt'].dt.strftime('%Y%m%d').astype(int)
        res['ID_Variedad'] = 22
        res['ID_Geografia'] = 5
        res['_id_modulo_catalogo'] = 14
        return res

    proc.resolver_dimensiones_batch = resolver_stub
    return proc


def _fila_ciclo(id_o, fecha='2026-03-16', etapa='Flor', valores=''):
    return {
        'ID_Ciclo_Fenologico': id_o, 'Fecha_Raw': fecha, 'Modulo_Raw': '5',
        'Turno_Raw': '1', 'Valvula_Raw': '2', 'Fundo_Raw': 'F',
        'Variedad_Raw': 'ROCIO', 'Variedad_Canonica': 'ROCIO',
        'Evaluador_Raw': None, 'Color_Raw': 'Rojo', 'Organo_Raw': 'Flor',
        'Etapa_Fenologica_Raw': etapa, 'Valores_Raw': valores,
        'Fecha_Sistema': pd.Timestamp('2026-05-20'),
    }


@pytest.fixture
def lookups():
    """obtener_id_estado_fenologico: 'Flor' -> 3, cualquier otra cosa -> None."""
    with patch('mdm.lookup.obtener_id_estado_fenologico',
               side_effect=lambda cat, engine: 3 if str(cat).strip().lower() == 'flor' else None), \
         patch('mdm.lookup.obtener_id_cinta', return_value=1):
        yield


# ── Ciclos Fenologicos ─────────────────────────────────────────────────────

class TestCiclosFechas:
    def test_fecha_posterior_a_junio_2026_no_se_recorta(self, lookups):
        proc = _proc_ciclos()
        ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        payload = proc._construir_payload(pd.DataFrame([_fila_ciclo(1, fecha='2026-10-15'),
                                                        _fila_ciclo(2, fecha=ayer)]))
        fechas = sorted(pd.Timestamp(r['Fecha_Evento']).strftime('%Y-%m-%d') for r in payload)
        assert '2026-10-15' in fechas          # antes quedaba como 2026-06-30
        assert '2026-06-30' not in fechas
        assert {r['ID_Tiempo'] for r in payload} == {20261015, int(ayer.replace('-', ''))}

    def test_fila_sin_fecha_se_rechaza_en_vez_de_inventar_2015(self, lookups):
        proc = _proc_ciclos()
        payload = proc._construir_payload(pd.DataFrame([_fila_ciclo(7, fecha=None)]))
        assert payload == []
        assert proc.ids_rechazados == [7]
        assert proc.resumen['cuarentena'][0]['motivo'].startswith('Sin fecha derivable')

    def test_fecha_se_deriva_de_ano_y_semana_si_falta(self, lookups):
        proc = _proc_ciclos()
        fila = _fila_ciclo(8, fecha=None, valores='Ano_Raw=2026 | Semana_Raw=10')
        payload = proc._construir_payload(pd.DataFrame([fila]))
        assert len(payload) == 1
        assert pd.Timestamp(payload[0]['Fecha_Evento']).year == 2026

    def test_fecha_futura_se_rechaza(self, lookups):
        proc = _proc_ciclos()
        futura = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        payload = proc._construir_payload(pd.DataFrame([_fila_ciclo(9, fecha=futura)]))
        assert payload == []
        assert 9 in proc.ids_rechazados
        assert proc.resumen['cuarentena'][0]['motivo'] == 'Fecha futura (posterior a hoy)'


class TestCiclosEstadoNoReconocido:
    def test_estado_desconocido_se_rechaza_y_no_se_marca_procesado(self, lookups):
        proc = _proc_ciclos()
        df = pd.DataFrame([_fila_ciclo(1, etapa='Flor'), _fila_ciclo(2, etapa='Xyz')])
        payload = proc._construir_payload(df)
        assert [r['id_origen_rastreo'] for r in payload] == [1]
        assert proc.ids_procesados == [1]          # el 2 ya no queda PROCESADO
        assert proc.ids_rechazados == [2]
        assert proc.resumen['cuarentena'][0]['motivo'] == 'Estado fenologico no reconocido'


# ── resolver_dimensiones_batch: nulos ──────────────────────────────────────

class TestResolverNulos:
    def _df(self, fechas, variedades):
        return pd.DataFrame({
            'ID': range(1, len(fechas) + 1),
            'Fecha_Raw': fechas, 'Modulo_Raw': ['5'] * len(fechas),
            'Variedad_Raw': variedades, 'Variedad_Canonica': variedades,
        })

    def test_fecha_vacia_se_rechaza(self):
        proc = _proc_base()
        out = proc.resolver_dimensiones_batch(
            self._df([None, None], ['ROCIO', 'ROCIO']),
            col_fecha='Fecha_Raw', col_modulo='Modulo_Raw',
            col_variedad='Variedad_Raw', dominio_fecha='clima',
        )
        assert out.empty
        assert sorted(proc.ids_rechazados) == [1, 2]
        assert proc.resumen['cuarentena'][0]['motivo'] == 'Fecha vacia'

    def test_variedad_vacia_se_rechaza_sin_duplicar_cuarentena(self):
        proc = _proc_base()
        # La fila 2 ya tiene cuarentena del homologador (variedad sin canonica).
        proc.resumen['cuarentena'].append(
            {'columna': 'Variedad_Raw', 'valor': 'raro', 'motivo': 'homologador',
             'id_registro_origen': 2})
        df = self._df(['2026-03-16'] * 3, ['ROCIO', None, None])
        with patch('mdm.lookup.obtener_id_variedad', return_value=22), \
             patch.object(proc, '_resolver_geografia_base',
                          return_value={'id_geografia': 9, 'id_modulo_catalogo': 4}):
            out = proc.resolver_dimensiones_batch(
                df, col_fecha='Fecha_Raw', col_modulo='Modulo_Raw',
                col_variedad='Variedad_Raw', dominio_fecha='clima',
            )
        assert list(out['ID']) == [1]
        assert sorted(proc.ids_rechazados) == [2, 3]
        # La fila 2 no genera una segunda entrada; la 3 si.
        ids_cuarentena = [c['id_registro_origen'] for c in proc.resumen['cuarentena']]
        assert ids_cuarentena.count(2) == 1
        assert ids_cuarentena.count(3) == 1


# ── Falsa alarma de perdida silenciosa ─────────────────────────────────────

class TestPerdidaSilenciosa:
    def _payload(self, insertados, actualizados):
        proc = _proc_base()
        proc.resumen.update(leidos=100, insertados=insertados,
                            actualizados_por_tiebreaker=actualizados)
        return proc.finalizar_proceso(MagicMock())

    def test_solo_actualizaciones_no_es_perdida(self):
        payload = self._payload(insertados=0, actualizados=40)
        assert payload['posible_perdida_silenciosa'] is False
        assert payload['Filas_Actualizadas'] == 40

    def test_sin_nada_sigue_siendo_alerta(self):
        assert self._payload(0, 0)['posible_perdida_silenciosa'] is True


# ── pipeline: auditoria y breaker en paralelo ──────────────────────────────

@pytest.fixture
def pipeline_mod():
    import pipeline
    return pipeline


def _resultado(nivel):
    return {'insertados': 5, 'rechazados': 6, 'leidos': 100, 'cuarentena': [],
            'breaker_nivel': nivel, 'breaker_mensaje': f'{nivel} simulado',
            'tasa_rechazo_pct': 6.0, 'motivos_principales': []}


class TestAuditoriaBreaker:
    @pytest.mark.parametrize('nivel,estado', [('ERROR', 'CB_ERROR'), ('CRITICO', 'CB_CRITICO')])
    def test_el_estado_del_breaker_no_se_sobrescribe(self, pipeline_mod, nivel, estado):
        from utils.errores import ErrorCircuitBreakerCritico
        fin = MagicMock()
        with patch.object(pipeline_mod, 'registrar_inicio', return_value=1), \
             patch.object(pipeline_mod, 'registrar_fin', fin):
            try:
                pipeline_mod._ejecutar_fact('F', 'Silver.F', lambda e: _resultado(nivel), None, {})
            except ErrorCircuitBreakerCritico:
                pass
        assert fin.call_count == 1
        assert fin.call_args[0][1]['estado'] == estado
        assert fin.call_args[0][1]['filas'] == 5      # ya no se pisa con 0

    def test_error_normal_se_sigue_registrando(self, pipeline_mod):
        fin = MagicMock()
        with patch.object(pipeline_mod, 'registrar_inicio', return_value=1), \
             patch.object(pipeline_mod, 'registrar_fin', fin):
            err = pipeline_mod._ejecutar_fact('F', 'Silver.F', MagicMock(side_effect=RuntimeError('x')), None, {})
        assert err == 'F: x'
        assert fin.call_args[0][1]['estado'] == 'ERROR'


class TestPoolParalelo:
    def _facts(self, n):
        return {f'F{i}': {'tabla_destino': f'Silver.F{i}', 'funcion': None} for i in range(n)}

    def test_breaker_critico_cancela_pendientes_y_conserva_resultados(self, pipeline_mod):
        from utils.errores import ErrorCircuitBreakerCritico
        ejecutadas = []
        lock = threading.Lock()

        def fake_fact(nombre, tabla, funcion, engine, resumen):
            with lock:
                ejecutadas.append(nombre)
            resumen[f'{nombre} marca'] = 'x'
            if nombre == 'F0':
                raise ErrorCircuitBreakerCritico('critico simulado')
            time.sleep(0.05)
            return None

        resumen, errores, con_error = {}, [], []
        with patch.object(pipeline_mod, '_ejecutar_fact', fake_fact):
            critico = pipeline_mod._ejecutar_facts_en_paralelo(
                None, self._facts(8), resumen, errores, con_error, max_workers=1)

        assert isinstance(critico, ErrorCircuitBreakerCritico)
        assert len(ejecutadas) < 8                         # las pendientes se cancelaron
        assert 'F0 marca' in resumen                       # el resultado del hilo no se pierde
        assert 'F0: critico simulado' in errores
        assert 'F0' in con_error
        assert 'Facts no ejecutadas (breaker critico)' in resumen

    def test_sin_breaker_ejecuta_todas(self, pipeline_mod):
        ejecutadas = []

        def fake_fact(nombre, tabla, funcion, engine, resumen):
            ejecutadas.append(nombre)
            return None

        with patch.object(pipeline_mod, '_ejecutar_fact', fake_fact):
            critico = pipeline_mod._ejecutar_facts_en_paralelo(
                None, self._facts(6), {}, [], [], max_workers=3)
        assert critico is None
        assert sorted(ejecutadas) == [f'F{i}' for i in range(6)]

    def test_abortar_deja_resumen_y_relanza(self, pipeline_mod):
        from utils.errores import ErrorCircuitBreakerCritico
        resumen = {}
        with patch.object(pipeline_mod, '_resumen_final') as resumen_final, \
             pytest.raises(ErrorCircuitBreakerCritico):
            pipeline_mod._abortar_por_breaker_critico(
                datetime.now(), resumen, ['F0: critico'], ErrorCircuitBreakerCritico('c'))
        resumen_final.assert_called_once()
        assert resumen['Pipeline abortado'] == 'CIRCUIT_BREAKER_CRITICO'
        assert resumen['Errores pipeline'] == 1
