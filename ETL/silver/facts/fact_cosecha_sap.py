"""
fact_cosecha_sap.py
===================
Carga Silver.Fact_Cosecha_SAP desde:
  - Bronce.Reporte_Cosecha
  - Bronce.Data_SAP

Grain: Fecha + Geografia + Variedad + Condicion_Cultivo
FKs obligatorias: ID_Tiempo, ID_Geografia, ID_Variedad, ID_Condicion_Cultivo
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from config.parametros import obtener_int
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import procesar_fecha, obtener_id_tiempo
from utils.texto import titulo
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_COSECHA = 'Bronce.Reporte_Cosecha'
TABLA_SAP     = 'Bronce.Data_SAP'
TABLA_DESTINO = 'Silver.Fact_Cosecha_SAP'


def _obtener_id_condicion_default() -> int:
    try:
        return obtener_int('ID_CONDICION_CULTIVO_DEFAULT', 1)
    except Exception:
        return 1


def _leer_bronce_cosecha(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Reporte_Cosecha,
                Fecha_Raw,
                Fundo_Raw,
                Modulo_Raw,
                Variedad_Raw,
                KgNeto_Raw,
                Jabas_Raw,
                Lote_Raw,
                Responsable_Raw
            FROM {TABLA_COSECHA}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _leer_bronce_sap(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Data_SAP,
                Fecha_Raw,
                Fundo_Raw,
                Modulo_Raw,
                Variedad_Raw,
                Peso_Bruto_Raw,
                Peso_Neto_Raw,
                Cantidad_Jabas_Raw,
                Lote_Raw,
                Almacen_Raw,
                Doc_Remision_Raw,
                Codigo_Cliente_Raw,
                Responsable_Raw,
                Descripcion_Material_Raw,
                Material_Codigo_Raw,
                Fecha_Recepcion_Raw
            FROM {TABLA_SAP}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _a_decimal(v):
    try:
        val = float(str(v).replace(',', '.'))
        return round(val, 3)
    except (ValueError, TypeError):
        return None


def _a_int(v):
    try:
        return int(float(str(v)))
    except (ValueError, TypeError):
        return None


class ProcesadorCosechaReporte(BaseFactProcessor):
    """Procesador para Bronce.Reporte_Cosecha → Silver.Fact_Cosecha_SAP."""

    def __init__(self, engine: Engine, id_condicion_default: int):
        super().__init__(engine, TABLA_COSECHA, TABLA_DESTINO, columna_id='ID_Reporte_Cosecha')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Condicion_Cultivo', 'Kg_Neto_MP']
        self._id_condicion_default = id_condicion_default

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo='Fundo_Raw',
            col_turno=None,
            col_valvula=None,
            dominio_fecha='cosecha_sap'
        )

        if df_resolved.empty:
            return []

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Reporte_Cosecha'])

            kg_neto = _a_decimal(r.get('KgNeto_Raw'))
            if kg_neto is None:
                continue

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':        r['ID_Geografia'],
                '_id_modulo_catalogo': r['_id_modulo_catalogo'],
                'ID_Tiempo':           int(r['ID_Tiempo']),
                'ID_Variedad':         int(r['ID_Variedad']),
                'ID_Condicion_Cultivo': self._id_condicion_default,
                'Kg_Neto_MP':          kg_neto,
                'Fecha_Evento':        r['Fecha_Evento_dt'],
                'Estado_DQ':           'OK',
                'id_origen_rastreo':   id_origen,
            })
        return payload


class ProcesadorCosechaSAP(BaseFactProcessor):
    """Procesador para Bronce.Data_SAP → Silver.Fact_Cosecha_SAP."""

    def __init__(self, engine: Engine, id_condicion_default: int):
        super().__init__(engine, TABLA_SAP, TABLA_DESTINO, columna_id='ID_Data_SAP')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Condicion_Cultivo', 'Kg_Neto_MP']
        self._id_condicion_default = id_condicion_default

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo='Fundo_Raw',
            col_turno=None,
            col_valvula=None,
            dominio_fecha='cosecha_sap'
        )

        if df_resolved.empty:
            return []

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Data_SAP'])

            kg_neto = _a_decimal(r.get('Peso_Neto_Raw'))
            if kg_neto is None:
                continue

            self.ids_procesados.append(id_origen)
            payload.append({
                'ID_Geografia':        r['ID_Geografia'],
                '_id_modulo_catalogo': r['_id_modulo_catalogo'],
                'ID_Tiempo':           int(r['ID_Tiempo']),
                'ID_Variedad':         int(r['ID_Variedad']),
                'ID_Condicion_Cultivo': self._id_condicion_default,
                'Kg_Neto_MP':          kg_neto,
                'Fecha_Evento':        r['Fecha_Evento_dt'],
                'Estado_DQ':           'OK',
                'id_origen_rastreo':   id_origen,
            })
        return payload


def cargar_fact_cosecha_sap(engine: Engine) -> dict:
    id_condicion_default = _obtener_id_condicion_default()

    df_cosecha = _leer_bronce_cosecha(engine)
    df_sap = _leer_bronce_sap(engine)

    if df_cosecha.empty and df_sap.empty:
        return _finalizar_resumen_fact({'leidos': 0, 'insertados': 0, 'rechazados': 0, 'cuarentena': []})

    proc_cosecha = ProcesadorCosechaReporte(engine, id_condicion_default)
    proc_sap = ProcesadorCosechaSAP(engine, id_condicion_default)

    proc_cosecha.resumen['leidos'] = len(df_cosecha)
    proc_sap.resumen['leidos'] = len(df_sap)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        # Homologar variedades de cada fuente dentro de la misma transaccion
        if not df_cosecha.empty:
            df_cosecha, cuar_cosecha = homologar_columna(
                df_cosecha, 'Variedad_Raw', 'Variedad_Canonica', TABLA_COSECHA, conexion
            )
            proc_cosecha.resumen['cuarentena'].extend(cuar_cosecha)

        if not df_sap.empty:
            df_sap, cuar_sap = homologar_columna(
                df_sap, 'Variedad_Raw', 'Variedad_Canonica', TABLA_SAP, conexion
            )
            proc_sap.resumen['cuarentena'].extend(cuar_sap)

        # Construir payloads y cargar cada fuente con su procesador
        if not df_cosecha.empty:
            payload_cosecha = proc_cosecha._construir_payload(df_cosecha)
            proc_cosecha._ejecutar_insercion_masiva_segura(contexto, payload_cosecha, '#Temp_CosechaReporte')
            proc_cosecha.finalizar_proceso(contexto)

        if not df_sap.empty:
            payload_sap = proc_sap._construir_payload(df_sap)
            proc_sap._ejecutar_insercion_masiva_segura(contexto, payload_sap, '#Temp_CosechaSAP')
            proc_sap.finalizar_proceso(contexto)

    # Consolidar resumen de ambas fuentes
    resumen_total = {
        'leidos':      proc_cosecha.resumen['leidos'] + proc_sap.resumen['leidos'],
        'insertados':  proc_cosecha.resumen['insertados'] + proc_sap.resumen['insertados'],
        'rechazados':  proc_cosecha.resumen['rechazados'] + proc_sap.resumen['rechazados'],
        'cuarentena':  proc_cosecha.resumen['cuarentena'] + proc_sap.resumen['cuarentena'],
    }
    return _finalizar_resumen_fact(resumen_total)
