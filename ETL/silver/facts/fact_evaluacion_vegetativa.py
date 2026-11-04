"""
fact_evaluacion_vegetativa.py
=============================
Carga Silver.Fact_Evaluacion_Vegetativa desde Bronce.Evaluacion_Vegetativa.

Grano real (verificado en BD): (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Campana, Piso, ID_Origen_Bronce).
Cada fila Bronce se EXPANDE a 5 filas Silver (una por Piso 1..5).
Pisos sin datos quedan con medidas en 0 (no NULL).
"""

import pandas as pd
from sqlalchemy.engine import Engine

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.tipos import a_entero, a_decimal
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_ORIGEN  = 'Bronce.Evaluacion_Vegetativa'
TABLA_DESTINO = 'Silver.Fact_Evaluacion_Vegetativa'

PISOS = range(1, 6)


def _a_decimal_cero(v) -> float:
    d = a_decimal(v)
    return float(d) if d is not None else 0.0


def _a_entero_cero(v) -> int:
    d = a_entero(v)
    return int(d) if d is not None else 0


class ProcesadorEvaluacionVegetativa(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Evaluacion_Veg')
        self.LIMITE_ERROR = 5.0
        self.columnas_clave_unica = [
            'ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Campana', 'Piso', 'ID_Origen_Bronce'
        ]

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # 1. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo=None,
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_cama='Cama_Raw',
            dominio_fecha='evaluacion_vegetativa'
        )

        if df_resolved.empty:
            return []

        # 2. Parsear Valores_Raw en lote para los registros resueltos
        lista_v_raw = [self.parsear_raw(x) for x in df_resolved['Valores_Raw']]

        payload: list[dict] = []
        registros = df_resolved.to_dict('records')

        for r, v_r in zip(registros, lista_v_raw):
            id_origen = int(r['ID_Evaluacion_Veg'])
            self.ids_procesados.append(id_origen)

            semanas_raw = r.get('Semanas_Poda_Raw') or v_r.get('Semanas_Poda_Raw')
            semanas     = _a_entero_cero(semanas_raw)

            altura      = _a_decimal_cero(r.get('Altura_Raw'))
            tb          = _a_decimal_cero(r.get('Tallos_Basales_Raw'))
            tbn         = _a_decimal_cero(r.get('Tallos_Basales_Nuevos_Raw'))

            muestra_raw = r.get('Muestra_Plantas_Raw') or v_r.get('Muestra_Plantas_Raw')
            muestra     = int(a_entero(muestra_raw)) if a_entero(muestra_raw) is not None else 1

            for piso in PISOS:
                payload.append({
                    'ID_Geografia':          r['ID_Geografia'],
                    '_id_modulo_catalogo':   r['_id_modulo_catalogo'],
                    'ID_Tiempo':             int(r['ID_Tiempo']),
                    'ID_Variedad':           int(r['ID_Variedad']),
                    'Piso':                  piso,
                    'Semanas_Despues_Poda':  semanas,
                    'Altura':                altura,
                    'Tallos_Basales':        tb,
                    'Tallos_Basales_Nuevos': tbn,
                    'Muestra_Plantas':       muestra,
                    'Brotes_Generales':      _a_decimal_cero(r.get(f'Piso{piso}_Brotes_Raw')),
                    'Brotes_Productivos':    _a_decimal_cero(r.get(f'Piso{piso}_Productivos_Raw')),
                    'Diametro_Brote':        _a_decimal_cero(r.get(f'Piso{piso}_Diametro_Raw')),
                    'Fecha_Evento':          r['Fecha_Evento_dt'],
                    'Estado_DQ':             'OK',
                    'ID_Origen_Bronce':      id_origen,
                    'id_origen_rastreo':     id_origen,
                })
        return payload


def cargar_fact_evaluacion_vegetativa(engine: Engine) -> dict:
    proc = ProcesadorEvaluacionVegetativa(engine)

    cols_raw = [
        'Fecha_Raw', 'Campana_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Cama_Raw',
        'Variedad_Raw', 'Evaluador_Raw', 'DNI_Raw', 'Semanas_Poda_Raw',
        'Altura_Raw', 'Tallos_Basales_Raw', 'Tallos_Basales_Nuevos_Raw', 'Muestra_Plantas_Raw',
        'Piso1_Brotes_Raw', 'Piso1_Productivos_Raw', 'Piso1_Diametro_Raw',
        'Piso2_Brotes_Raw', 'Piso2_Productivos_Raw', 'Piso2_Diametro_Raw',
        'Piso3_Brotes_Raw', 'Piso3_Productivos_Raw', 'Piso3_Diametro_Raw',
        'Piso4_Brotes_Raw', 'Piso4_Productivos_Raw', 'Piso4_Diametro_Raw',
        'Piso5_Brotes_Raw', 'Piso5_Productivos_Raw', 'Piso5_Diametro_Raw',
        'Valores_Raw',
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Evaluacion_Veg',
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_EvaluacionVegetativa')

        return proc.finalizar_proceso(contexto)
