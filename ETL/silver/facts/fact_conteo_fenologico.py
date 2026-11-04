"""
fact_conteo_fenologico.py
=========================
Carga Silver.Fact_Conteo_Fenologico desde Bronce.Conteo_Fruta.

Soporta dos layouts de origen:
1) Layout largo: Estado_Raw + Cantidad_Organos_Raw poblados.
2) Layout ancho: valores en Valores_Raw (Botones/Flores/Fases/etc.) y Punto_Raw.
"""

import re
import unicodedata
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo, parsear_fecha
from mdm.lookup import obtener_id_estado_fenologico
from mdm.homologador import homologar_columna
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    finalizar_resumen_fact as _finalizar_resumen_fact,
    parsear_valores_raw as _parsear_valores_raw,
)


TABLA_ORIGEN = 'Bronce.Conteo_Fruta'
TABLA_DESTINO = 'Silver.Fact_Conteo_Fenologico'

MAPA_ESTADOS_WIDE = {
    'Botones_Florales_Raw': 'Boton Floral',
    'Flores_Raw': 'Flor',
    'Bayas_Pequenas_Raw': 'Pequena',
    'Bayas_Grandes_Verdes_Raw': 'Verde',
    'Fase1_Raw': 'Inicio F1',
    'Fase2_Raw': 'Inicio F2',
    'Bayas_Cremas_Raw': 'Crema',
    'Bayas_Maduras_Raw': 'Madura',
    'Bayas_Cosechables_Raw': 'Cosechable',
}

SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Conteo_Fenologico (
        ID_Geografia, ID_Tiempo, ID_Variedad,
        ID_Personal, ID_Estado_Fenologico,
        Cantidad_Organos, Plantas_Productivas, Plantas_No_Productivas,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_tiempo, :id_variedad,
        :id_personal, :id_estado,
        :cantidad, :plantas_prod, :plantas_noprod,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _normalizar_tipo_evaluacion(valor) -> str:
    texto = str(valor or '').strip()
    if not texto:
        return ''
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.casefold()
    texto = re.sub(r'[^a-z0-9]+', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def _es_evaluacion_compatible_con_conteo(valor) -> bool:
    """
    Acepta filas del layout real de conteo de flores, incluyendo variantes
    operativas observadas en el Excel de campo.

    Casos validados:
    - CONTEO DE FLORES
    - ENSAYO DE CONTEO
    - PODA GENERAL

    Si la fuente no trae evaluacion, conserva compatibilidad hacia atras.
    """
    normalizado = _normalizar_tipo_evaluacion(valor)
    if not normalizado:
        return True
    if 'conteo' in normalizado or 'fenolog' in normalizado:
        return True
    if normalizado == 'poda general':
        return True
    return False


def _normalizar_cantidad(valor) -> int:
    try:
        return int(float(str(valor)))
    except (ValueError, TypeError):
        return 0


def _a_entero_nulo(valor) -> int | None:
    try:
        if valor is None or str(valor).strip() in ('', 'None', 'nan', 'NULL'):
            return None
        return int(float(str(valor)))
    except (ValueError, TypeError):
        return None


def _extraer_estados_desde_fila(fila) -> list[tuple[str, int]]:
    estado_raw = fila.get('Estado_Raw')
    cantidad_raw = fila.get('Cantidad_Organos_Raw')

    if estado_raw is not None and str(estado_raw).strip() and cantidad_raw is not None and str(cantidad_raw).strip():
        return [(str(estado_raw).strip(), _normalizar_cantidad(cantidad_raw))]

    valores = _parsear_valores_raw(fila.get('Valores_Raw'))
    estados: list[tuple[str, int]] = []
    
    # Mapeo unificado para soportar tanto columnas físicas del nuevo layout como las llaves de Valores_Raw antiguas
    mapeo_dual = {
        'Boton Floral': ['BotonesFlorales_Raw', 'Botones_Florales_Raw'],
        'Flor': ['Flores_Raw', 'Flores_Raw'],
        'Pequena': ['BayasPequenas_Raw', 'Bayas_Pequenas_Raw'],
        'Verde': ['BayasGrandes_Raw', 'Bayas_Grandes_Verdes_Raw'],
        'Inicio F1': ['Fase1_Raw', 'Fase1_Raw'],
        'Inicio F2': ['Fase2_Raw', 'Fase2_Raw'],
        'Crema': ['BayasCremas_Raw', 'Bayas_Cremas_Raw'],
        'Madura': ['BayasMaduras_Raw', 'Bayas_Maduras_Raw'],
        'Cosechable': ['BayasCosechables_Raw', 'Bayas_Cosechables_Raw'],
        'Yema Hinchada': ['YemasActivadas_Raw', 'Yemas_Activadas_Raw', 'YemasHinchadas_Raw', 'Yemas_Hinchadas_Raw', 'Yema_Hinchada_Raw'],
    }

    for nombre_estado, claves in mapeo_dual.items():
        cantidad_val = None
        for c in claves:
            v = fila.get(c) if c in fila else None
            if pd.notna(v) and str(v).strip() != '':
                cantidad_val = v
                break

        if cantidad_val is None:
            for c in claves:
                v = valores.get(c)
                if pd.notna(v) and str(v).strip() != '':
                    cantidad_val = v
                    break

        if cantidad_val is not None:
            cantidad = _normalizar_cantidad(cantidad_val)
            estados.append((nombre_estado, cantidad))
            
    return estados


class ProcesadorConteoFenologico(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Conteo_Fruta')
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Estado_Fenologico', 'Punto']
        self.columna_tiebreaker_timestamp = 'Fecha_Registro'

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # Pre-vectorización: castea columnas numéricas a float (NaN-aware),
        # evitando que 'nan' literal contamine los inserts a temp tables.
        cols_num = ('Punto_Raw', 'PlantasProductivas_Raw', 'PlantasNoProductivas_Raw',
                    'Cantidad_Organos_Raw', 'BotonesFlorales_Raw', 'Flores_Raw',
                    'BayasPequenas_Raw', 'BayasGrandes_Raw', 'Fase1_Raw', 'Fase2_Raw',
                    'BayasCremas_Raw', 'BayasMaduras_Raw', 'BayasCosechables_Raw',
                    'YemasActivadas_Raw', 'Muestras_Raw')
        for c in cols_num:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')

        # 1. Filtrar evaluaciones compatibles vectorialmente
        mask_compat = df['Tipo_Evaluacion_Raw'].map(_es_evaluacion_compatible_con_conteo)
        df_incompat = df[~mask_compat]
        for idx, r in df_incompat.iterrows():
            id_orig = int(r['ID_Conteo_Fruta'])
            tipo_eval = r.get('Tipo_Evaluacion_Raw')
            self.registrar_rechazo(id_orig, 'Tipo_Evaluacion_Raw', tipo_eval, 'Evaluacion no compatible con Fact_Conteo_Fenologico')

        df_compat = df[mask_compat]
        if df_compat.empty:
            return []

        # 2. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df_compat,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo='Fundo_Raw',
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_dni='Evaluador_Raw',
            col_sector='Sector_Raw',
            dominio_fecha='conteo_fenologico'
        )

        if df_resolved.empty:
            return []

        payload = []
        cache_estado: dict = {}
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Conteo_Fruta'])
            valores_dict = None

            estados_cantidades = _extraer_estados_desde_fila(r)
            if not estados_cantidades:
                self.registrar_rechazo(id_origen, 'Valores_Raw', r.get('Valores_Raw'), 'No se encontraron estados fenologicos/cantidades en fila')
                continue

            # Extracción robusta de Plantas_Productivas y Plantas_No_Productivas
            plantas_prod_val = None
            if 'PlantasProductivas_Raw' in r and r.get('PlantasProductivas_Raw') is not None and str(r.get('PlantasProductivas_Raw')).strip() != '':
                plantas_prod_val = r.get('PlantasProductivas_Raw')
            else:
                valores_dict = _parsear_valores_raw(r.get('Valores_Raw'))
                plantas_prod_val = valores_dict.get('PlantasProductivas_Raw') or valores_dict.get('Plantas_Productivas') or valores_dict.get('PlantasProductivas')

            plantas_noprod_val = None
            if 'PlantasNoProductivas_Raw' in r and r.get('PlantasNoProductivas_Raw') is not None and str(r.get('PlantasNoProductivas_Raw')).strip() != '':
                plantas_noprod_val = r.get('PlantasNoProductivas_Raw')
            else:
                if valores_dict is None:
                    valores_dict = _parsear_valores_raw(r.get('Valores_Raw'))
                plantas_noprod_val = valores_dict.get('PlantasNoProductivas_Raw') or valores_dict.get('Plantas_No_Productivas') or valores_dict.get('PlantasNoProductivas')

            plantas_productivas = _a_entero_nulo(plantas_prod_val)
            plantas_no_productivas = _a_entero_nulo(plantas_noprod_val)

            punto_val = _a_entero_nulo(r.get('Punto_Raw'))
            if punto_val is None:
                if valores_dict is None:
                    valores_dict = _parsear_valores_raw(r.get('Valores_Raw'))
                punto_val = _a_entero_nulo(valores_dict.get('Punto_Raw') or valores_dict.get('Punto'))
            if punto_val is None:
                punto_val = 0
            fecha_registro = parsear_fecha(r.get('Fecha_Registro_Raw'))

            filas_expandidas = 0
            for estado_raw, cantidad in estados_cantidades:
                if estado_raw in cache_estado:
                    id_estado = cache_estado[estado_raw]
                else:
                    id_estado = obtener_id_estado_fenologico(estado_raw, self.engine)
                    cache_estado[estado_raw] = id_estado
                if not id_estado:
                    self.resumen['cuarentena'].append({
                        'columna': 'Estado_Raw',
                        'valor': estado_raw,
                        'motivo': 'Estado fenologico no reconocido',
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
                    'Cantidad_Organos':       cantidad,
                    'Plantas_Productivas':    plantas_productivas,
                    'Plantas_No_Productivas': plantas_no_productivas,
                    'Punto':                  punto_val,
                    'Fecha_Evento':           r['Fecha_Evento_dt'],
                    'Fecha_Registro':         fecha_registro,
                    'Estado_DQ':              'OK',
                    'id_origen_rastreo':      id_origen,
                })
                filas_expandidas += 1

            if filas_expandidas > 0:
                self.ids_procesados.append(id_origen)
            else:
                self.registrar_rechazo(id_origen, 'Estado_Raw', None, 'Ningún estado fenologico reconocido en la fila')

        return payload


def cargar_fact_conteo_fenologico(engine: Engine) -> dict:
    proc = ProcesadorConteoFenologico(engine)

    cols_raw = [
        'Fecha_Raw', 'Fundo_Raw', 'Sector_Raw', 'Modulo_Raw', 'Turno_Raw',
        'Valvula_Raw', 'Variedad_Raw', 'Evaluador_Raw', 'Color_Cinta_Raw',
        'Estado_Raw', 'Cantidad_Organos_Raw', 'Tipo_Evaluacion_Raw',
        'Valores_Raw', 'Fecha_Registro_Raw',
        'Punto_Raw', 'BotonesFlorales_Raw', 'Flores_Raw', 'BayasPequenas_Raw',
        'BayasGrandes_Raw', 'Fase1_Raw', 'Fase2_Raw', 'BayasCremas_Raw',
        'BayasMaduras_Raw', 'BayasCosechables_Raw', 'YemasActivadas_Raw',
        'PlantasProductivas_Raw', 'PlantasNoProductivas_Raw', 'Muestras_Raw'
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        df, cuarentenas_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Conteo_Fruta',
        )
        proc.resumen['cuarentena'].extend(cuarentenas_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_ConteoFenologico')

        return proc.finalizar_proceso(contexto)
