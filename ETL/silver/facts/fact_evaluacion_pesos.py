"""
fact_evaluacion_pesos.py
========================
Carga Silver.Fact_Evaluacion_Pesos desde Bronce.Evaluacion_Pesos.

Grain: Fecha + Geo + Personal + Variedad
FKs obligatorias: ID_Tiempo, ID_Geografia, ID_Variedad, ID_Personal
Validacion critica: Peso_Baya_g BETWEEN 0.5 AND 8.0
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from dq.validador import validar_peso_baya
from mdm.homologador import homologar_columna
from mdm.lookup import obtener_id_campana_anual
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
    derivar_fecha_iso_semana as _derivar_fecha_iso_semana,
)


TABLA_ORIGEN  = 'Bronce.Evaluacion_Pesos'
TABLA_DESTINO = 'Silver.Fact_Evaluacion_Pesos'


def _calcular_peso_ponderado(fila) -> float | None:
    """
    Calcula el peso promedio ponderado de baya en gramos.
    Usa todas las categorias de bayas disponibles en el reporte horizontal.
    Retorna None si no hay datos suficientes para calcular.
    """
    def safe_float(val, default=0.0):
        try:
            return float(str(val)) if val is not None and str(val).strip() not in ('', 'None', 'nan') else default
        except (ValueError, TypeError):
            return default

    # Si ya viene un PesoBaya_Raw directo (otros formatos), usarlo
    peso_directo = safe_float(fila.get('PesoBaya_Raw'))
    cant_directo = safe_float(fila.get('CantMuestra_Raw'))
    if peso_directo > 0 and cant_directo > 0:
        return round(peso_directo / cant_directo, 4)

    # Calcular desde columnas horizontales
    pares = [
        ('BayasPequenas_Raw',  'PesoBayasPequenas_Raw'),
        ('BayasGrandes_Raw',   None),
        ('BayasFase1_Raw',     'PesoBayasFase1_Raw'),
        ('BayasFase2_Raw',     'PesoBayasFase2_Raw'),
        ('Cremas_Raw',         'PesoCremas_Raw'),
        ('Maduras_Raw',        'PesoMaduras_Raw'),
        ('Cosechables_Raw',    'PesoCosechables_Raw'),
    ]

    total_bayas = 0.0
    total_peso  = 0.0
    for col_cnt, col_peso in pares:
        cnt  = safe_float(fila.get(col_cnt))
        peso = safe_float(fila.get(col_peso)) if col_peso else 0.0
        total_bayas += cnt
        total_peso  += peso

    if total_bayas > 0 and total_peso > 0:
        return round(total_peso / total_bayas, 4)

    return None


def _safe_int(v) -> int:
    try:
        return max(0, int(float(str(v)))) if v is not None and str(v).strip() not in ('', 'None', 'nan') else 0
    except (ValueError, TypeError):
        return 0


class ProcesadorEvaluacionPesos(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO)
        # Grain: Geo + Tiempo + Variedad + Personal + Peso
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal']
        self.LIMITE_ERROR = 101.0
        self.LIMITE_CRITICO = 101.0

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # 1. Derivar Fecha_Evento de forma vectorizada
        def _get_fecha_pesos(r_fecha, ano, sem):
            if r_fecha and str(r_fecha).strip() not in ('', 'None', 'nan'):
                return str(r_fecha)
            return _derivar_fecha_iso_semana(ano, sem)

        df['_Deriv_Fecha_Temp'] = [
            _get_fecha_pesos(df.loc[idx, 'Fecha_Raw'], df.loc[idx, 'Ano_Raw'], df.loc[idx, 'Semana_Raw'])
            for idx in df.index
        ]

        # 2. Derivar Módulo Geográfico vectorialmente
        modulo_raw = df['Modulo_Raw']
        valvula_raw = df['Valvula_Raw']
        df['_Modulo_Temp'] = modulo_raw.where(modulo_raw.notna() & (modulo_raw.astype(str).str.strip() != '') & (modulo_raw.astype(str) != 'None') & (modulo_raw.astype(str) != 'nan'), valvula_raw)

        # 3. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Deriv_Fecha_Temp',
            col_modulo='_Modulo_Temp',
            col_variedad='Variedad_Canonica',
            col_fundo='Fundo_Raw',
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_cama='Cama_Raw',
            col_dni='DNI_Raw',
            dominio_fecha='evaluacion_pesos'
        )

        if df_resolved.empty:
            return []

        payload = []
        pares = [
            ('BayasPequenas_Raw',  'PesoBayasPequenas_Raw'),
            ('BayasGrandes_Raw',   None),
            ('BayasFase1_Raw',     'PesoBayasFase1_Raw'),
            ('BayasFase2_Raw',     'PesoBayasFase2_Raw'),
            ('Cremas_Raw',         'PesoCremas_Raw'),
            ('Maduras_Raw',        'PesoMaduras_Raw'),
            ('Cosechables_Raw',    'PesoCosechables_Raw'),
        ]

        def safe_float(val, default=0.0):
            try:
                return float(str(val)) if val is not None and str(val).strip() not in ('', 'None', 'nan') else default
            except (ValueError, TypeError):
                return default

        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Evaluacion_Pesos'])

            # Calcular peso ponderado desde columnas horizontales
            peso = _calcular_peso_ponderado(r)
            if peso is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='Peso_Baya_g',
                    valor=None,
                    motivo='Registro sin datos de peso validos en el Excel',
                    severidad='ALTO'
                )
                continue

            # Validar rango DQ dinámico (desde Config.Parametros_Pipeline)
            peso_val, error_peso = validar_peso_baya(peso, config=self.config_params)
            if error_peso:
                self.registrar_rechazo(
                    id_origen,
                    columna=error_peso.get('columna', 'Peso_Baya_g'),
                    valor=error_peso.get('valor'),
                    motivo=error_peso.get('motivo', 'Peso invalido'),
                    severidad=error_peso.get('severidad', 'ALTO'),
                )
                continue

            self.ids_procesados.append(id_origen)
            cantidad = sum(safe_float(r.get(c)) for c, _ in pares)

            payload.append({
                'ID_Geografia':              r['ID_Geografia'],
                '_id_modulo_catalogo':       r['_id_modulo_catalogo'],
                'ID_Tiempo':                 int(r['ID_Tiempo']),
                'ID_Variedad':               int(r['ID_Variedad']),
                'ID_Personal':               int(r['ID_Personal']),
                'Peso_Promedio_Baya_g':      peso_val,
                'Cantidad_Cosechables':      safe_float(r.get('Cosechables_Raw')),
                'Peso_Cosechables_g':        safe_float(r.get('PesoCosechables_Raw')),
                'Cantidad_Bayas_Muestra':    cantidad,
                'Fecha_Evento':              r['Fecha_Evento_dt'],
                'Fecha_Sistema':             r.get('Fecha_Sistema'),
                'ID_Campana':                obtener_id_campana_anual(r['Fecha_Evento_dt'], self.engine),
                'Estado_DQ':                 'OK',
                'id_origen_rastreo':         id_origen,
            })
        return payload


def cargar_fact_evaluacion_pesos(engine: Engine) -> dict:
    proc = ProcesadorEvaluacionPesos(engine)

    cols_raw = [
        'Fecha_Raw', 'Ano_Raw', 'Semana_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Valvula_Raw', 'Turno_Raw',
        'Cama_Raw', 'Variedad_Raw', 'Evaluacion_Raw', 'DNI_Raw', 'Fecha_Sistema', 'PesoBaya_Raw',
        'CantMuestra_Raw', 'BayasPequenas_Raw', 'PesoBayasPequenas_Raw',
        'BayasGrandes_Raw', 'BayasFase1_Raw', 'PesoBayasFase1_Raw',
        'BayasFase2_Raw', 'PesoBayasFase2_Raw', 'Cremas_Raw', 'PesoCremas_Raw',
        'Maduras_Raw', 'PesoMaduras_Raw', 'Cosechables_Raw', 'PesoCosechables_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Evaluacion_Pesos'
        )
        df = df.copy()
        
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_EvaluacionPesos')

        return proc.finalizar_proceso(contexto)
