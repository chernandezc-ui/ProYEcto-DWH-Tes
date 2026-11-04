"""
fact_induccion_floral.py
========================
Carga Silver.Fact_Induccion_Floral desde Bronce.Induccion_Floral.
"""
from __future__ import annotations
import re
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    a_entero_nulo as _a_entero_nulo,
    a_entero_no_negativo as _a_entero_no_negativo,
    finalizar_resumen_fact as _finalizar_resumen_fact,
    texto_nulo as _texto_nulo,
    parsear_valores_raw as _parsear_valores_raw,
    derivar_fecha_iso_semana as _derivar_fecha_iso_semana,
    validar_layout_migrado as _validar_layout_migrado_helper,
)


TABLA_ORIGEN = 'Bronce.Induccion_Floral'
TABLA_DESTINO = 'Silver.Fact_Induccion_Floral'

# Conservado para referencia del schema — ya no se usa directamente (bulk insert via #Temp)
SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Induccion_Floral (
        ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal,
        Tipo_Evaluacion, Codigo_Consumidor,
        Cantidad_Plantas_Por_Cama, Cantidad_Plantas_Con_Induccion,
        Cantidad_Brotes_Con_Induccion, Cantidad_Brotes_Totales,
        Cantidad_Brotes_Con_Flor,
        Pct_Plantas_Con_Induccion, Pct_Brotes_Con_Induccion, Pct_Brotes_Con_Flor,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_tiempo, :id_variedad, :id_personal,
        :tipo_evaluacion, :codigo_consumidor,
        :plantas_por_cama, :plantas_con_induccion,
        :brotes_con_induccion, :brotes_totales,
        :brotes_con_flor,
        :pct_plantas_induccion, :pct_brotes_induccion, :pct_brotes_flor,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _pct(parte: int, total: int) -> float | None:
    if total <= 0:
        return None
    val = round((parte / total) * 100.0, 2)
    if val > 999.99:
        return 999.99
    return val


def _validar_layout_migrado(engine: Engine) -> str:
    return _validar_layout_migrado_helper(
        engine,
        tabla_origen=TABLA_ORIGEN,
        tabla_destino=TABLA_DESTINO,
        columna_id='ID_Induccion_Floral',
        columnas_bronce_requeridas={
            'ID_Induccion_Floral',
            'Fecha_Raw',
            'DNI_Raw',
            'Consumidor_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'PlantasPorCama_Raw',
            'PlantasConInduccion_Raw',
            'BrotesConInduccion_Raw',
            'BrotesTotales_Raw',
            'BrotesConFlor_Raw',
            'Estado_Carga',
        },
        columnas_silver_requeridas={
            'ID_Geografia',
            'ID_Tiempo',
            'ID_Variedad',
            'ID_Personal',
            'Codigo_Consumidor',
            'Cantidad_Plantas_Por_Cama',
            'Cantidad_Plantas_Con_Induccion',
            'Cantidad_Brotes_Con_Induccion',
            'Cantidad_Brotes_Totales',
            'Cantidad_Brotes_Con_Flor',
        },
        nombre_layout='Induccion_Floral',
    )


class ProcesadorInduccionFloral(BaseFactProcessor):
    def __init__(self, engine: Engine, columna_id: str):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id=columna_id)
        # El historico tiene ~3% de geografias no catalogadas (modulos antiguos/renombrados).
        # Subimos el umbral a 5% para evitar falsos positivos del circuit breaker.
        self.LIMITE_ERROR = 5.0
        # Grain: Geo + Tiempo + Variedad + Personal + Tipo_Evaluacion
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal', 'Tipo_Evaluacion']
        self._columna_id = columna_id

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        import re
        import numpy as np

        # Identificar columna ID original
        col_id_origen = self.columna_id
        if col_id_origen not in df.columns:
            col_id_origen = 'ID_Registro_Origen'
            
        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)
        
        # 2. Derivar fechas en lote
        def _derivar_fecha_fila(r_fecha, v_r):
            if r_fecha and str(r_fecha).strip() not in ('', 'None', 'nan'):
                return str(r_fecha)
            
            ano = v_r.get('Ano_Raw') or v_r.get('Anio_Raw')
            sem = v_r.get('Sem_Calendario_Raw') or v_r.get('Semana_Raw')
            f_derived = _derivar_fecha_iso_semana(ano, sem)
            if f_derived:
                return f_derived
                
            camp = v_r.get('Campana_Raw')
            if camp:
                numeros = re.findall(r'\d+', str(camp))
                if numeros:
                    primer_num = int(numeros[0])
                    year_campana = primer_num + 2000 if primer_num < 100 else primer_num
                    return f'{year_campana}-01-01'
                    
            return '2015-01-01'
            
        df['_Deriv_Fecha_Temp'] = [
            _derivar_fecha_fila(df.loc[idx, 'Fecha_Raw'], v_raw_df.loc[idx])
            for idx in df.index
        ]
        
        # 3. Resolver dimensiones en batch
        df['_Fundo_Temp'] = None
        
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Deriv_Fecha_Temp',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo='_Fundo_Temp',
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_cama='Cama_Raw',
            col_dni='DNI_Raw',
            dominio_fecha='induccion_floral'
        )
        
        if df_resolved.empty:
            return []
            
        v_raw_resolved = v_raw_df.loc[df_resolved.index]
        
        # 4. Formatear payload final aplicando lógica de negocio local
        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = _a_entero_nulo(r.get(col_id_origen))
            
            # Si no hay variedad y tampoco hay actividad de brotes/plantas, se descarta silenciosamente
            variedad_raw = r.get('Variedad_Fuente_Raw')
            v_r = v_raw_resolved.loc[idx]
            if pd.isna(variedad_raw) or str(variedad_raw).strip().lower() in ('', 'none', 'nan'):
                total_organos = _a_entero_no_negativo(v_r.get('Total_Organos_Raw'))
                if total_organos is None or total_organos == 0:
                    continue
                    
            plantas_por_cama = _a_entero_no_negativo(r.get('PlantasPorCama_Raw'))
            plantas_con_induccion = _a_entero_no_negativo(r.get('PlantasConInduccion_Raw'))
            brotes_con_induccion = _a_entero_no_negativo(r.get('BrotesConInduccion_Raw'))
            brotes_con_flor = _a_entero_no_negativo(r.get('BrotesConFlor_Raw'))
            
            brotes_totales_raw = _a_entero_no_negativo(r.get('BrotesTotales_Raw'))
            if brotes_totales_raw is None or brotes_totales_raw == 0:
                brotes_totales_raw = _a_entero_no_negativo(v_r.get('BrotesTotales_Raw'))
            if brotes_totales_raw is None or brotes_totales_raw == 0:
                brotes_totales_raw = _a_entero_no_negativo(v_r.get('pEvaluadas_Raw'))
            brotes_totales = brotes_totales_raw
            
            if brotes_totales is None or brotes_totales == 0:
                brotes_totales = _a_entero_no_negativo(r.get('BrotesConInduccion_Raw'))
                
            uso_proxy = False
            if plantas_por_cama is None or plantas_por_cama <= 0:
                todos_cero = all(v is None or v == 0 for v in [
                    plantas_con_induccion, brotes_con_induccion, brotes_con_flor, brotes_totales
                ])
                if todos_cero:
                    # Fila vacía (semana sin actividad): se descarta sin penalizar tasa de rechazo
                    continue
                # Proxy checks
                proxy = brotes_totales if (brotes_totales and brotes_totales > 0) else None
                if proxy is None and brotes_con_flor and brotes_con_flor > 0:
                    proxy = brotes_con_flor
                if proxy:
                    plantas_por_cama = proxy
                    uso_proxy = True
                else:
                    self.registrar_rechazo(id_origen, 'PlantasPorCama_Raw', r.get('PlantasPorCama_Raw'), 'Cantidad de plantas por cama invalida')
                    continue
                    
            if uso_proxy:
                if plantas_con_induccion is None:
                    plantas_con_induccion = 0
                if brotes_con_induccion is None:
                    brotes_con_induccion = 0
                if brotes_totales is None or brotes_totales <= 0:
                    brotes_totales = plantas_por_cama
                if brotes_con_flor is None:
                    brotes_con_flor = 0
                    
            if plantas_con_induccion is None:
                self.registrar_rechazo(id_origen, 'PlantasConInduccion_Raw', r.get('PlantasConInduccion_Raw'), 'Plantas con induccion invalida')
                continue
            if brotes_totales is None or brotes_totales <= 0:
                self.registrar_rechazo(id_origen, 'BrotesTotales_Raw', r.get('BrotesTotales_Raw'), 'Cantidad de brotes totales invalida')
                continue
            if brotes_con_induccion is None:
                if brotes_con_flor is not None:
                    brotes_con_induccion = brotes_con_flor
                else:
                    self.registrar_rechazo(id_origen, 'BrotesConInduccion_Raw', r.get('BrotesConInduccion_Raw'), 'Brotes con induccion invalida')
                    continue
            if brotes_con_flor is None:
                self.registrar_rechazo(id_origen, 'BrotesConFlor_Raw', r.get('BrotesConFlor_Raw'), 'Brotes con flor invalida')
                continue
                
            if id_origen is not None:
                self.ids_procesados.append(id_origen)
                
            payload.append({
                'ID_Geografia':                   r['ID_Geografia'],
                '_id_modulo_catalogo':            r['_id_modulo_catalogo'],
                'ID_Tiempo':                      int(r['ID_Tiempo']),
                'ID_Variedad':                    int(r['ID_Variedad']),
                'ID_Personal':                    int(r['ID_Personal']),
                'Tipo_Evaluacion':                _texto_nulo(r.get('Evaluacion_Raw')) or 'SIN_TIPO',
                'Cantidad_Plantas_Por_Cama':      plantas_por_cama,
                'Cantidad_Plantas_Con_Induccion': plantas_con_induccion,
                'Cantidad_Brotes_Con_Induccion':  brotes_con_induccion,
                'Cantidad_Brotes_Totales':        brotes_totales,
                'Cantidad_Brotes_Con_Flor':       brotes_con_flor,
                'Pct_Plantas_Con_Induccion':      _pct(plantas_con_induccion, plantas_por_cama) or 0.0,
                'Pct_Brotes_Con_Induccion':       _pct(brotes_con_induccion, brotes_totales) or 0.0,
                'Pct_Brotes_Con_Flor':            _pct(brotes_con_flor, brotes_totales) or 0.0,
                'Fecha_Evento':                   r['Fecha_Evento_dt'],
                'Estado_DQ':                      'OK',
                'id_origen_rastreo':              id_origen,
            })
        return payload


def cargar_fact_induccion_floral(engine: Engine) -> dict:
    proc = ProcesadorInduccionFloral(engine, columna_id='ID_Induccion_Floral')

    # Layout real de Bronce.Induccion_Floral: la variedad y las métricas año/semana
    # viven empacadas en Valores_Raw; el tipo viene en Evaluacion_Raw.
    cols_raw = [
        'Fecha_Raw', 'DNI_Raw', 'Fecha_Subida_Raw',
        'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Evaluacion_Raw',
        'Cama_Raw', 'PlantasPorCama_Raw',
        'PlantasConInduccion_Raw', 'BrotesConInduccion_Raw', 'BrotesConFlor_Raw',
        'Valores_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        # La variedad viene empacada en Valores_Raw (clave 'Variedad_Raw'), no en columna.
        df['Variedad_Fuente_Raw'] = df['Valores_Raw'].map(
            lambda v: _parsear_valores_raw(v).get('Variedad_Raw')
        )
        df, cuar_var = homologar_columna(
            df, 'Variedad_Fuente_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Induccion_Floral',
        )
        df = df.copy()
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_InduccionFloral')

        return proc.finalizar_proceso(contexto)
