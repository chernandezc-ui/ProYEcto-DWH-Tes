"""
test_umbrales_configurables.py
==============================
Las reglas de negocio salen de Config.Parametros_Pipeline (config/reglas.py) y el
codigo no trae valores por defecto: si falta una regla requerida hay un error
claro, y un cambio en la base cambia el comportamiento sin tocar codigo.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import reglas
from silver.facts import _base_processor as bp
from utils.circuit_breaker import UmbralesCircuitBreaker, evaluar, resolver_umbrales

GLOBALES = {'BREAKER_WARNING_PCT': '1.0', 'BREAKER_ERROR_PCT': '2.0',
            'BREAKER_CRITICO_PCT': '5.0', 'BREAKER_MIN_MUESTRA': '50'}


def fuente(**extra):
    reglas.usar_fuente_en_memoria({**GLOBALES, **extra})


# ── lector de reglas ───────────────────────────────────────────────────────

class TestLector:
    def test_falta_un_parametro_requerido_da_error_claro(self):
        reglas.usar_fuente_en_memoria({})
        with pytest.raises(reglas.ErrorConfiguracion, match="LEVENSHTEIN_UMBRAL"):
            reglas.parametro_float('LEVENSHTEIN_UMBRAL')

    def test_valor_vacio_cuenta_como_faltante(self):
        reglas.usar_fuente_en_memoria({'X': '   '})
        with pytest.raises(reglas.ErrorConfiguracion):
            reglas.parametro('X')

    def test_numero_con_coma_y_espacios(self):
        reglas.usar_fuente_en_memoria({'X': ' 2,5 '})
        assert reglas.parametro_float('X') == 2.5

    def test_numero_invalido(self):
        reglas.usar_fuente_en_memoria({'X': 'abc'})
        with pytest.raises(reglas.ErrorConfiguracion, match='no es numerico'):
            reglas.parametro_int('X')

    def test_lista_json_conserva_el_elemento_vacio(self):
        reglas.usar_fuente_en_memoria({'T': ['', 'NONE']})
        assert reglas.lista('T') == ['', 'NONE']

    def test_cache_se_invalida_al_cambiar_la_fuente(self):
        reglas.usar_fuente_en_memoria({'L': ['a']})
        assert reglas.lista('L') == ['a']
        reglas.usar_fuente_en_memoria({'L': ['b']})
        assert reglas.lista('L') == ['b']

    def test_lista_json_y_separada_por_comas(self):
        reglas.usar_fuente_en_memoria({'A': ['x', 'y'], 'B': 'p, q ; r'})
        assert reglas.lista('A') == ['x', 'y']
        assert reglas.lista('B') == ['p', 'q', 'r']
        assert reglas.conjunto('A') == frozenset({'x', 'y'})

    def test_mapeo_json(self):
        reglas.usar_fuente_en_memoria({'M': {'BUENAS': 1, 'MALAS': 3}})
        assert reglas.mapeo('M') == {'BUENAS': '1', 'MALAS': '3'}

    def test_mapeo_invalido(self):
        reglas.usar_fuente_en_memoria({'M': 'no es json', 'V': '{}'})
        with pytest.raises(reglas.ErrorConfiguracion, match='JSON'):
            reglas.mapeo('M')
        with pytest.raises(reglas.ErrorConfiguracion, match='no vacio'):
            reglas.mapeo('V')


# ── circuit breaker ────────────────────────────────────────────────────────

class TestResolverUmbrales:
    def test_globales(self):
        fuente()
        assert resolver_umbrales() == UmbralesCircuitBreaker(1.0, 2.0, 5.0, 50)

    def test_cambia_con_la_base_sin_tocar_codigo(self):
        fuente(BREAKER_WARNING_PCT='3', BREAKER_ERROR_PCT='6.5',
               BREAKER_CRITICO_PCT='10', BREAKER_MIN_MUESTRA='200')
        u = resolver_umbrales('Fact_Peladas')
        assert (u.warning, u.error, u.critico, u.min_muestra) == (3.0, 6.5, 10.0, 200)

    def test_override_por_fact_gana(self):
        fuente(**{'BREAKER_ERROR_PCT.Fact_Telemetria_Clima': '101',
                  'BREAKER_CRITICO_PCT.Fact_Telemetria_Clima': '101'})
        assert resolver_umbrales('Fact_Telemetria_Clima').critico == 101.0
        assert resolver_umbrales('Fact_Peladas').critico == 5.0      # otra fact: global

    def test_falta_un_global_requerido(self):
        reglas.usar_fuente_en_memoria({k: v for k, v in GLOBALES.items() if k != 'BREAKER_ERROR_PCT'})
        with pytest.raises(reglas.ErrorConfiguracion, match='BREAKER_ERROR_PCT'):
            resolver_umbrales('Fact_Peladas')

    def test_combinacion_incoherente(self):
        fuente(BREAKER_WARNING_PCT='9')
        with pytest.raises(reglas.ErrorConfiguracion, match='incoherentes'):
            resolver_umbrales('Fact_Peladas')


def _procesador(total=100, rechazados=3, insertados=97, clase=None):
    with patch.object(bp, 'obtener_parametros_pipeline', return_value={}), \
         patch.object(bp, 'obtener_reglas_validacion', return_value={}):
        proc = clase(None) if clase else bp.BaseFactProcessor(None, 'Bronce.Test', 'Silver.Fact_Test')
    proc.resumen.update(leidos=total, insertados=insertados,
                        rechazados_ids=[{'id': i} for i in range(rechazados)])
    return proc


class TestEnFinalizarProceso:
    def test_3_por_ciento_con_los_globales_es_error(self):
        fuente()
        assert _procesador().finalizar_proceso(MagicMock())['breaker_nivel'] == 'ERROR'

    def test_un_cambio_en_la_base_relaja_el_breaker(self):
        fuente(BREAKER_ERROR_PCT='4', BREAKER_CRITICO_PCT='8')
        assert _procesador().finalizar_proceso(MagicMock())['breaker_nivel'] == 'WARNING'

    def test_override_por_fact_usa_el_nombre_de_la_tabla_destino(self):
        fuente(**{'BREAKER_ERROR_PCT.Fact_Test': '2', 'BREAKER_CRITICO_PCT.Fact_Test': '2.5'})
        assert _procesador().finalizar_proceso(MagicMock())['breaker_nivel'] == 'CRITICO'

    def test_muestra_minima_afecta_breaker_y_alerta_silenciosa(self):
        fuente(BREAKER_MIN_MUESTRA='500')
        payload = _procesador(total=100, rechazados=0, insertados=0).finalizar_proceso(MagicMock())
        assert payload['breaker_nivel'] is None
        assert payload['posible_perdida_silenciosa'] is False

    def test_facts_con_breaker_desactivado_salen_de_la_base(self):
        from silver.facts.fact_telemetria_clima import ProcesadorTelemetriaClima
        reglas.usar_semilla_en_memoria()          # la semilla trae 101 para esta fact
        proc = _procesador(total=100, rechazados=100, insertados=0, clase=ProcesadorTelemetriaClima)
        assert proc.finalizar_proceso(MagicMock())['breaker_nivel'] == 'WARNING'
        # y si alguien lo cambia en la base, cambia el comportamiento
        fuente(**{'BREAKER_ERROR_PCT.Fact_Telemetria_Clima': '50',
                  'BREAKER_CRITICO_PCT.Fact_Telemetria_Clima': '90'})
        proc = _procesador(total=100, rechazados=100, insertados=0, clase=ProcesadorTelemetriaClima)
        assert proc.finalizar_proceso(MagicMock())['breaker_nivel'] == 'CRITICO'

    def test_sin_parametros_la_carga_falla_con_mensaje_claro(self):
        reglas.usar_fuente_en_memoria({})
        with pytest.raises(reglas.ErrorConfiguracion, match='BREAKER_'):
            _procesador().finalizar_proceso(MagicMock())


# ── otras reglas que antes estaban fijas ───────────────────────────────────

class TestOtrasReglas:
    def test_umbral_de_homologacion_sale_de_la_base(self):
        import pandas as pd
        from mdm.homologador import buscar_match_levenshtein
        catalogo = pd.DataFrame({'Clave_Valor_Canonico': ['SEKOYA POP'], 'Valor_Canonico': ['SEKOYA POP']})
        reglas.usar_fuente_en_memoria({'LEVENSHTEIN_UMBRAL': '0.85'})
        valor, score = buscar_match_levenshtein('sekoya pap', catalogo)
        assert valor == 'SEKOYA POP' and 0.85 <= score < 1
        reglas.usar_fuente_en_memoria({'LEVENSHTEIN_UMBRAL': '0.99'})
        assert buscar_match_levenshtein('sekoya pap', catalogo)[0] is None

    def test_rango_de_peso_de_baya_sale_de_la_base(self):
        from dq.validador import validar_peso_baya
        reglas.usar_fuente_en_memoria({'PESO_BAYA_MIN': '0.5', 'PESO_BAYA_MAX': '12'})
        assert validar_peso_baya('0.2')[0] is None
        reglas.usar_fuente_en_memoria({'PESO_BAYA_MIN': '0.03', 'PESO_BAYA_MAX': '12'})
        assert validar_peso_baya('0.2')[0] == 0.2

    def test_longitud_del_dni_sale_de_la_base(self):
        from utils.dni import procesar_dni
        reglas.usar_fuente_en_memoria({'DNI_LONGITUD': '8'})
        assert procesar_dni('123') == ('00000123', True)
        reglas.usar_fuente_en_memoria({'DNI_LONGITUD': '9'})
        assert procesar_dni('123') == ('000000123', True)

    def test_ventana_de_campana_y_dominios_salen_de_la_base(self):
        from utils.fechas import procesar_fecha
        reglas.usar_fuente_en_memoria({
            'CAMPANA_FECHA_INICIO': '2026-01-01', 'CAMPANA_FECHA_FIN': '2026-12-31',
            'DOMINIOS_SIN_RESTRICCION_CAMPANA': ['clima']})
        assert procesar_fecha('2025-05-01', dominio='cosecha_sap')[1] is False   # fuera de ventana
        assert procesar_fecha('2025-05-01', dominio='clima')[1] is True          # dominio exento
        reglas.usar_fuente_en_memoria({
            'CAMPANA_FECHA_INICIO': '2015-01-01', 'CAMPANA_FECHA_FIN': '2030-12-31',
            'DOMINIOS_SIN_RESTRICCION_CAMPANA': ['clima']})
        assert procesar_fecha('2025-05-01', dominio='cosecha_sap')[1] is True


# ── la semilla es coherente ────────────────────────────────────────────────

class TestSemilla:
    def test_todos_los_valores_caben_en_la_columna(self):
        for p in reglas.cargar_semilla()['parametros']:
            assert len(reglas.serializar_valor(p['valor'])) <= reglas.MAX_LONGITUD_VALOR, p['nombre']

    def test_umbrales_validos_para_todas_las_facts(self):
        from utils.ejecucion import CONFIG_FACTS
        reglas.usar_semilla_en_memoria()
        for nombre in CONFIG_FACTS:
            resolver_umbrales(nombre)      # no debe lanzar
        assert evaluar(100, 100, umbrales=resolver_umbrales('Fact_Censo_Plantas')).nivel == 'WARNING'

    def test_nombres_unicos(self):
        nombres = [p['nombre'] for p in reglas.cargar_semilla()['parametros']]
        assert len(nombres) == len(set(nombres))


# ── reglas migradas: mismo comportamiento con la semilla, y cambian con la base ──

class TestReglasMigradas:
    def test_conteo_estados_desde_columnas_configuradas(self):
        import pandas as pd
        from silver.facts.fact_conteo_fenologico import _extraer_estados_desde_fila
        fila = pd.Series({'BotonesFlorales_Raw': 5, 'Flores_Raw': 7, 'Bayas_Cremas_Raw': 2,
                          'YemasHinchadas_Raw': 9, 'Valores_Raw': None})
        assert _extraer_estados_desde_fila(fila) == [
            ('Boton Floral', 5), ('Flor', 7), ('Crema', 2), ('Yema Hinchada', 9)]
        # cambiar la prioridad de columnas en la base cambia el resultado sin tocar codigo
        reglas.usar_fuente_en_memoria({
            **{p['nombre']: p['valor'] for p in reglas.cargar_semilla()['parametros']},
            'ESTADOS_FENOLOGICOS_CONTEO': ['Flor'],
            'COLUMNAS_ESTADO_FENOLOGICO.Flor': ['OtraColumna_Raw']})
        assert _extraer_estados_desde_fila(pd.Series({'Flores_Raw': 7, 'OtraColumna_Raw': 3})) == [('Flor', 3)]

    def test_conteo_tipos_de_evaluacion_validos(self):
        from silver.facts.fact_conteo_fenologico import _es_evaluacion_compatible_con_conteo as ok
        assert ok('CONTEO DE FLORES') and ok('Ensayo de Conteo') and ok('PODA GENERAL') and ok('')
        assert not ok('Otra cosa')
        reglas.usar_fuente_en_memoria({'TIPO_EVALUACION_CONTEO_CONTIENE': ['otra'],
                                       'TIPO_EVALUACION_CONTEO_EXACTO': ['x']})
        assert ok('Otra cosa') and not ok('PODA GENERAL')

    def test_tercio(self):
        from silver.facts.fact_fisiologia import _normalizar_tercio
        assert _normalizar_tercio('b') == 'BAJO' and _normalizar_tercio('High') == 'ALTO'
        assert _normalizar_tercio('xyz') == 'XYZ' and _normalizar_tercio(None) is None

    def test_tareo_filas_no_operativas_incluye_la_fecha_vacia(self):
        from silver.facts.fact_tareo import _es_fila_no_operativa as no_op
        assert no_op({'Fecha_Raw': '', 'IDPersonalGeneral_Raw': 'x'})          # el vacio es un token
        assert no_op({'Fecha_Raw': 'personas', 'IDPersonalGeneral_Raw': 'x'})
        assert no_op({'Fecha_Raw': '2026-01-01', 'IDPersonalGeneral_Raw': 'total'})
        assert not no_op({'Fecha_Raw': '2026-01-01', 'IDPersonalGeneral_Raw': '123'})

    def test_geografia_placeholders_y_fundo_por_defecto(self):
        from mdm.lookup import _normalizar_componente, fundo_defecto
        assert _normalizar_componente('SIN_FUNDO') == 'NONE' and _normalizar_componente('M5') == '5'
        assert fundo_defecto() == 'ARANDANO ACP'

    def test_alias_de_estado_fenologico_y_cinta(self):
        from mdm import lookup
        mapa = {'inicio f1': 11, 'flor': 12, 'amarilla': 7}
        with patch.object(lookup, '_obtener_mapa_dim', return_value=mapa):
            assert lookup.obtener_id_estado_fenologico('FFase1', None) == 11
            assert lookup.obtener_id_estado_fenologico('Floración', None) == 12
            assert lookup.obtener_id_cinta('Amarillo', None) == 7

    def test_semilla_tiene_las_reglas_migradas(self):
        nombres = {p['nombre'] for p in reglas.cargar_semilla()['parametros']}
        for n in ('FUNDO_DEFECTO', 'MAPEO_ESTADO_PLANTA', 'ALIAS_CINTA', 'PLACEHOLDERS_GEOGRAFICOS',
                  'TOKENS_FECHA_NO_OPERATIVA', 'ESTADOS_FENOLOGICOS_CONTEO', 'FECHA_SIN_DATO'):
            assert n in nombres
        assert reglas.mapeo('MAPEO_ESTADO_PLANTA')['TOTAL_PLANTAS'] == '-1'
