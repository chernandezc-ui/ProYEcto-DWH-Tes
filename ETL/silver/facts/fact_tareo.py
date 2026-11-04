"""
fact_tareo.py
=============
Carga Silver.Fact_Tareo desde Bronce.Consolidado_Tareos.

Grain: Fecha + DNI + Actividad + Geo
FKs obligatorias: ID_Tiempo, ID_Personal, ID_Actividad_Operativa, ID_Geografia
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from config.parametros import TOKENS_FECHA_NO_OPERATIVA, TOKENS_SUPERVISOR_NO_OPERATIVO
from utils.contexto_transaccional import ContextoTransaccionalETL
from mdm.lookup import obtener_id_actividad
from utils.fechas import obtener_id_tiempo
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_ORIGEN  = 'Bronce.Consolidado_Tareos'
TABLA_DESTINO = 'Silver.Fact_Tareo'


def _es_fila_no_operativa(fila) -> bool:
    fecha_raw = str(fila.get('Fecha_Raw') or '').strip()
    supervisor_raw = str(fila.get('IDPersonalGeneral_Raw') or '').strip().upper()
    return fecha_raw.upper() in TOKENS_FECHA_NO_OPERATIVA or supervisor_raw in TOKENS_SUPERVISOR_NO_OPERATIVO


class ProcesadorTareo(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Tareo')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Personal', 'ID_Actividad_Operativa']
        self.ids_descartados: list[int] = []

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # Identificar columna ID original
        col_id_origen = self.columna_id
        if col_id_origen not in df.columns:
            col_id_origen = 'ID_Registro_Origen'

        # 1. Vectorizar descarte de filas no operativas
        mask_non_op = df['Fecha_Raw'].astype(str).str.strip().str.upper().isin(TOKENS_FECHA_NO_OPERATIVA) | \
                      df['IDPersonalGeneral_Raw'].astype(str).str.strip().str.upper().isin(TOKENS_SUPERVISOR_NO_OPERATIVO)
        
        df_descartado = df[mask_non_op]
        if not df_descartado.empty:
            self.ids_descartados = df_descartado[col_id_origen].dropna().astype(int).tolist()

        df_operative = df[~mask_non_op]
        if df_operative.empty:
            return []

        # 2. Resolver geografía, tiempo y personal principal en batch
        df_resolved = self.resolver_dimensiones_batch(
            df_operative,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad=None,
            col_fundo='Fundo_Raw',
            col_turno=None,
            col_valvula=None,
            col_dni='DNIResponsable_Raw',
            dominio_fecha='tareo'
        )

        if df_resolved.empty:
            return []

        # 3. Resolver supervisor (IDPersonalGeneral_Raw) en batch
        unique_sups = df_resolved['IDPersonalGeneral_Raw'].dropna().unique()
        mapeo_sups = {}
        for rd in unique_sups:
            from utils.dni import procesar_dni
            from mdm.lookup import obtener_id_personal
            dni, _ = procesar_dni(rd)
            id_pers = obtener_id_personal(dni, self.engine)
            mapeo_sups[rd] = None if id_pers == -1 else id_pers

        # 4. Resolver actividades operativas en batch
        unique_labores = df_resolved['Labor_Raw'].dropna().unique()
        mapeo_labores = {}
        for lr in unique_labores:
            mapeo_labores[lr] = obtener_id_actividad(lr, self.engine)

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Tareo'])

            id_actividad = mapeo_labores.get(r['Labor_Raw'])
            if not id_actividad:
                self.registrar_rechazo(
                    id_origen,
                    columna='Labor_Raw',
                    valor=r.get('Labor_Raw'),
                    motivo='Actividad no reconocida en Dim_Actividad_Operativa',
                )
                continue

            id_supervisor = mapeo_sups.get(r['IDPersonalGeneral_Raw'])

            try:
                horas = float(str(r.get('HorasTrabajadas_Raw', 0)).replace(',', '.'))
            except (ValueError, TypeError):
                horas = 0.0

            planilla = str(r.get('IDPlanilla_Raw', '')) or None

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':           r['ID_Geografia'],
                '_id_modulo_catalogo':    r['_id_modulo_catalogo'],
                'ID_Tiempo':              int(r['ID_Tiempo']),
                'ID_Personal':            int(r['ID_Personal']),
                'ID_Actividad_Operativa': id_actividad,
                'ID_Personal_Supervisor': id_supervisor,
                'Horas_Trabajadas':       horas,
                'ID_Planilla':            planilla,
                'Es_Observado_SAP':       0,
                'Fecha_Evento':           r['Fecha_Evento_dt'],
                'id_origen_rastreo':      id_origen,
            })
        return payload


def cargar_fact_tareo(engine: Engine) -> dict:
    proc = ProcesadorTareo(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'DNIResponsable_Raw',
        'IDPersonalGeneral_Raw', 'Labor_Raw', 'HorasTrabajadas_Raw',
        'IDPlanilla_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Tareo')

        # Marcar DESCARTADO para filas no operativas (encabezados, totales, etc.)
        if proc.ids_descartados:
            contexto.marcar_estado_carga(TABLA_ORIGEN, 'ID_Tareo', proc.ids_descartados, estado='DESCARTADO')

        return proc.finalizar_proceso(contexto)
