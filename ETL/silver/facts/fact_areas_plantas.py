import datetime as _dt
import re
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.homologador import homologar_columna
from mdm.lookup import obtener_id_campana
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact

TABLA_ORIGEN  = 'Bronce.Base_Plantas_Area'
TABLA_DESTINO = 'Silver.Fact_Areas_Plantas'

def _anio_desde_campana(valor) -> int | None:
    if valor is None:
        return None
    txt = str(valor).strip()
    if not txt or txt.lower() == 'nan':
        return None
    m = re.search(r'(\d{4})', txt)
    return int(m.group(1)) if m else None

def _safe_float(v, default=0.0) -> float:
    if v is None:
        return default
    try:
        s = str(v).strip()
        if not s or s.lower() == 'nan':
            return default
        return float(s)
    except (ValueError, TypeError):
        return default

class ProcesadorAreasPlantas(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Base_Plantas_Area')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Variedad', 'ID_Tiempo']
        self.LIMITE_CRITICO = 101.0
        self.LIMITE_ERROR = 101.0

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        import datetime as _dt
        # 1. Derivar Fecha_Evento de forma vectorizada
        today_year = _dt.date.today().year
        df['_Deriv_Fecha_Temp'] = df['Campana_Raw'].map(lambda x: _dt.date(_anio_desde_campana(x) or today_year, 7, 1))

        # 2. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Deriv_Fecha_Temp',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo=None,
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            dominio_fecha='comun'
        )

        if df_resolved.empty:
            return []

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Base_Plantas_Area'])
            self.ids_procesados.append(id_origen)

            payload.append({
                'ID_Geografia':           r['ID_Geografia'],
                '_id_modulo_catalogo':    r['_id_modulo_catalogo'],
                'ID_Variedad':            int(r['ID_Variedad']),
                'ID_Tiempo':              int(r['ID_Tiempo']),
                'Cantidad_Plantas':       _safe_float(r.get('Plantas_Raw')),
                'Area_ha':                _safe_float(r.get('Area_Raw')),
                'Estado_DQ':              'OK',
                'Fecha_Evento':           r['Fecha_Evento_dt'],
                'Fecha_Sistema':          pd.Timestamp.now(),
                'id_origen_rastreo':      id_origen,
            })
        return payload


def cargar_fact_areas_plantas(engine: Engine) -> dict:
    proc = ProcesadorAreasPlantas(engine)
    
    cols_raw = [
        'Campana_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw',
        'Area_Raw', 'Plantas_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    # Dedup: elimina solo duplicados exactos incluyendo Campana_Raw en la clave,
    # para no colapsar registros legítimos de distintas campañas en uno solo.
    cols_dedup = [c for c in ['Campana_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Variedad_Raw'] if c in df.columns]
    if cols_dedup:
        df = df.drop_duplicates(subset=cols_dedup, keep='first')

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Base_Plantas_Area'
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_AreasPlantas')

        return proc.finalizar_proceso(contexto)
