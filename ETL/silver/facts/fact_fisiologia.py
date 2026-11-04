"""
fact_fisiologia.py
==================
Carga Silver.Fact_Fisiologia desde Bronce.Fisiologia.

Grain: Geo + Tiempo + Variedad + Tercio
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.homologador import homologar_columna
from mdm.lookup import obtener_id_campana_anual
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
)


TABLA_ORIGEN  = 'Bronce.Fisiologia'
TABLA_DESTINO = 'Silver.Fact_Fisiologia'

MAPA_TERCIO = {
    'BAJO': 'BAJO', 'B': 'BAJO', 'LOW': 'BAJO',
    'MEDIO': 'MEDIO', 'M': 'MEDIO', 'MID': 'MEDIO',
    'ALTO': 'ALTO', 'A': 'ALTO', 'HIGH': 'ALTO',
}


def _normalizar_tercio(valor) -> str | None:
    tercio_raw = str(valor or '').strip().upper()
    return MAPA_TERCIO.get(tercio_raw, tercio_raw or None)


class ProcesadorFisiologia(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Fisiologia')
        # Grain: Geo + Tiempo + Variedad + Tercio + Brote
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Tercio', 'Brote']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)
        
        # 2. Obtener series de columnas geográficas usando _vectorized_get_raw_val
        fundo_s = self._vectorized_get_raw_val(df, v_raw_df, 'Fundo_Raw')
        modulo_s = self._vectorized_get_raw_val(df, v_raw_df, 'Modulo_Raw')
        turno_s = self._vectorized_get_raw_val(df, v_raw_df, 'Turno_Raw')
        valvula_s = self._vectorized_get_raw_val(df, v_raw_df, 'Valvula_Raw')
        
        # 3. Resolver dimensiones en batch
        df['_Fundo_Temp'] = fundo_s
        df['_Modulo_Temp'] = modulo_s
        df['_Turno_Temp'] = turno_s
        df['_Valvula_Temp'] = valvula_s
        
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='Fecha_Raw',
            col_modulo='_Modulo_Temp',
            col_variedad='Variedad_Raw',
            col_fundo='_Fundo_Temp',
            col_turno='_Turno_Temp',
            col_valvula='_Valvula_Temp',
            col_dni=None,
        )
        
        if df_resolved.empty:
            return []
            
        # Parsear de nuevo v_raw_df para el subconjunto resuelto
        v_raw_resolved = v_raw_df.loc[df_resolved.index]
        
        # 4. Extraer métricas en lote
        brotes_prod = self._vectorized_get_raw_val(df_resolved, v_raw_resolved, 'BrotesProd_Raw').map(self.a_int)
        
        # 5. Generar lista de payloads
        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Fisiologia'])
            self.ids_procesados.append(id_origen)
            
            v_r = v_raw_resolved.loc[idx]
            brote_val = str(self._get_val_loc(r, v_r, 'Brote_Raw') or '')
            
            payload.append({
                'ID_Geografia':        r['ID_Geografia'],
                '_id_modulo_catalogo':  r['_id_modulo_catalogo'],
                'ID_Tiempo':           int(r['ID_Tiempo']),
                'ID_Variedad':         int(r['ID_Variedad']),
                'Tercio':              _normalizar_tercio(self._get_val_loc(r, v_r, 'Tercio_Raw')),
                'Brote':               brote_val,
                'Brotes_Productivos':  brotes_prod.loc[idx],
                'Brotes_Vegetativos':  self.a_int(self._get_val_loc(r, v_r, 'BrotesVeg_Raw')),
                'Hinchadas':           self.a_int(self._get_val_loc(r, v_r, 'Hinchadas_Raw')),
                'Productivas':         self.a_int(self._get_val_loc(r, v_r, 'Productivas_Raw')),
                'Total_Organos':       self.a_int(self._get_val_loc(r, v_r, 'Total_Org_Raw')),
                'Aux':                 self._get_val_loc(r, v_r, 'Aux_Raw') or self._get_val_loc(r, v_r, 'AUXILIAR_Raw'),
                'Fecha_Evento':        r['Fecha_Evento_dt'],
                'ID_Campana':          obtener_id_campana_anual(r['Fecha_Evento_dt'], self.engine),
                'Estado_DQ':           'OK',
                'id_origen_rastreo':   id_origen,
            })
        return payload


def cargar_fact_fisiologia(engine: Engine) -> dict:
    proc = ProcesadorFisiologia(engine)

    # Definición de columnas RAW necesarias
    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Sector_Raw', 'Modulo_Raw', 'Turno_Raw', 
        'Valvula_Raw', 'Variedad_Raw', 'Tercio_Raw', 'Hinchadas_Raw', 
        'Productivas_Raw', 'Total_Org_Raw', 'Brote_Raw', 'BrotesProd_Raw', 
        'BrotesVeg_Raw', 'Valores_Raw'
    ]
    
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion
        )
        # Deduplicación temprana — clave completa incluyendo válvula, turno y valores
        df = proc.pre_limpiar_duplicados_batch(df, [
            'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Fecha_Raw', 
            'Variedad_Raw', 'Tercio_Raw', 'Brote_Raw', 'Valores_Raw'
        ])
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Fisiologia')

        return proc.finalizar_proceso(contexto)