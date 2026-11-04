"""
fact_ciclo_poda.py
==================
Carga Silver.Fact_Ciclo_Poda desde:
  - Bronce.Evaluacion_Calidad_Poda
  - Bronce.Ciclos_Fenologicos

Grain: Fecha + Geo + Variedad
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.texto import titulo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact
from utils.tipos import a_decimal as _a_decimal, a_entero as _a_entero


TABLA_PODA    = 'Bronce.Evaluacion_Calidad_Poda'
TABLA_CICLOS  = 'Bronce.Ciclos_Fenologicos'
TABLA_DESTINO = 'Silver.Fact_Ciclo_Poda'


class ProcesadorCicloPoda(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_PODA, TABLA_DESTINO, columna_id='ID_Evaluacion_Poda')
        # Grain: Geo + Tiempo + Variedad + Tipo_Evaluacion + Punto
        # (cada fila Bronce es UN punto de muestreo dentro de la valvula)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Tipo_Evaluacion', 'Punto']
        self.columna_tiebreaker_timestamp = 'Fecha_Registro_App'

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)

        # 2. Extraer punto y filtrar nulos registrando cuarentena
        punto_s = self._vectorized_get_raw_val(df, v_raw_df, 'Punto_Raw').map(self.a_int)
        df['Punto_Temp'] = punto_s
        
        # Extraer fecha real de registro en la app para usarla como tiebreaker de duplicados
        fecha_reg_s = self._vectorized_get_raw_val(df, v_raw_df, 'Fecha_Registro_Raw')
        df['Fecha_Registro_App'] = fecha_reg_s
        
        nulos_mask = df['Punto_Temp'].isna()
        if nulos_mask.any():
            df_nulos = df[nulos_mask]
            for idx, r in df_nulos.iterrows():
                id_orig = int(r['ID_Evaluacion_Poda'])
                self.registrar_rechazo(
                    id_orig,
                    columna='Punto_Raw',
                    valor=r.get('Punto_Raw'),
                    motivo='Punto_Raw no especificado o invalido',
                )
            df = df[~nulos_mask]

        if df.empty:
            return []

        # 3. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo='Fundo_Raw',
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            dominio_fecha='ciclo_poda'
        )

        if df_resolved.empty:
            return []

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Evaluacion_Poda'])
            self.ids_procesados.append(id_origen)

            payload.append({
                'ID_Geografia':       r['ID_Geografia'],
                '_id_modulo_catalogo': r['_id_modulo_catalogo'],
                'ID_Tiempo':          int(r['ID_Tiempo']),
                'ID_Variedad':        int(r['ID_Variedad']),
                'Tipo_Evaluacion':    titulo(r.get('Tipo_Evaluacion_Raw')) or 'SIN_TIPO',
                'Punto':              int(r['Punto_Temp']),
                'Tallos_Planta':      _a_decimal(r.get('TallosPlanta_Raw')),
                'Longitud_Tallo':     _a_decimal(r.get('LongitudTallo_Raw')),
                'Diametro_Tallo':     _a_decimal(r.get('DiametroTallo_Raw')),
                'Ramilla_Planta':     _a_decimal(r.get('RamillaPlanta_Raw')),
                'Tocones_Planta':     _a_decimal(r.get('ToconesPlanta_Raw')),
                'Cortes_Defectuosos': _a_decimal(r.get('CortesDefectuosos_Raw')),
                'Altura_Poda':        _a_decimal(r.get('AlturaPoda_Raw')),
                'Fecha_Evento':       r['Fecha_Evento_dt'],
                'Fecha_Sistema':      r.get('Fecha_Sistema'),
                'Fecha_Registro_App': r.get('Fecha_Registro_App'),
                'Estado_DQ':          'OK',
                'id_origen_rastreo':  id_origen,
            })
        return payload


def cargar_fact_ciclo_poda(engine: Engine) -> dict:
    proc = ProcesadorCicloPoda(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw',
        'Variedad_Raw', 'Tipo_Evaluacion_Raw', 'Punto_Raw',
        'TallosPlanta_Raw',
        'LongitudTallo_Raw', 'DiametroTallo_Raw', 'RamillaPlanta_Raw',
        'ToconesPlanta_Raw', 'CortesDefectuosos_Raw', 'AlturaPoda_Raw',
        'Fecha_Sistema', 'Valores_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_PODA, conexion,
            columna_id_origen='ID_Evaluacion_Poda'
        )
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_CicloPoda')

        return proc.finalizar_proceso(contexto)
