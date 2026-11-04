"""
fact_censo_plantas.py
=====================
Carga Silver.Fact_Censo_Plantas desde Bronce.Seguimiento_Errores.

Nota historica: este modulo era antes ``fact_sanidad_activo.py`` y poblaba
Silver.Fact_Sanidad_Activo con las metricas Plantas_Vivas / Plantas_Muertas /
Total_Plantas. En la fase35 la tabla pasa a llamarse Silver.Fact_Censo_Plantas
y la semantica cambia a Plantas_Buenas / Plantas_Regulares / Plantas_Malas.

PENDIENTE de decision de negocio: como mapean las columnas Raw del Bronce
(Plantas_Vivas_Raw, Plantas_Muertas_Raw, Total_Plantas_Raw) a las nuevas
metricas (Buenas/Regulares/Malas). Hasta definirlo, el loader lanza
NotImplementedError para evitar inserts incorrectos.
"""

import re
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from dq.validador import validar_total_plantas
from mdm.homologador import homologar_columna
from mdm.lookup import obtener_id_campana_anual
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact


TABLA_ORIGEN  = 'Bronce.Censo_Plantas'
TABLA_DESTINO = 'Silver.Fact_Censo_Plantas'

# Centinela para censos sin variedad declarada (ver fase51_seed_variedad_sin_variedad.sql).
# Un censo cuenta plantas por estado; la variedad es opcional, no se rechaza por ausencia.
ID_VARIEDAD_SIN_VARIEDAD = -1

MAPA_ESTADO_PLANTA = {
    'BUENAS': 1, 'PLANTAS BUENAS': 1, 'PLANTAS_BUENAS': 1, 'PLANTAS_VIVAS': 1, 'VIVAS': 1,
    'REGULARES': 2, 'PLANTAS REGULARES': 2, 'PLANTAS_REGULARES': 2,
    'MALAS': 3, 'PLANTAS MALAS': 3, 'PLANTAS_MALAS': 3,
    'MUERTAS': 4, 'HOYOS': 4, 'PLANTAS_MUERTAS': 4,
    'TOTAL_PLANTAS': -1 # Ignoramos el total si viene como columna
}


def _a_int(valor) -> int | None:
    try:
        return int(float(str(valor)))
    except (ValueError, TypeError):
        return None


