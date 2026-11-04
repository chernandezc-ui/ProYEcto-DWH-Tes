"""
fact_peladas.py
===============
Carga Silver.Fact_Peladas desde Bronce.Peladas.

Grain: Fecha + Geo + Variedad + Punto
Validación crítica: Muestras >= 1 (evita división por cero)
"""

from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from dq.validador import validar_muestras
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
    parsear_valores_raw as _parsear_valores_raw,
)
from utils.tipos import a_entero, obtener_valor_raw as _obtener_valor_raw_util


TABLA_ORIGEN  = 'Bronce.Peladas'
TABLA_DESTINO = 'Silver.Fact_Peladas'


def _a_int(valor, default: int = 0) -> int:
    n = a_entero(valor)
    return max(0, n) if n is not None else default


def _obtener_campo(fila: pd.Series, nombre_columna: str, valores_raw: dict) -> Any:
    """Retorna el valor de la columna directa si existe, sino busca en valores_raw."""
    valor = fila.get(nombre_columna)
    if valor is not None and str(valor).strip() not in ('', 'None', 'nan'):
        return valor
    return _obtener_valor_raw_util(fila, nombre_columna, valores_raw)


class ProcesadorPeladas(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'Punto', 'ID_Estado_Fenologico']

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        from mdm.lookup import obtener_id_estado_fenologico

        mapeo_dual = {
            'Boton Floral': ['BotonesFlorales_Raw', 'Botones_Florales_Raw'],
            'Flor': ['Flores_Raw', 'Flores_Raw'],
            'Pequena': ['BayasPequenas_Raw', 'Bayas_Pequenas_Raw'],
            'Verde': ['BayasGrandes_Raw', 'Bayas_Grandes_Verdes_Raw', 'BayasGrandes_Raw'],
            'Inicio F1': ['Fase1_Raw', 'Fase1_Raw'],
            'Inicio F2': ['Fase2_Raw', 'Fase2_Raw'],
            'Crema': ['BayasCremas_Raw', 'Bayas_Cremas_Raw'],
            'Madura': ['BayasMaduras_Raw', 'Bayas_Maduras_Raw'],
            'Cosechable': ['BayasCosechables_Raw', 'Bayas_Cosechables_Raw'],
            'Yema Hinchada': ['YemasActivadas_Raw', 'Yemas_Activadas_Raw', 'YemasHinchadas_Raw', 'Yemas_Hinchadas_Raw', 'Yema_Hinchada_Raw'],
        }

        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)

        # 2. Obtener series de columnas derivadas usando _vectorized_get_raw_val
        fecha_s = self._vectorized_get_raw_val(df, v_raw_df, 'Fecha_Raw')
        fundo_s = self._vectorized_get_raw_val(df, v_raw_df, 'Fundo_Raw')
        modulo_s = self._vectorized_get_raw_val(df, v_raw_df, 'Modulo_Raw')
        turno_s = self._vectorized_get_raw_val(df, v_raw_df, 'Turno_Raw')
        valvula_s = self._vectorized_get_raw_val(df, v_raw_df, 'Valvula_Raw')
        dni_s = self._vectorized_get_raw_val(df, v_raw_df, 'DNI_Raw')
        muestras_s = self._vectorized_get_raw_val(df, v_raw_df, 'Muestras_Raw')
        punto_s = self._vectorized_get_raw_val(df, v_raw_df, 'Punto_Raw')
        plantas_prod_s = self._vectorized_get_raw_val(df, v_raw_df, 'PlantasProductivas_Raw')
        plantas_noprod_s = self._vectorized_get_raw_val(df, v_raw_df, 'PlantasNoProductivas_Raw')

        df['_Fecha_Temp'] = fecha_s
        df['_Fundo_Temp'] = fundo_s
        df['_Modulo_Temp'] = modulo_s
        df['_Turno_Temp'] = turno_s
        df['_Valvula_Temp'] = valvula_s
        df['_DNI_Temp'] = dni_s

        # 3. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Fecha_Temp',
            col_modulo='_Modulo_Temp',
            col_variedad='Variedad_Canonica',
            col_fundo='_Fundo_Temp',
            col_turno='_Turno_Temp',
            col_valvula='_Valvula_Temp',
            col_dni='_DNI_Temp',
            dominio_fecha='peladas'
        )

        if df_resolved.empty:
            return []

        v_raw_resolved = v_raw_df.loc[df_resolved.index]

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Peladas'])
            v_r = v_raw_resolved.loc[idx]

            # Validar muestras
            m_val = muestras_s.loc[idx]
            muestras, error_muestras = validar_muestras(m_val)
            if error_muestras:
                self.registrar_rechazo(
                    id_origen,
                    columna=error_muestras.get('columna', 'Muestras'),
                    valor=error_muestras.get('valor'),
                    motivo=error_muestras.get('motivo', 'Muestras invalidas'),
                    tipo_regla='DQ',
                    severidad=error_muestras.get('severidad', 'ALTO'),
                )
                continue

            try:
                p_val = punto_s.loc[idx]
                punto = int(float(str(p_val or 1)))
            except (ValueError, TypeError):
                punto = 1

            plantas_prod = _a_int(plantas_prod_s.loc[idx])
            plantas_noprod = _a_int(plantas_noprod_s.loc[idx])

            estados_encontrados = []
            for nombre_estado, claves in mapeo_dual.items():
                cantidad_val = None
                for c in claves:
                    if c in r.index and r[c] is not None and str(r[c]).strip() != '':
                        cantidad_val = r[c]
                        break
                if cantidad_val is None:
                    for c in claves:
                        if c in v_r.index and v_r[c] is not None and str(v_r[c]).strip() != '':
                            cantidad_val = v_r[c]
                            break
                if cantidad_val is not None:
                    try:
                        cantidad = int(float(str(cantidad_val)))
                    except (ValueError, TypeError):
                        cantidad = 0
                    estados_encontrados.append((nombre_estado, cantidad))

            if not estados_encontrados:
                self.registrar_rechazo(id_origen, 'Valores_Raw', r.get('Valores_Raw'), 'No se encontraron estados fenologicos en la pelada')
                continue

            filas_expandidas = 0
            for estado_raw, cantidad in estados_encontrados:
                id_estado = obtener_id_estado_fenologico(estado_raw, self.engine)
                if not id_estado:
                    self.resumen['cuarentena'].append({
                        'columna': 'Estado_Raw',
                        'valor': estado_raw,
                        'motivo': 'Estado fenologico no reconocido en peladas',
                        'severidad': 'ALTO',
                        'id_registro_origen': id_origen,
                    })
                    continue

                payload.append({
                    'ID_Geografia':           r['ID_Geografia'],
                    '_id_modulo_catalogo':    r['_id_modulo_catalogo'],
                    'ID_Tiempo':              int(r['ID_Tiempo']),
                    'ID_Variedad':            int(r['ID_Variedad']),
                    'ID_Personal':            int(r['ID_Personal']),
                    'ID_Estado_Fenologico':   id_estado,
                    'Punto':                  punto,
                    'Cantidad':               cantidad,
                    'Muestras':               muestras,
                    'Plantas_Productivas':    plantas_prod,
                    'Plantas_No_Productivas': plantas_noprod,
                    'Fecha_Evento':           r['Fecha_Evento_dt'],
                    'Estado_DQ':              'OK',
                    'id_origen_rastreo':      id_origen,
                })
                filas_expandidas += 1

            if filas_expandidas > 0:
                self.ids_procesados.append(id_origen)

        return payload


def cargar_fact_peladas(engine: Engine) -> dict:
    proc = ProcesadorPeladas(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw',
        'Variedad_Raw', 'DNI_Raw', 'Evaluador_Raw', 'Punto_Raw', 'Muestras_Raw',
        'BotonesFlorales_Raw', 'Flores_Raw', 'BayasPequenas_Raw', 'BayasGrandes_Raw',
        'Fase1_Raw', 'Fase2_Raw', 'BayasCremas_Raw', 'BayasMaduras_Raw',
        'BayasCosechables_Raw', 'YemasActivadas_Raw', 'PlantasProductivas_Raw', 'PlantasNoProductivas_Raw',
        'Valores_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Peladas'
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Peladas')

        return proc.finalizar_proceso(contexto)