class ProcesadorCensoPlantas(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Censo_Plantas')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Estado_Planta', 'Linea_Raw']
        self.LIMITE_CRITICO = 101.0
        self.LIMITE_ERROR = 101.0

    def _resolver_variedad_base(self, variedad_canonica: Any) -> int | None:
        from mdm.lookup import obtener_id_variedad
        return obtener_id_variedad(variedad_canonica, self.engine)

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        import re
        import datetime as _dt

        # Identificar columna ID original
        col_id_origen = self.columna_id
        if col_id_origen not in df.columns:
            col_id_origen = 'ID_Registro_Origen'

        # 1. Derivar Fecha de forma vectorizada
        def _get_fecha_censo(fila_fecha, fila_campana):
            if fila_fecha and str(fila_fecha).strip() not in ('', 'None', 'nan'):
                return str(fila_fecha)
            campana = str(fila_campana or '').strip()
            if campana and campana not in ('None', 'nan'):
                match = re.search(r'(\d{2,4})', campana)
                if match:
                    anio_str = match.group(1)
                    if len(anio_str) == 2:
                        anio_str = f"20{anio_str}"
                    return f"{anio_str}-01-01"
            return '2015-01-01'

        df['_Deriv_Fecha_Temp'] = [
            _get_fecha_censo(df.loc[idx, 'Fecha_Raw'], df.loc[idx, 'Campana_Raw'] if 'Campana_Raw' in df.columns else None)
            for idx in df.index
        ]

        # 2. Resolver geografía y tiempo en batch (sin variedad, variedad es opcional)
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Deriv_Fecha_Temp',
            col_modulo='Modulo_Raw',
            col_variedad=None,
            col_fundo='Fundo_Raw',
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_cama='Linea_Raw',
            dominio_fecha='censo_plantas'
        )

        if df_resolved.empty:
            return []

        # 3. Resolver variedad para los registros que sí la tienen declarada
        def is_empty(val):
            return val is None or str(val).strip() in ('', 'None', 'nan')

        df_con_var = df_resolved[~df_resolved['Variedad_Raw'].map(is_empty)]
        unique_vars = df_con_var['Variedad_Canonica'].dropna().unique()
        mapeo_vars = {}
        for rv in unique_vars:
            mapeo_vars[rv] = self._resolver_variedad_base(rv)

        ids_validos = []
        df_resolved['ID_Variedad'] = -1

        for idx, r in df_resolved.iterrows():
            var_raw = r.get('Variedad_Raw')
            if is_empty(var_raw):
                df_resolved.at[idx, 'ID_Variedad'] = ID_VARIEDAD_SIN_VARIEDAD
                ids_validos.append(idx)
            else:
                var_can = r.get('Variedad_Canonica')
                id_var = mapeo_vars.get(var_can)
                if id_var is None:
                    id_orig = int(r[col_id_origen])
                    self.registrar_rechazo(
                        id_orig,
                        columna='Variedad_Raw',
                        valor=var_raw if var_raw is not None else var_can,
                        motivo='Variedad sin match en Dim_Variedad',
                        tipo_regla='MDM',
                    )
                else:
                    df_resolved.at[idx, 'ID_Variedad'] = id_var
                    ids_validos.append(idx)

        df_resolved = df_resolved.loc[ids_validos]
        if df_resolved.empty:
            return []

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Censo_Plantas'])
            self.ids_procesados.append(id_origen)

            estado_raw = str(r.get('Estado_Planta_Raw') or '').strip().upper()
            id_estado_planta = MAPA_ESTADO_PLANTA.get(estado_raw)
            if id_estado_planta == -1:
                continue
            if not id_estado_planta:
                self.registrar_rechazo(id_origen, 'Estado_Planta_Raw', estado_raw, 'Estado_Planta_Raw no reconocido')
                continue

            cantidad = _a_int(r.get('Cantidad_Raw'))
            if cantidad is None:
                self.registrar_rechazo(id_origen, 'Cantidad_Raw', r.get('Cantidad_Raw'), 'Cantidad_Raw no numerica o vacia')
                continue

            linea_raw = r.get('Linea_Raw')
            if pd.isna(linea_raw) or str(linea_raw).strip().lower() in ('nan', 'none', ''):
                linea_str = "Sin Línea"
            else:
                linea_str = str(linea_raw).strip()[:100]

            payload.append({
                'ID_Geografia':           r['ID_Geografia'],
                '_id_modulo_catalogo':    r['_id_modulo_catalogo'],
                'ID_Tiempo':              int(r['ID_Tiempo']),
                'ID_Variedad':            int(r['ID_Variedad']),
                'ID_Campana':             obtener_id_campana_anual(r['Fecha_Evento_dt'], self.engine),
                'ID_Estado_Planta':       id_estado_planta,
                'Cantidad':               cantidad,
                'Linea_Raw':              linea_str,
                'Fecha_Evento':           r['Fecha_Evento_dt'],
                'Fecha_Sistema':          pd.Timestamp.now(),
                'id_origen_rastreo':      id_origen,
            })

        # --- PILOTO DE PRUEBA PARA HISTORICO ---
        # Agrupamos por la clave única para sumar Cantidad y evitar duplicados de registros
        # sin línea (o de la misma línea) en el mismo batch.
        agrupado = {}
        for row in payload:
            clave = (
                row['ID_Geografia'],
                row['ID_Tiempo'],
                row['ID_Variedad'],
                row['ID_Estado_Planta'],
                row['Linea_Raw'],
                row.get('ID_Campana')
            )
            if clave not in agrupado:
                agrupado[clave] = row
            else:
                agrupado[clave]['Cantidad'] += row['Cantidad']
                
        payload_agregado = list(agrupado.values())
        return payload_agregado


def cargar_fact_censo_plantas(engine: Engine) -> dict:
    proc = ProcesadorCensoPlantas(engine)

    cols_raw = [
        'Fecha_Raw', 'Campana_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw',
        'Estado_Planta_Raw', 'Cantidad_Raw', 'Linea_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Censo_Plantas'
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_CensoPlantas')

        return proc.finalizar_proceso(contexto)
