"""
cargador.py
===========
Lee archivos Excel de campo e inserta en Bronce como NVARCHAR raw.
Aplica validacion de layout critico cuando la operacion lo exige.
"""

import json
import shutil
import tempfile
import re
import unicodedata
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from bronce.rutas import (
    CARPETA_PROCESADOS,
    CARPETA_RECHAZADOS,
    listar_carpetas_con_archivos,
)
from config.conexion import obtener_engine
from auditoria.log import registrar_inicio, registrar_fin


_CACHE_COLUMNAS_BRONCE: dict[str, set[str]] = {}


_FIRMAS_LAYOUT_CRITICO: dict[str, dict[str, Any]] = {
    'Bronce.Floracion': {
        'ruta_canonica': 'evaluacion_vegetativa',
        'columnas_obligatorias': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Evaluacion_Raw',
            'N_Plantas_Evaluadas_Raw',
            'N_Plantas_en_Floracion_Raw',
        },
        'columnas_incompatibles': {
            'Altura_Raw',
            'Tallos_basales_Raw',
            'Tallos_basales_nuevos_Raw',
            'Brotes_Generales_1_Raw',
            'Brotes_Generales_2_Raw',
            'Brotes_Generales_3_Raw',
            'Brotes_Generales_4_Raw',
            'Brotes_Productivos_Totales_Raw',
            'Brotes_Productivos_1_Raw',
            'Brotes_Productivos_2_Raw',
            'Brotes_Productivos_3_Raw',
            'Brotes_Productivos_4_Raw',
            'Diametro_brote1_Raw',
            'Diametro_brote2_Raw',
        },
        'motivo': (
            'El layout recibido no corresponde al fact actual de Evaluacion Vegetativa. '
            'Faltan columnas de plantas y aparecen metricas de brotes/altura/diametro.'
        ),
    },
    'Bronce.Fisiologia': {
        'ruta_canonica': 'fisiologia',
        'columnas_obligatorias': {
            'Fecha_Raw',
            'Modulo_Raw',
            'Variedad_Raw',
            'Tercio_Raw',
            'Hinchadas_Raw',
            'Productivas_Raw',
            'Total_Org_Raw',
        },
        'columnas_geo_alternativas': (
            {'Fundo_Raw'},
            {'Turno_Raw', 'Valvula_Raw'},
        ),
        'columnas_brote_alternativas': (
            {'Brote_Raw'},
            {'BrotesProd_Raw'},
        ),
        'columnas_incompatibles': {
            'DNI_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Evaluacion_Raw',
            'Altura_Raw',
            'Tallos_basales_Raw',
            'Tallos_basales_nuevos_Raw',
            'Brotes_Generales_1_Raw',
            'Brotes_Generales_2_Raw',
            'Brotes_Generales_3_Raw',
            'Brotes_Generales_4_Raw',
            'Brotes_Productivos_Totales_Raw',
            'Brotes_Productivos_1_Raw',
            'Brotes_Productivos_2_Raw',
            'Brotes_Productivos_3_Raw',
            'Brotes_Productivos_4_Raw',
            'Diametro_brote1_Raw',
            'Diametro_brote2_Raw',
        },
        'motivo': (
            'El layout recibido no corresponde al fact actual de Fisiologia. '
            'Se detectaron columnas incompatibles o faltan componentes minimos de geografia/biologia para el fact.'
        ),
        'rechazar_por_faltantes': True,
    },
}

_FIRMAS_RUTA_SUGERIDA: dict[str, dict[str, Any]] = {
    'peladas': {
        'tabla_destino': 'Bronce.Peladas',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Tipo_Evaluacion_Raw',
            'Punto_Raw',
            'Variedad_Raw',
            'BotonesFlorales_Raw',
            'Flores_Raw',
            'BayasPequenas_Raw',
            'BayasGrandes_Raw',
            'Fase1_Raw',
            'Fase2_Raw',
            'BayasCremas_Raw',
            'BayasMaduras_Raw',
            'BayasCosechables_Raw',
            'PlantasProductivas_Raw',
            'PlantasNoProductivas_Raw',
            'Muestras_Raw',
        },
    },
    'induccion_floral': {
        'tabla_destino': 'Bronce.Induccion_Floral',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Tipo_Evaluacion_Raw',
            'PlantasPorCama_Raw',
            'PlantasConInduccion_Raw',
            'BrotesConInduccion_Raw',
            'BrotesTotales_Raw',
            'BrotesConFlor_Raw',
        },
    },
    'tasa_crecimiento_brotes': {
        'tabla_destino': 'Bronce.Tasa_Crecimiento_Brotes',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Condicion_Raw',
            'Estado_Vegetativo_Raw',
            'Tipo_Tallo_Raw',
            'Ensayo_Raw',
            'Medida_Raw',
            'Fecha_Poda_Aux_Raw',
            'Campana_Raw',
            'Tipo_Evaluacion_Raw',
        },
    },
    'evaluacion_vegetativa': {
        'tabla_destino': 'Bronce.Floracion',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Evaluacion_Raw',
            'N_Plantas_Evaluadas_Raw',
            'N_Plantas_en_Floracion_Raw',
        },
    },
    'evaluacion_pesos': {
        'tabla_destino': 'Bronce.Evaluacion_Pesos',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Variedad_Raw',
            'BayasPequenas_Raw',
            'PesoBayasPequenas_Raw',
            'Cosechables_Raw',
            'PesoCosechables_Raw',
        },
    },
    'evaluacion_calidad_poda': {
        'tabla_destino': 'Bronce.Evaluacion_Calidad_Poda',
        'columnas_clave': {
            'Fecha_Raw',
            'Fundo_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Variedad_Raw',
            'Tipo_Evaluacion_Raw',
            'TallosPlanta_Raw',
            'LongitudTallo_Raw',
            'DiametroTallo_Raw',
            'RamillaPlanta_Raw',
            'ToconesPlanta_Raw',
            'CortesDefectuosos_Raw',
            'AlturaPoda_Raw',
        },
    },
    'conteo_fruta': {
        'tabla_destino': 'Bronce.Conteo_Fruta',
        'columnas_clave': {
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Tipo_Evaluacion_Raw',
            'Punto_Raw',
            'Variedad_Raw',
            'BotonesFlorales_Raw',
            'Flores_Raw',
            'BayasPequenas_Raw',
            'BayasGrandes_Raw',
            'Fase1_Raw',
            'Fase2_Raw',
            'BayasCremas_Raw',
            'BayasMaduras_Raw',
            'BayasCosechables_Raw',
            'PlantasProductivas_Raw',
            'PlantasNoProductivas_Raw',
            'Muestras_Raw',
        },
    },
}


# Mapeo de nombres de columnas comunes del Excel a nombres estándar del ETL.
# Se aplica DESPUÉS de reemplazar espacios por _ y eliminar acentos.
# Clave : nombre ya sin acentos/espacios (sin _Raw)
# Valor : nombre esperado por los scripts Silver (sin _Raw)
_ALIAS_COLUMNAS: dict[str, str] = {
    # Fechas
    'Fecha_de_evaluacion':        'Fecha',
    'Fecha_de_evaluaci_n':        'Fecha',
    'Fecha_evaluacion':           'Fecha',
    'Fecha':                      'Fecha',
    'fecha':                      'Fecha',
    'FECHA':                      'Fecha',
    'FECHAEVALUACION':            'Fecha',
    # Fecha de subida
    'Fecha_de_subida':            'Fecha_Subida',
    'FechaSubida':                'Fecha_Subida',
    'FECHASUBIDA':                'Fecha_Subida',
    'FECHAREGISTRO':              'Fecha_Registro',
    # Timestamp del evento de campo en "Conteo frutos" (columna "Registro")
    'Registro':                   'Fecha_Registro_Raw',
    'REGISTRO':                   'Fecha_Registro_Raw',
    'registro':                   'Fecha_Registro_Raw',
    'Fecha_de_registro':          'Fecha_Registro',
    # Fundo
    'Fundo':                      'Fundo',
    'fundo':                      'Fundo',
    # Modulo
    'Modulo':                     'Modulo',
    'modulo':                     'Modulo',
    'MODULO':                     'Modulo',
    'M':                          'Modulo',
    # Valvula
    'Valvula':                    'Valvula',
    'valvula':                    'Valvula',
    'VALVULA':                    'Valvula',
    'NROVALVULA':                 'Valvula',
    'Cama':                       'Cama',
    'N_cama':                     'Cama',
    'N_de_cama':                  'Cama',
    # Turno
    'Turno':                      'Turno',
    'turno':                      'Turno',
    'TURNO':                      'Turno',
    'T':                          'Turno',
    # Variedad
    'Variedad':                   'Variedad',
    'variedad':                   'Variedad',
    'VARIEDAD':                   'Variedad',
    'VAR':                        'Variedad',
    # Evaluacion
    'Evaluacion':                 'Evaluacion',
    'evaluacion':                 'Evaluacion',
    'Tipo_de_Evaluacion':         'Tipo_Evaluacion',
    # DNI / Personal
    'DNI':                        'DNI',
    'dni':                        'DNI',
    'USUARIO':                    'Evaluador',
    'USUARIOEVALUADOR':           'Evaluador',
    'EVALUADOR':                  'Evaluador',
    'Nombres':                    'Nombres',
    'Nombre':                     'Nombres',
    'Evaluador':                  'Evaluador',
    # Hora
    'Hora':                       'Hora',
    'HORA':                       'Hora',
    # Sector
    'Sector':                     'Sector',
    'sector':                     'Sector',
    'SECTOR':                     'Sector',
    # Clima
    'T_Max':                      'TempMax',
    'T_Min':                      'TempMin',
    'HUMEDAD_RELATIVA':           'Humedad',
    'RADIACION_SOLAR':            'Radiacion',
    'DVP_Real':                   'VPD',
    'DVP_PROMETEO':               'VPD',
    'Temp_Exterior_C':            'Temp_Exterior',
    'Temp_Maxima_C':              'Temp_Maxima',
    'Temp_Minima_C':              'Temp_Minima',
    'Punto_Rocio_C':              'Punto_Rocio',
    'Temperatura_Exterior':       'Temp_Exterior',
    'Temperatura_Maxima':         'Temp_Maxima',
    'Temperatura_Minima':         'Temp_Minima',
    'Punto_de_Rocio':             'Punto_Rocio',
    'Humedad_Externa':            'Humedad_Externa',
    'Velocida_Max_km_hr':         'Velocidad_Max_KmH',
    'Lluvia_mm':                  'Lluvia',
    'Radiacion_Solar_w_m2':       'Radiacion_Solar',
    'Indice_Rayos_UV_F7':         'Indice_UV',
    'Evapotranspiracion_mm':      'Evapotranspiracion',
    'Indice_de_Calor':            'Indice_Calor',
    'Intensidad_de_Lluvia_mm_hr': 'Intensidad_Lluvia',
    'Grados_Dia':                 'Grados_Dia',
    'Velocidad_Max_m_s':          'Velocidad_Max_Ms',
    # Tareos
    'DNIRESPONSABLE':             'DNIResponsable',
    'DNI_RESPONSABLE':            'DNIResponsable',
    'IDPERSONALGENERAL':          'IDPersonalGeneral',
    'ID_PERSONAL_GENERAL':        'IDPersonalGeneral',
    'IDPLANILLA':                 'IDPlanilla',
    'ID_PLANILLA':                'IDPlanilla',
    'IDACTIVIDAD':                'IDActividad',
    'ID_ACTIVIDAD':               'IDActividad',
    'ACTIVIDAD':                  'Actividad',
    'IDLABOR':                    'IDLabor',
    'ID_LABOR':                   'IDLabor',
    'LABOR':                      'Labor',
    'IDTURNO':                    'Turno',
    'ID_TURNO':                   'Turno',
    'HORAS':                      'HorasTrabajadas',
    'HORASTRABAJADAS':            'HorasTrabajadas',
    'AREA':                       'Area',
    # Pesos bayas (Reporte_evaluacion_peso.xlsx) - post normalizacion de acentos
    'Bayas_pequenas':             'BayasPequenas',
    'Peso_bayas_pequenas':        'PesoBayasPequenas',
    'Peso_bayas_pequenas1':       'PesoBayasPequenas2',
    'Peso_bayas_pequenas2':       'PesoBayasPequenas2',
    'Bayas_grandes':              'BayasGrandes',
    'Peso_bayas_grandes':         'PesoBayasGrandes',
    'Bayas_fase_1':               'BayasFase1',
    'Peso_bayas_fase_1':          'PesoBayasFase1',
    'Bayas_fase_2':               'BayasFase2',
    'Peso_bayas_fase_2':          'PesoBayasFase2',
    'Cremas':                     'Cremas',
    'Peso_cremas':                'PesoCremas',
    'Maduras':                    'Maduras',
    'Peso_maduras':               'PesoMaduras',
    'Cosechables':                'Cosechables',
    'Peso_cosechables':           'PesoCosechables',
    'PesoBaya':                   'PesoBaya',
    'CantMuestra':                'CantMuestra',
    # Peladas / Conteos
    'Botones_Florales':           'BotonesFlorales',
    'Flores':                     'Flores',
    'Bayas_Pequenas':             'BayasPequenas',
    'Bayas_Grandes_Verdes':       'BayasGrandes',
    'Bayas_Cremas':               'BayasCremas',
    'Bayas_Maduras':              'BayasMaduras',
    'Bayas_Cosechables':          'BayasCosechables',
    'Plantas_Productivas':        'PlantasProductivas',
    'Plantas_No_Productivas':     'PlantasNoProductivas',
    'Muestra':                    'Muestras',
    'Yemas_Activadas':            'YemasActivadas',
    'TOTAL_ORGANOS':              'Total_Organos',
    'Total_plantas':              'TotalPlantas',
    'Plantas_Proy':               'PlantasProy',
    # Fisiologia
    'TERCIO':                     'Tercio',
    'HINCHADAS':                  'Hinchadas',
    'PRODUCTIVAS':                'Productivas',
    'TOTAL_ORG':                  'Total_Org',
    'BROTE':                      'Brote',
    'BROTESPROD':                 'BrotesProd',
    'BROTESVEG':                  'BrotesVeg',
    # Evaluacion Vegetativa (Historico)
    'piso_1':                     'Piso1_Brotes',
    'piso_2':                     'Piso2_Brotes',
    'piso_3':                     'Piso3_Brotes',
    'piso_4':                     'Piso4_Brotes',
    'piso_5':                     'Piso5_Brotes',
    'piso1':                      'Piso1_Brotes',
    'piso2':                      'Piso2_Brotes',
    'piso3':                      'Piso3_Brotes',
    'piso4':                      'Piso4_Brotes',
    'piso5':                      'Piso5_Brotes',
    'productivos_1':              'Piso1_Productivos',
    'productivos_2':              'Piso2_Productivos',
    'productivos_3':              'Piso3_Productivos',
    'productivos_4':              'Piso4_Productivos',
    'productivos_5':              'Piso5_Productivos',
    'productivos1':               'Piso1_Productivos',
    'productivos2':               'Piso2_Productivos',
    'productivos3':               'Piso3_Productivos',
    'productivos4':               'Piso4_Productivos',
    'productivos5':               'Piso5_Productivos',
    'diametro_piso_1':            'Piso1_Diametro',
    'diametro_piso_2':            'Piso2_Diametro',
    'diametro_piso_3':            'Piso3_Diametro',
    'diametro_piso_4':            'Piso4_Diametro',
    'diametro_piso_5':            'Piso5_Diametro',
    'diametro_piso1':             'Piso1_Diametro',
    'diametro_piso2':             'Piso2_Diametro',
    'diametro_piso3':             'Piso3_Diametro',
    'diametro_piso4':             'Piso4_Diametro',
    'diametro_piso5':             'Piso5_Diametro',
    'diametro1':                  'Piso1_Diametro',
    'diametro2':                  'Piso2_Diametro',
    'diametro3':                  'Piso3_Diametro',
    'diametro4':                  'Piso4_Diametro',
    'diametro5':                  'Piso5_Diametro',
    'semanas_despues_de_poda':    'Semanas_Poda',
    'semanas_despues_poda':       'Semanas_Poda',
    'sem_poda':                   'Semanas_Poda',
    # Ciclos Fenológicos (Excel en mayúsculas + typo "EPATA")
    'ORGANO':                     'Organo',
    'IDESTADOCICLO':              'ID_Estado_Ciclo',
    'EPATA_FENOLOGICA':           'Etapa_Fenologica',
    'COLOR':                      'Color',
    # Fiscalización
    'CARTILLA':                   'Cartilla',
    'DNIFISCALIZADOR':            'DNI_Fiscalizador',
    'FISCALIZADOR':               'Fiscalizador',
    'TFISCALIZADOR':              'Tipo_Fiscalizador',
    'DNIEVALUADOR':               'DNI_Evaluador',
    # Fisiología
    'FECHA_DETALLE':              'Fecha_Detalle',
    # Inducción Floral histórico (pFloreadas/pEvaluadas/bEvaluadas/bFloreadas)
    'pFloreadas':                 'PlantasConInduccion',
    'pEvaluadas':                 'PlantasPorCama',
    'bEvaluadas':                 'BrotesTotales',
    'bFloreadas':                 'BrotesConFlor',
    # New aliases for Inducción Floral - Floración Campaña 2025
    'Plantas_Evaluadas':          'PlantasPorCama',
    'Plantas_con_Floracion':      'PlantasConInduccion',
    'Brotes_con_Induccion_Planta':'BrotesConInduccion',
    'Brotes_Planta':              'BrotesTotales',
    'Flor':                       'BrotesConFlor',
    # Evaluación Vegetativa histórica (orden invertido y plural)
    'Diametro_Piso1':             'Piso1_Diametro',
    'Diametro_Piso2':             'Piso2_Diametro',
    'Diametro_Piso3':             'Piso3_Diametro',
    'Diametro_Piso4':             'Piso4_Diametro',
    'Diametro_Piso5':             'Piso5_Diametro',
    'Brotes_Productivos_Totales': 'Brotes_Productivos_Total',
}


_ALIAS_COLUMNAS_CASEFOLD: dict[str, str] = {
    str(clave).casefold(): valor
    for clave, valor in _ALIAS_COLUMNAS.items()
}


def _alias(col_snake: str) -> str:
    """Retorna el alias estandar si existe, o la misma col_snake."""
    if col_snake in _ALIAS_COLUMNAS:
        return _ALIAS_COLUMNAS[col_snake]
    return _ALIAS_COLUMNAS_CASEFOLD.get(str(col_snake).casefold(), col_snake)


def _normalizar_nombre_columna_base(columna) -> str:
    """
    Canoniza encabezados reales del Excel a una forma estable:
    - quita tildes y variantes Unicode
    - elimina simbolos como °, º, #, /, (), .
    - colapsa separadores repetidos
    - normaliza sufijos numericos tipo ".1" -> "1"
    """
    texto = str(columna).strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace('°', '').replace('º', '').replace('#', 'N')
    texto = re.sub(r'[^0-9A-Za-z]+', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    texto = re.sub(r'_(\d+)$', r'\1', texto)
    return texto


def _consolidar_columnas_duplicadas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Si varios encabezados del Excel terminan en el mismo nombre normalizado,
    conserva una sola columna usando el primer valor no nulo por fila.
    """
    nombres_ordenados = list(dict.fromkeys(str(col) for col in df.columns))
    if len(nombres_ordenados) == len(df.columns):
        return df

    df_consolidado = pd.DataFrame(index=df.index)
    for nombre in nombres_ordenados:
        bloque = df.loc[:, df.columns == nombre]
        if isinstance(bloque, pd.Series):
            df_consolidado[nombre] = bloque
            continue

        bloque = bloque.replace(r'^\s*$', np.nan, regex=True)
        if bloque.shape[1] == 1:
            df_consolidado[nombre] = bloque.iloc[:, 0]
        else:
            df_consolidado[nombre] = bloque.bfill(axis=1).iloc[:, 0]

    return df_consolidado


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas del Excel:
    - Quita espacios / caracteres especiales
    - Aplica alias estándares (Fecha de evaluación → Fecha_Raw)
    - Agrega sufijo _Raw si no lo tiene
    """
    columnas_nuevas = {}
    for col in df.columns:
        col_snake = _normalizar_nombre_columna_base(col)
        col_snake = _alias(col_snake)
        if not col_snake.endswith('_Raw'):
            col_snake = f'{col_snake}_Raw'
        columnas_nuevas[col] = col_snake
    df = df.rename(columns=columnas_nuevas)
    return _consolidar_columnas_duplicadas(df)


def castear_todo_a_texto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte todas las columnas a string (vectorizado).
    None y NaN se convierten a None (NULL en SQL).
    Bronce nunca tipifica — todo es NVARCHAR.
    """
    for col in df.columns:
        mask_nulo = df[col].isna()
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
        )
        df[col] = np.where(mask_nulo, None, df[col])
    return df


def agregar_columnas_sistema(df: pd.DataFrame,
                              nombre_archivo: str) -> pd.DataFrame:
    """
    Agrega columnas de infraestructura que no vienen del Excel:
    - Fecha_Sistema  : timestamp de carga
    - Nombre_Archivo : nombre del archivo fuente
    - Estado_Carga   : estado inicial
    """
    ahora = datetime.now()
    df['Fecha_Sistema'] = ahora
    df['Nombre_Archivo'] = nombre_archivo
    df['Estado_Carga'] = 'CARGADO'
    return df


def insertar_en_bronce(df: pd.DataFrame,
                        tabla: str,
                        engine) -> int:
    """
    Inserta el DataFrame en la tabla Bronce indicada.
    Retorna el número de filas insertadas.

    Usa cursor.fast_executemany directo en vez de pandas.to_sql() para
    garantizar que fast_executemany se aplique efectivamente: to_sql()
    usa su propia ruta de ejecución interna que puede ignorar el flag
    del engine según la versión de pandas/SQLAlchemy.
    """
    if df.empty:
        return 0

    esquema, nombre_tabla = tabla.split('.')
    columnas = list(df.columns)
    placeholders = ', '.join(['?' for _ in columnas])
    cols_quoted   = ', '.join([f'[{c}]' for c in columnas])
    sql = f'INSERT INTO [{esquema}].[{nombre_tabla}] ({cols_quoted}) VALUES ({placeholders})'

    # Convertir a lista de tuplas; sustituir NaN/NaT por None para que
    # pyodbc los envíe como NULL sin lanzar "Invalid parameter type"
    datos: list[tuple] = [
        tuple(None if (v != v or v is None) else v for v in fila)
        for fila in df.itertuples(index=False, name=None)
    ]

    with engine.begin() as conn:
        cursor = conn.connection.cursor()
        try:
            cursor.fast_executemany = True
            cursor.executemany(sql, datos)
        except Exception:
            cursor.fast_executemany = False
            cursor.executemany(sql, datos)
        cursor.close()

    return len(df)


def _crear_copia_temporal_excel(ruta_archivo: Path) -> Path:
    sufijo = f'_{ruta_archivo.name}'
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as temporal:
        ruta_temporal = Path(temporal.name)
    shutil.copy2(str(ruta_archivo), str(ruta_temporal))
    return ruta_temporal


def _ruta_marca_archivo(ruta_archivo: Path) -> Path:
    return ruta_archivo.with_name(f'{ruta_archivo.name}.procesado.json')


def _marcar_archivo_local(ruta_archivo: Path,
                          estado: str,
                          *,
                          destino: Path | None = None,
                          codigo_rechazo: str | None = None) -> Path:
    stat_archivo = ruta_archivo.stat()
    payload = {
        'archivo': ruta_archivo.name,
        'estado': str(estado).upper(),
        'fecha_marca': datetime.now().isoformat(timespec='seconds'),
        'tamano_bytes': int(stat_archivo.st_size),
        'mtime_ns': int(stat_archivo.st_mtime_ns),
    }
    if destino is not None:
        payload['destino'] = str(destino)
    if codigo_rechazo:
        payload['codigo_rechazo'] = str(codigo_rechazo)

    ruta_marca = _ruta_marca_archivo(ruta_archivo)
    ruta_marca.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding='utf-8',
    )
    return ruta_marca


def _archivar_o_marcar(ruta_archivo: Path,
                       destino: Path,
                       *,
                       estado_marca: str,
                       codigo_rechazo: str | None = None) -> tuple[Path, bool]:
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(ruta_archivo), str(destino))
        return destino, False
    except PermissionError:
        shutil.copy2(str(ruta_archivo), str(destino))
        _marcar_archivo_local(
            ruta_archivo,
            estado_marca,
            destino=destino,
            codigo_rechazo=codigo_rechazo,
        )
        return destino, True


def archivar_archivo(ruta_archivo: Path, nombre_carpeta: str) -> tuple[Path, bool]:
    """
    Mueve el archivo procesado a data/procesados/nombre_carpeta/
    con timestamp en el nombre para no sobrescribir.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_nuevo = f'{ruta_archivo.stem}_{timestamp}{ruta_archivo.suffix}'
    destino = CARPETA_PROCESADOS / nombre_carpeta / nombre_nuevo
    return _archivar_o_marcar(
        ruta_archivo,
        destino,
        estado_marca='PROCESADO',
    )


def archivar_archivo_rechazado(ruta_archivo: Path,
                               nombre_carpeta: str,
                               codigo_rechazo: str) -> tuple[Path, bool]:
    """
    Mueve el archivo rechazado a data/rechazados/nombre_carpeta/
    preservando trazabilidad del motivo en el nombre.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    sufijo = str(codigo_rechazo or 'RECHAZADO').strip().replace(' ', '_')
    nombre_nuevo = f'{ruta_archivo.stem}_{sufijo}_{timestamp}{ruta_archivo.suffix}'
    destino = CARPETA_RECHAZADOS / nombre_carpeta / nombre_nuevo
    return _archivar_o_marcar(
        ruta_archivo,
        destino,
        estado_marca='RECHAZADO',
        codigo_rechazo=codigo_rechazo,
    )


def _obtener_columnas_bronce(tabla_destino: str, engine) -> set[str]:
    """
    Devuelve columnas fisicas de la tabla Bronce destino.
    Usa cache en memoria para evitar query repetida en cada archivo.
    """
    if tabla_destino in _CACHE_COLUMNAS_BRONCE:
        return _CACHE_COLUMNAS_BRONCE[tabla_destino]

    esquema, tabla = tabla_destino.split('.')
    consulta = text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :esquema
          AND TABLE_NAME = :tabla
    """)
    with engine.connect() as conexion:
        filas = conexion.execute(
            consulta,
            {'esquema': esquema, 'tabla': tabla},
        ).fetchall()

    columnas = {str(fila[0]) for fila in filas}
    _CACHE_COLUMNAS_BRONCE[tabla_destino] = columnas
    return columnas


def _columnas_normalizadas_excel(
    ruta_archivo: Path,
    header_idx: int,
    sheet_name: str | int = 0,
) -> list[str]:
    """
    Lee solo encabezados del Excel y devuelve nombres normalizados (con _Raw).
    """
    df = pd.read_excel(
        str(ruta_archivo),
        sheet_name=sheet_name,
        header=header_idx,
        dtype=str,
        nrows=0,
        engine='calamine',
    )
    df = normalizar_columnas(df)
    return [str(col) for col in df.columns]


def _extraer_sector_climatico_desde_archivo(ruta_archivo: Path) -> str | None:
    coincidencia = re.search(r'\b([A-Z]\d{2})\b', ruta_archivo.stem.upper())
    return coincidencia.group(1) if coincidencia else None


def _leer_excel_especial(
    ruta_archivo: Path,
    *,
    header_idx: int,
    sheet_name: str | int | None = 0,
) -> pd.DataFrame:
    """
    Lee un Excel con layout conocido, elimina filas/columnas totalmente vacias
    y normaliza encabezados a la convención _Raw del ETL.
    """
    df = pd.read_excel(
        str(ruta_archivo),
        sheet_name=sheet_name,
        header=header_idx,
        dtype=str,
        engine='calamine',
    )
    if df.empty:
        return df

    df = df.dropna(how='all')
    df = df.loc[:, ~df.columns.isna()]
    return normalizar_columnas(df)


def _leer_excel_hojas(
    ruta_archivo: Path,
    hojas_candidatas: tuple[str, ...],
    header_idx: int = 0,
) -> pd.DataFrame:
    """
    Lee y concatena las hojas existentes del listado de candidatas.
    Hojas ausentes se omiten; útil para archivos con BD/BD_LT/Hoja1 etc.
    """
    with pd.ExcelFile(str(ruta_archivo), engine='calamine') as xls:
        existentes = [h for h in hojas_candidatas if h in xls.sheet_names]
    frames = [_leer_excel_especial(ruta_archivo, sheet_name=h, header_idx=header_idx) for h in existentes]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _leer_excel_clima_bd(ruta_archivo: Path) -> pd.DataFrame:
    """
    Lee el layout analitico de clima desde la hoja BD.
    El header real esta en la fila 3 del Excel (header=2).
    """
    df = _leer_excel_especial(ruta_archivo, sheet_name='BD', header_idx=2)
    if df.empty:
        return df

    sector = _extraer_sector_climatico_desde_archivo(ruta_archivo)
    if sector:
        df['Sector_Raw'] = sector

    return df


def _leer_excel_peladas_bd(ruta_archivo: Path) -> pd.DataFrame:
    """
    Lee el layout formal de Peladas.
    Prioriza la hoja BD_LT, que representa el subconjunto operativo de Peladas.
    Si no existe, intenta hoja BD y filtra solo registros con Tipo_Evaluacion = PELADAS.
    """
    with pd.ExcelFile(str(ruta_archivo), engine='calamine') as libro:
        hojas = set(libro.sheet_names)

        if 'BD_LT' in hojas:
            return _leer_excel_especial(ruta_archivo, sheet_name='BD_LT', header_idx=0)

        if 'BD' in hojas:
            df = _leer_excel_especial(ruta_archivo, sheet_name='BD', header_idx=0)
            if df.empty:
                return df

            if 'Tipo_Evaluacion_Raw' in df.columns:
                mascara_peladas = (
                    df['Tipo_Evaluacion_Raw']
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    .eq('PELADAS')
                )
                df = df[mascara_peladas].copy()

            return df

    raise ValueError(
        'Layout de Peladas sin hoja compatible. '
        'Se esperaba BD_LT o BD.'
    )


def _proyectar_dataframe_conteo_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta Conteo de Fruta. Dos layouts:
    - Histórico: hojas 'BD' + 'Hoja1' con encabezados en fila 1 (header=0) → concatena.
    - Reporte diario: hoja única con título en fila 1 (header=1).
    """
    df = _leer_excel_hojas(ruta_archivo, ('BD', 'Hoja1'), header_idx=0)
    if df.empty:
        df = _leer_excel_especial(ruta_archivo, sheet_name=0, header_idx=1)
    if df.empty:
        return df

    columnas_salida = {
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'Fecha_Registro_Raw': _serie_o_nulos(df, 'Fecha_Registro_Raw'),
        'Fecha_Subida_Raw': _serie_o_nulos(df, 'Fecha_Subida_Raw'),
        'DNI_Raw': _serie_o_nulos(df, 'DNI_Raw'),
        'Nombres_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Evaluador_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Fundo_Raw': _serie_o_nulos(df, 'Fundo_Raw'),
        'Sector_Raw': _serie_o_nulos(df, 'Sector_Raw'),
        'Modulo_Raw': _serie_o_nulos(df, 'Modulo_Raw'),
        'Turno_Raw': _serie_o_nulos(df, 'Turno_Raw'),
        'Valvula_Raw': _serie_o_nulos(df, 'Valvula_Raw'),
        'Variedad_Raw': _serie_o_nulos(df, 'Variedad_Raw'),
        'Punto_Raw': _serie_o_nulos(df, 'Punto_Raw'),
        'Tipo_Evaluacion_Raw': _serie_o_nulos(df, 'Evaluacion_Raw'),
        'BotonesFlorales_Raw': _serie_o_nulos(df, 'BotonesFlorales_Raw'),
        'Flores_Raw': _serie_o_nulos(df, 'Flores_Raw'),
        'BayasPequenas_Raw': _serie_o_nulos(df, 'BayasPequenas_Raw'),
        'BayasGrandes_Raw': _serie_o_nulos(df, 'BayasGrandes_Raw'),
        'Fase1_Raw': _serie_o_nulos(df, 'Fase1_Raw'),
        'Fase2_Raw': _serie_o_nulos(df, 'Fase2_Raw'),
        'BayasCremas_Raw': _serie_o_nulos(df, 'BayasCremas_Raw'),
        'BayasMaduras_Raw': _serie_o_nulos(df, 'BayasMaduras_Raw'),
        'BayasCosechables_Raw': _serie_o_nulos(df, 'BayasCosechables_Raw'),
        'YemasActivadas_Raw': _serie_o_nulos(df, 'YemasActivadas_Raw'),
        'PlantasProductivas_Raw': _serie_o_nulos(df, 'PlantasProductivas_Raw'),
        'PlantasNoProductivas_Raw': _serie_o_nulos(df, 'PlantasNoProductivas_Raw'),
        'Muestras_Raw': _serie_o_nulos(df, 'Muestras_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    
    columnas_usadas = set(columnas_salida.keys())
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _proyectar_dataframe_peladas_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta el layout real de Peladas a las columnas fisicas esperadas en Bronce.
    Conserva metadatos adicionales en Valores_Raw para no perder trazabilidad.
    """
    df = _leer_excel_peladas_bd(ruta_archivo)
    if df.empty:
        return df

    columnas_salida = {
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'Fundo_Raw': _serie_o_nulos(df, 'Fundo_Raw'),
        'DNI_Raw': _serie_o_nulos(df, 'DNI_Raw'),
        'Nombres_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Evaluador_Raw': _serie_o_nulos(df, 'Nombres_Raw'),
        'Modulo_Raw': _serie_o_nulos(df, 'Modulo_Raw'),
        'Turno_Raw': _serie_o_nulos(df, 'Turno_Raw'),
        'Valvula_Raw': _serie_o_nulos(df, 'Valvula_Raw'),
        'Tipo_Evaluacion_Raw': _serie_o_nulos(df, 'Tipo_Evaluacion_Raw'),
        'Punto_Raw': _serie_o_nulos(df, 'Punto_Raw'),
        'Variedad_Raw': _serie_o_nulos(df, 'Variedad_Raw'),
        'Muestras_Raw': _serie_o_nulos(df, 'Muestras_Raw'),
        'BotonesFlorales_Raw': _serie_o_nulos(df, 'BotonesFlorales_Raw'),
        'Flores_Raw': _serie_o_nulos(df, 'Flores_Raw'),
        'BayasPequenas_Raw': _serie_o_nulos(df, 'BayasPequenas_Raw'),
        'BayasGrandes_Raw': _serie_o_nulos(df, 'BayasGrandes_Raw'),
        'Fase1_Raw': _serie_o_nulos(df, 'Fase1_Raw'),
        'Fase2_Raw': _serie_o_nulos(df, 'Fase2_Raw'),
        'BayasCremas_Raw': _serie_o_nulos(df, 'BayasCremas_Raw'),
        'BayasMaduras_Raw': _serie_o_nulos(df, 'BayasMaduras_Raw'),
        'BayasCosechables_Raw': _serie_o_nulos(df, 'BayasCosechables_Raw'),
        'YemasActivadas_Raw': _serie_o_nulos(df, 'YemasActivadas_Raw'),
        'PlantasProductivas_Raw': _serie_o_nulos(df, 'PlantasProductivas_Raw'),
        'PlantasNoProductivas_Raw': _serie_o_nulos(df, 'PlantasNoProductivas_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    columnas_usadas = {
        'Fecha_Raw',
        'Fundo_Raw',
        'DNI_Raw',
        'Nombres_Raw',
        'Modulo_Raw',
        'Turno_Raw',
        'Valvula_Raw',
        'Tipo_Evaluacion_Raw',
        'Punto_Raw',
        'Variedad_Raw',
        'Muestras_Raw',
        'BotonesFlorales_Raw',
        'Flores_Raw',
        'BayasPequenas_Raw',
        'BayasGrandes_Raw',
        'Fase1_Raw',
        'Fase2_Raw',
        'BayasCremas_Raw',
        'BayasMaduras_Raw',
        'BayasCosechables_Raw',
        'YemasActivadas_Raw',
        'PlantasProductivas_Raw',
        'PlantasNoProductivas_Raw',
    }
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _serie_o_nulos(df: pd.DataFrame, columna: str) -> pd.Series:
    if columna in df.columns:
        return df[columna]
    return pd.Series([None] * len(df), index=df.index)


def _proyectar_dataframe_clima_bronce(
    ruta_archivo: Path,
    tabla_destino: str,
) -> pd.DataFrame:
    """
    Proyecta el layout BD de clima a las columnas fisicas esperadas en Bronce.
    No depende del alineador generico porque el libro trae muchas metricas analiticas.
    """
    df = _leer_excel_clima_bd(ruta_archivo)
    if df.empty:
        return df

    columnas_base = {
        'Fecha_Raw': _serie_o_nulos(df, 'Fecha_Raw'),
        'Sector_Raw': _serie_o_nulos(df, 'Sector_Raw'),
        'TempMax_Raw': _serie_o_nulos(df, 'TempMax_Raw'),
        'TempMin_Raw': _serie_o_nulos(df, 'TempMin_Raw'),
        'Humedad_Raw': _serie_o_nulos(df, 'Humedad_Raw'),
    }

    if tabla_destino == 'Bronce.Reporte_Clima':
        columnas_base.update({
            'Hora_Raw': _serie_o_nulos(df, 'Hora_Raw'),
            'Precipitacion_Raw': _serie_o_nulos(df, 'Precipitacion_Raw'),
        })
    df_salida = pd.DataFrame(columnas_base, index=df.index)

    columnas_usadas = set(df_salida.columns)
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _proyectar_dataframe_induccion_floral_bronce(ruta_archivo: Path, engine=None) -> pd.DataFrame:
    """
    Proyecta Inducción Floral. Soporta layouts con títulos y filas vacías arriba
    detectando dinámicamente el header en base a la fila que contiene Módulo y Variedad.
    """
    # Detectar la hoja adecuada
    sheet_name = 0
    if engine is not None:
        sheet_name, _ = _detectar_hoja_y_header(ruta_archivo, 'Bronce.Induccion_Floral', engine)
    else:
        # Fallback estático para testing/entornos sin motor DB
        with pd.ExcelFile(str(ruta_archivo), engine='calamine') as xls:
            sheets = xls.sheet_names
        for sh in sheets:
            sh_clean = sh.strip().upper()
            if 'BD INDUCCION' in sh_clean or 'BD INDUCCIÓN' in sh_clean or 'BASE DE DATOS' in sh_clean or sh_clean == 'BD':
                sheet_name = sh
                break

    # Detectar dinámicamente dónde está el header (puede ser fila 0, 1, 2, o más)
    df_raw = pd.read_excel(str(ruta_archivo), sheet_name=sheet_name, header=None, nrows=10, engine='calamine')
    header_idx = 0
    for i, row in df_raw.iterrows():
        fila_str = ' '.join([str(x).upper() for x in row.values])
        if ('MODULO' in fila_str or 'MÓDULO' in fila_str) and any(
            x in fila_str for x in ('VARIEDAD', 'DNI', 'NOMBRES', 'VALVULA', 'PLANTAS', 'DESCRIPCION', 'DESCRIPCI')
        ):
            header_idx = i
            break

    df = _leer_excel_especial(ruta_archivo, header_idx=header_idx, sheet_name=sheet_name)
    if df.empty:
        return df

    # Si tiene Fecha_Raw, es el Reporte Diario (formato estandarizado con fecha por fila)
    if 'Fecha_Raw' in df.columns:
        def _get_col(*col_options: str) -> pd.Series:
            for col in col_options:
                if col in df.columns:
                    return df[col]
            return pd.Series([None] * len(df), index=df.index)

        columnas_salida = {
            'Fecha_Raw':           _get_col('Fecha_Raw'),
            'DNI_Raw':             _get_col('DNI_Raw'),
            'Fecha_Subida_Raw':    _get_col('Fecha_Subida_Raw'),
            'Nombres_Raw':         _get_col('Nombres_Raw', 'Evaluador_Raw'),
            'Evaluador_Raw':       _get_col('Evaluador_Raw', 'Nombres_Raw'),
            'Consumidor_Raw':      _get_col('Consumidor_Raw'),
            'Modulo_Raw':          _get_col('Modulo_Raw', 'Modulo'),
            'Turno_Raw':           _get_col('Turno_Raw', 'Turno'),
            'Valvula_Raw':         _get_col('Valvula_Raw', 'Valvula'),
            'Tipo_Evaluacion_Raw': _get_col('Tipo_de_Evaluacion_Raw', 'Tipo_Evaluacion_Raw', 'Evaluacion_Raw'),
            'Cama_Raw':            _get_col('N_Cama_Raw', 'Cama_Raw'),
            'Descripcion_Raw':     _get_col('Descripcion_Raw'),
            'Variedad_Raw':        _get_col('Variedad_Raw', 'Descripcion_Raw'),
            'PlantasPorCama_Raw':  _get_col('N_Plantas_por_Cama_Raw', 'Plantas_por_Cama_Raw'),
            'PlantasConInduccion_Raw': _get_col('N_Plantas_con_Induccion_Raw', 'Plantas_con_Induccion_Raw'),
            'BrotesConInduccion_Raw':  _get_col('N_Brotes_con_Induccion_Raw', 'Brotes_con_Induccion_Raw'),
            'BrotesTotales_Raw':       _get_col('N_Brotes_Totales_Raw', 'Brotes_Totales_Raw'),
            'BrotesConFlor_Raw':       _get_col('Brotes_con_Flor_Raw'),
        }
        columnas_usadas = {
            'Fecha_Raw',
            'DNI_Raw',
            'Fecha_Subida_Raw',
            'Nombres_Raw',
            'Consumidor_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Evaluacion_Raw',
            'Cama_Raw',
            'N_Cama_Raw',
            'Descripcion_Raw',
            'Plantas_por_Cama_Raw',
            'N_Plantas_por_Cama_Raw',
            'Plantas_con_Induccion_Raw',
            'N_Plantas_con_Induccion_Raw',
            'Brotes_con_Induccion_Raw',
            'N_Brotes_con_Induccion_Raw',
            'Brotes_Totales_Raw',
            'N_Brotes_Totales_Raw',
            'Brotes_con_Flor_Raw',
            'Semana_Raw',
            'Ano_Raw'
        }
        df_salida = pd.DataFrame(columnas_salida, index=df.index)
        columnas_extra = [col for col in df.columns if col not in columnas_usadas]
        if columnas_extra:
            df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)
        return df_salida

    # Si no tiene Fecha_Raw, es el histórico (se alinea con aliases y Valores_Raw de forma estándar)
    return df


def _proyectar_dataframe_tasa_crecimiento_brotes_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta Tasa de Crecimiento. Dos layouts:
    - Histórico (hoja BD_General): nombres alterados (Mod, Tur, Val, EVALUADOR_A) → proyección.
    - Reporte diario: encabezados estándar en fila 2 → mapeo vía aliases.

    Las columnas de detalle de cada medición se colocan en columnas físicas dedicadas:
      Planta_Brote_Raw  <- Ensayo / Planta_Brote del Excel
      Cantidad_Raw      <- Medida del Excel
      Tallo_Raw         <- Tipo_Tallo / Tipo_de_Tallo del Excel
    Esto evita que el pipeline Silver tenga que desempacar Valores_Raw.
    """
    with pd.ExcelFile(str(ruta_archivo), engine='calamine') as xls:
        tiene_bd_general = 'BD_General' in xls.sheet_names

    if not tiene_bd_general:
        # --- Reporte diario (header en fila 2) ---
        df = _leer_excel_especial(ruta_archivo, sheet_name=0, header_idx=1)
        if df.empty:
            return df

        # Resolver columna Planta_Brote: puede venir como Ensayo_Raw o Planta_Brote_Raw
        planta_brote = (
            _serie_o_nulos(df, 'Ensayo_Raw') if 'Ensayo_Raw' in df.columns
            else _serie_o_nulos(df, 'Planta_Brote_Raw')
        )
        # Resolver Medida → Cantidad
        cantidad = (
            _serie_o_nulos(df, 'Medida_Raw') if 'Medida_Raw' in df.columns
            else _serie_o_nulos(df, 'Cantidad_Raw')
        )
        # Resolver Tipo_Tallo
        tallo = (
            _serie_o_nulos(df, 'Tipo_Tallo_Raw') if 'Tipo_Tallo_Raw' in df.columns
            else (_serie_o_nulos(df, 'Tipo_de_Tallo_Raw') if 'Tipo_de_Tallo_Raw' in df.columns
                  else _serie_o_nulos(df, 'Tallo_Raw'))
        )

        columnas_salida = {
            'Fecha_Raw':             _serie_o_nulos(df, 'Fecha_Raw'),
            'Fecha_Registro_Raw':    _serie_o_nulos(df, 'Fecha_Registro_Raw'),
            'Fecha_Subida_Raw':      _serie_o_nulos(df, 'Fecha_Subida_Raw'),
            'DNI_Raw':               _serie_o_nulos(df, 'DNI_Raw'),
            'Evaluador_Raw':         _serie_o_nulos(df, 'Evaluador_Raw'),
            'Nombres_Raw':           _serie_o_nulos(df, 'Nombres_Raw'),
            'Modulo_Raw':            _serie_o_nulos(df, 'Modulo_Raw'),
            'Turno_Raw':             _serie_o_nulos(df, 'Turno_Raw'),
            'Valvula_Raw':           _serie_o_nulos(df, 'Valvula_Raw'),
            'Cama_Raw':              _serie_o_nulos(df, 'Cama_Raw'),
            'Variedad_Raw':          _serie_o_nulos(df, 'Variedad_Raw'),
            'Estado_Vegetativo_Raw': _serie_o_nulos(df, 'Estado_Vegetativo_Raw'),
            'Planta_Brote_Raw':      planta_brote,
            'Cantidad_Raw':          cantidad,
            'Tallo_Raw':             tallo,
            'Evaluacion_Raw':        _serie_o_nulos(df, 'Evaluacion_Raw'),
        }
        columnas_usadas = {
            'Fecha_Raw', 'Fecha_Registro_Raw', 'Fecha_Subida_Raw',
            'DNI_Raw', 'Evaluador_Raw', 'Nombres_Raw',
            'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Cama_Raw',
            'Variedad_Raw', 'Estado_Vegetativo_Raw',
            'Ensayo_Raw', 'Planta_Brote_Raw',
            'Medida_Raw', 'Cantidad_Raw',
            'Tipo_Tallo_Raw', 'Tipo_de_Tallo_Raw', 'Tallo_Raw',
            'Evaluacion_Raw',
        }
        df_salida = pd.DataFrame(columnas_salida, index=df.index)
        columnas_extra = [col for col in df.columns if col not in columnas_usadas]
        if columnas_extra:
            df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)
        return df_salida

    # --- Histórico (hoja BD_General) ---
    df = _leer_excel_especial(ruta_archivo, sheet_name='BD_General', header_idx=1)
    if df.empty:
        return df

    columnas_salida = {
        'Codigo_Origen_Raw':     _serie_o_nulos(df, 'Unnamed0_Raw'),
        'Semana_Raw':            _serie_o_nulos(df, 'Semana_Raw'),
        'Dia_Raw':               _serie_o_nulos(df, 'Dia_Raw'),
        'Fecha_Raw':             _serie_o_nulos(df, 'Fecha_Raw'),
        'DNI_Raw':               _serie_o_nulos(df, 'DNI_Raw'),
        'Evaluador_Raw':         _serie_o_nulos(df, 'EVALUADOR_A_Raw'),
        'Modulo_Raw':            _serie_o_nulos(df, 'Mod_Raw'),
        'Turno_Raw':             _serie_o_nulos(df, 'Tur_Raw'),
        'Valvula_Raw':           _serie_o_nulos(df, 'Val_Raw'),
        'Condicion_Raw':         _serie_o_nulos(df, 'Condicion_Raw'),
        'Estado_Vegetativo_Raw': _serie_o_nulos(df, 'Estado_Vegetativo_Raw'),
        'Variedad_Raw':          _serie_o_nulos(df, 'Variedad_Raw'),
        'Cama_Raw':              _serie_o_nulos(df, 'Cama_Raw'),
        # Columnas físicas dedicadas de Bronce
        'Planta_Brote_Raw':      _serie_o_nulos(df, 'Ensayo_Raw'),
        'Cantidad_Raw':          _serie_o_nulos(df, 'Medida_Raw'),
        'Tallo_Raw':             _serie_o_nulos(df, 'Tipo_de_Tallo_Raw'),
        'Fecha_Poda_Aux_Raw':    _serie_o_nulos(df, 'Fecha_Poda_Aux_Raw'),
        'Campana_Raw':           _serie_o_nulos(df, 'CAMPANA_Raw'),
        'Observacion_Raw':       _serie_o_nulos(df, 'Observacion_Raw'),
        'Tipo_Evaluacion_Raw':   _serie_o_nulos(df, 'Evaluacion_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    columnas_usadas = {
        'Unnamed0_Raw', 'Semana_Raw', 'Dia_Raw', 'Fecha_Raw', 'DNI_Raw',
        'EVALUADOR_A_Raw', 'Mod_Raw', 'Tur_Raw', 'Val_Raw',
        'Condicion_Raw', 'Estado_Vegetativo_Raw', 'Variedad_Raw', 'Cama_Raw',
        'Ensayo_Raw', 'Medida_Raw', 'Tipo_de_Tallo_Raw',
        'Fecha_Poda_Aux_Raw', 'CAMPANA_Raw', 'Observacion_Raw', 'Evaluacion_Raw',
    }
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _proyectar_dataframe_censo_plantas_bronce(ruta_archivo: Path) -> pd.DataFrame:
    import pandas as pd
    # Detectar dinámicamente dónde está el header (puede ser fila 0 o 1)
    df_raw = pd.read_excel(str(ruta_archivo), header=None, nrows=10, engine='calamine')
    header_idx = 0
    for i, row in df_raw.iterrows():
        fila_str = ' '.join([str(x).upper() for x in row.values])
        if 'FECHA' in fila_str and ('VARIEDAD' in fila_str or 'VALVULA' in fila_str or 'VÁLVULA' in fila_str or 'MODULO' in fila_str):
            header_idx = i
            break

    df = _leer_excel_especial(ruta_archivo, sheet_name=0, header_idx=header_idx)
    if df.empty:
        return df

    # Identificar si el Excel ya viene en formato largo (tiene Estado_Planta y Cantidad)
    columnas_lower = {str(c).lower(): c for c in df.columns}
    col_estado_largo = columnas_lower.get('estado_planta_raw') or columnas_lower.get('estado_planta') or columnas_lower.get('estado planta')
    col_cantidad = columnas_lower.get('cantidad_raw') or columnas_lower.get('cantidad')

    if col_estado_largo and col_cantidad:
        # Ya está en formato largo
        if col_estado_largo != 'Estado_Planta_Raw':
            df = df.rename(columns={col_estado_largo: 'Estado_Planta_Raw'})
        if col_cantidad != 'Cantidad_Raw':
            df = df.rename(columns={col_cantidad: 'Cantidad_Raw'})
    else:
        # Formato ancho (Pivoteado). Identificar columnas de estado.
        estados_validos = ('BUENAS', 'REGULARES', 'MALAS', 'MUERTAS', 'HOYOS', 'PLANTAS_VIVAS', 'PLANTAS_MUERTAS', 'TOTAL_PLANTAS')
        col_estado = [c for c in df.columns if str(c).strip().upper().replace('_RAW', '') in estados_validos]
        
        if col_estado:
            id_vars = [c for c in df.columns if c not in col_estado]
            df = df.melt(id_vars=id_vars, value_vars=col_estado, var_name='Estado_Planta_Raw', value_name='Cantidad_Raw')
            df['Estado_Planta_Raw'] = df['Estado_Planta_Raw'].str.replace('_Raw', '', regex=False)
            df = df.dropna(subset=['Cantidad_Raw'])

    df_salida = pd.DataFrame()
    df_salida['Fecha_Raw'] = _serie_o_nulos(df, 'Fecha_Raw')
    df_salida['Fundo_Raw'] = _serie_o_nulos(df, 'Fundo_Raw')
    df_salida['Modulo_Raw'] = _serie_o_nulos(df, 'Modulo_Raw')
    df_salida['Turno_Raw'] = _serie_o_nulos(df, 'Turno_Raw')
    df_salida['Valvula_Raw'] = _serie_o_nulos(df, 'Valvula_Raw')
    df_salida['Variedad_Raw'] = _serie_o_nulos(df, 'Variedad_Raw')
    df_salida['Estado_Planta_Raw'] = _serie_o_nulos(df, 'Estado_Planta_Raw')
    df_salida['Cantidad_Raw'] = _serie_o_nulos(df, 'Cantidad_Raw')
    df_salida['Linea_Raw'] = _serie_o_nulos(df, 'Linea_Raw') if 'Linea_Raw' in df.columns else _serie_o_nulos(df, 'Linea')
    
    # Extraer columnas operativas
    df_salida['DNI_Raw'] = _serie_o_nulos(df, 'DNI_Raw') if 'DNI_Raw' in df.columns else _serie_o_nulos(df, 'DNI')
    df_salida['Evaluador_Raw'] = _serie_o_nulos(df, 'Evaluador_Raw') if 'Evaluador_Raw' in df.columns else _serie_o_nulos(df, 'Evaluador')
    df_salida['Fecha_Detalle_Raw'] = _serie_o_nulos(df, 'Fecha_Detalle_Raw') if 'Fecha_Detalle_Raw' in df.columns else _serie_o_nulos(df, 'Fecha_Detalle')
    df_salida['Fecha_Subida_Raw'] = _serie_o_nulos(df, 'Fecha_Subida_Raw') if 'Fecha_Subida_Raw' in df.columns else _serie_o_nulos(df, 'Fecha_Subida')

    # Intentar extraer Campaña si existe
    col_campana = [c for c in df.columns if str(c).lower().replace('ñ', 'n') in ('campana', 'campaa', 'campana_raw', 'campaña')]
    if col_campana:
        df_salida['Campana_Raw'] = df[col_campana[0]]
    else:
        df_salida['Campana_Raw'] = None

    df_salida['Valores_Raw'] = None
    return df_salida


def _proyectar_dataframe_telemetria_clima_bronce(ruta_archivo: Path) -> pd.DataFrame:
    """
    Proyecta el layout de Telemetria de Clima a columnas de Bronce.
    Extrae el sector climatico desde el nombre del archivo, o usa 'SIN_SECTOR' por defecto.
    """
    df = _leer_excel_especial(ruta_archivo, sheet_name=0, header_idx=0)
    if df.empty:
        return df

    sector = _extraer_sector_climatico_desde_archivo(ruta_archivo) or 'SIN_SECTOR'

    columnas_salida = {
        'Semana_Raw':              _serie_o_nulos(df, 'Semana_Raw'),
        'FechaHora_Raw':           _serie_o_nulos(df, 'FechaHora_Raw'),
        'Sector_Raw':              pd.Series([sector] * len(df), index=df.index),
        'Temp_Exterior_Raw':       _serie_o_nulos(df, 'Temp_Exterior_Raw'),
        'Temp_Maxima_Raw':         _serie_o_nulos(df, 'Temp_Maxima_Raw'),
        'Temp_Minima_Raw':         _serie_o_nulos(df, 'Temp_Minima_Raw'),
        'Humedad_Externa_Raw':     _serie_o_nulos(df, 'Humedad_Externa_Raw'),
        'Punto_Rocio_Raw':         _serie_o_nulos(df, 'Punto_Rocio_Raw'),
        'Velocidad_Max_KmH_Raw':   _serie_o_nulos(df, 'Velocidad_Max_KmH_Raw'),
        'Velocidad_Max_Ms_Raw':    _serie_o_nulos(df, 'Velocidad_Max_Ms_Raw'),
        'Lluvia_Raw':              _serie_o_nulos(df, 'Lluvia_Raw'),
        'Intensidad_Lluvia_Raw':   _serie_o_nulos(df, 'Intensidad_Lluvia_Raw'),
        'Radiacion_Solar_Raw':     _serie_o_nulos(df, 'Radiacion_Solar_Raw'),
        'Indice_UV_Raw':           _serie_o_nulos(df, 'Indice_UV_Raw'),
        'Evapotranspiracion_Raw':  _serie_o_nulos(df, 'Evapotranspiracion_Raw'),
        'Indice_Calor_Raw':        _serie_o_nulos(df, 'Indice_Calor_Raw'),
        'Calor_Raw':               _serie_o_nulos(df, 'Calor_Raw'),
        'Grados_Dia_Raw':          _serie_o_nulos(df, 'Grados_Dia_Raw'),
    }

    df_salida = pd.DataFrame(columnas_salida, index=df.index)
    columnas_usadas = set(columnas_salida.keys())
    columnas_extra = [col for col in df.columns if col not in columnas_usadas]
    if columnas_extra:
        df_salida['Valores_Raw'] = _serializar_valores_extra(df, columnas_extra)

    return df_salida


def _detectar_hoja_y_header(
    ruta_archivo: Path,
    tabla_destino: str,
    engine,
) -> tuple[str | int, int]:
    """
    Recorre todas las hojas del Excel y elige (hoja, header_idx) que más coincida
    con columnas reales de la tabla Bronce. Score: matches, -unnamed, -desconocidas.
    """
    columnas_raw = {c for c in _obtener_columnas_bronce(tabla_destino, engine)
                    if str(c).endswith('_Raw')}
    with pd.ExcelFile(str(ruta_archivo), engine='calamine') as xls:
        hojas = xls.sheet_names

    mejor = (hojas[0], 0)
    mejor_score = (-1, -1, -1)
    for sh in hojas:
        for idx in (0, 1):
            try:
                cols = _columnas_normalizadas_excel(ruta_archivo, idx, sheet_name=sh)
            except Exception:
                continue
            set_cols = set(cols)
            match = len(set_cols & columnas_raw) if columnas_raw else 0
            unnamed = sum(1 for c in cols if str(c).lower().startswith('unnamed'))
            desconocidas = len(set_cols - columnas_raw) if columnas_raw else 0
            score = (match, -unnamed, -desconocidas)
            if score > mejor_score:
                mejor = (sh, idx)
                mejor_score = score
    return mejor


def _serializar_valores_extra(df: pd.DataFrame, columnas_extra: list[str]) -> pd.Series:
    """
    Serializa columnas no mapeadas en formato "col=valor | col2=valor2".
    Versión vectorizada para alta performance en archivos grandes.
    """
    if not columnas_extra:
        return pd.Series([None] * len(df), index=df.index)

    # Inicializar con serie de strings vacíos
    res = pd.Series("", index=df.index, dtype=str)
    
    for col in columnas_extra:
        # Extraer, convertir a string y limpiar
        val = df[col].astype(str).str.strip()
        # Máscara de valores que ignoraremos (vacíos, None, nan)
        mask = (val == "") | (val.str.lower() == "none") | (df[col].isna())
        
        # Preparar fragmento "NombreColumna=Valor"
        fragmento = col + "=" + val
        fragmento[mask] = ""
        
        # Concatenar usando separador. str.cat con na_rep="" maneja la unión eficientemente
        res = res.str.cat(fragmento, sep=" | ", na_rep="").str.strip(" | ")
        
    return res.replace("", None)


def _formatear_columnas_extra(columnas_extra: list[str], max_columnas: int = 12) -> str:
    """
    Devuelve una version legible de las columnas extra detectadas.
    Limita la salida para no romper el log de consola.
    """
    if not columnas_extra:
        return ''

    columnas_ordenadas = sorted(str(col) for col in columnas_extra)
    if len(columnas_ordenadas) <= max_columnas:
        return ', '.join(columnas_ordenadas)

    visibles = ', '.join(columnas_ordenadas[:max_columnas])
    restantes = len(columnas_ordenadas) - max_columnas
    return f'{visibles}, ... (+{restantes} mas)'


def _alinear_dataframe_a_tabla(
    df: pd.DataFrame,
    tabla_destino: str,
    engine,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Alinea columnas del DataFrame con columnas fisicas de la tabla SQL.
    - Aplica mapeos de compatibilidad entre layouts de Excel.
    - Descarta columnas no existentes en SQL.
    - Si existe Valores_Raw, serializa columnas descartadas para no perder dato.
    """
    columnas_tabla = _obtener_columnas_bronce(tabla_destino, engine)
    if not columnas_tabla:
        return df, []

    mapa_ci = {col.lower(): col for col in columnas_tabla}
    renombres_ci = {col: mapa_ci[col.lower()] for col in df.columns
                    if col not in columnas_tabla and col.lower() in mapa_ci}
    if renombres_ci:
        df = df.rename(columns=renombres_ci)

    if 'Evaluador_Raw' in columnas_tabla and 'Evaluador_Raw' not in df.columns and 'Nombres_Raw' in df.columns:
        df['Evaluador_Raw'] = df['Nombres_Raw']
    if 'Variedad_Raw' in columnas_tabla and 'Variedad_Raw' not in df.columns and 'Descripcion_Raw' in df.columns:
        df['Variedad_Raw'] = df['Descripcion_Raw']
    if 'Tipo_Evaluacion_Raw' in columnas_tabla and 'Tipo_Evaluacion_Raw' not in df.columns and 'Evaluacion_Raw' in df.columns:
        df['Tipo_Evaluacion_Raw'] = df['Evaluacion_Raw']
    if 'TallosPlanta_Raw' in columnas_tabla and 'TallosPlanta_Raw' not in df.columns and 'Tallos_Planta_Raw' in df.columns:
        df['TallosPlanta_Raw'] = df['Tallos_Planta_Raw']
    if 'LongitudTallo_Raw' in columnas_tabla and 'LongitudTallo_Raw' not in df.columns and 'Longitud_de_Tallo_Raw' in df.columns:
        df['LongitudTallo_Raw'] = df['Longitud_de_Tallo_Raw']
    if 'DiametroTallo_Raw' in columnas_tabla and 'DiametroTallo_Raw' not in df.columns and 'Diametro_de_Tallo_Raw' in df.columns:
        df['DiametroTallo_Raw'] = df['Diametro_de_Tallo_Raw']
    if 'RamillaPlanta_Raw' in columnas_tabla and 'RamillaPlanta_Raw' not in df.columns and 'Ramilla_Planta_Raw' in df.columns:
        df['RamillaPlanta_Raw'] = df['Ramilla_Planta_Raw']
    if 'ToconesPlanta_Raw' in columnas_tabla and 'ToconesPlanta_Raw' not in df.columns and 'Tocones_Planta_Raw' in df.columns:
        df['ToconesPlanta_Raw'] = df['Tocones_Planta_Raw']
    if 'CortesDefectuosos_Raw' in columnas_tabla and 'CortesDefectuosos_Raw' not in df.columns and 'N_Cortes_Defect_Planta_Raw' in df.columns:
        df['CortesDefectuosos_Raw'] = df['N_Cortes_Defect_Planta_Raw']
    if 'AlturaPoda_Raw' in columnas_tabla and 'AlturaPoda_Raw' not in df.columns and 'Altura_de_Planta_Raw' in df.columns:
        df['AlturaPoda_Raw'] = df['Altura_de_Planta_Raw']
    if 'Semanas_Poda_Raw' in columnas_tabla and 'Semanas_Poda_Raw' not in df.columns and 'N_de_cama_Raw' in df.columns:
        df['Semanas_Poda_Raw'] = df['N_de_cama_Raw']
    if 'Peso_Neto_Raw' in columnas_tabla and 'Peso_Neto_Raw' not in df.columns and 'Kg_Total_Raw' in df.columns:
        df['Peso_Neto_Raw'] = df['Kg_Total_Raw']
    if 'Peso_Bruto_Raw' in columnas_tabla and 'Peso_Bruto_Raw' not in df.columns and 'Kg_Total_Raw' in df.columns:
        df['Peso_Bruto_Raw'] = df['Kg_Total_Raw']

    # Mapeo específico para Cosecha_SAP: KgNeto_Raw -> Kg_Total_Raw
    if (
        tabla_destino.endswith('Cosecha_SAP')
        and 'Kg_Total_Raw' in columnas_tabla
        and 'KgNeto_Raw' in df.columns
    ):
        df['Kg_Total_Raw'] = df['KgNeto_Raw']
        df = df.drop(columns=['KgNeto_Raw'])

    columnas_extra = [col for col in df.columns if col not in columnas_tabla]

    if columnas_extra and 'Valores_Raw' in columnas_tabla:
        extras_serializados = _serializar_valores_extra(df, columnas_extra)
        if 'Valores_Raw' in df.columns:
            base = df['Valores_Raw'].astype(str).replace({'None': ''}).fillna('')
            extra = extras_serializados.astype(str).replace({'None': ''}).fillna('')
            combinado = (base.str.strip() + ' | ' + extra.str.strip()).str.strip(' |')
            df['Valores_Raw'] = combinado.replace('', None)
        else:
            df['Valores_Raw'] = extras_serializados

    columnas_insertables = [col for col in df.columns if col in columnas_tabla]
    if not columnas_insertables:
        return df.iloc[:, 0:0], columnas_extra

    return df[columnas_insertables], columnas_extra


def _detectar_ruta_sugerida(
    columnas_detectadas: set[str],
    nombre_carpeta_actual: str,
) -> tuple[str | None, float]:
    mejor_ruta = None
    mejor_score = 0.0

    for ruta, firma in _FIRMAS_RUTA_SUGERIDA.items():
        if ruta == nombre_carpeta_actual:
            continue

        columnas_clave = set(firma.get('columnas_clave', set()))
        if not columnas_clave:
            continue

        coincidencias = len(columnas_detectadas & columnas_clave)
        score = coincidencias / len(columnas_clave)
        if score >= 0.8 and coincidencias >= 6 and score > mejor_score:
            mejor_ruta = ruta
            mejor_score = score

    return mejor_ruta, mejor_score


def _score_ruta_actual(
    columnas_detectadas: set[str],
    nombre_carpeta_actual: str,
) -> float:
    firma = _FIRMAS_RUTA_SUGERIDA.get(nombre_carpeta_actual)
    if not firma:
        return 0.0

    columnas_clave = set(firma.get('columnas_clave', set()))
    if not columnas_clave:
        return 0.0

    coincidencias = len(columnas_detectadas & columnas_clave)
    return coincidencias / len(columnas_clave)


def _validar_layout_critico(
    nombre_carpeta: str,
    tabla_destino: str,
    columnas_detectadas: set[str],
) -> dict | None:
    firma = _FIRMAS_LAYOUT_CRITICO.get(tabla_destino)
    if not firma:
        return None

    columnas_obligatorias = set(firma.get('columnas_obligatorias', set()))
    faltantes = sorted(columnas_obligatorias - columnas_detectadas)
    columnas_incompatibles = sorted(columnas_detectadas & set(firma.get('columnas_incompatibles', set())))

    columnas_geo_alternativas = tuple(
        set(grupo) for grupo in firma.get('columnas_geo_alternativas', tuple())
    )
    if columnas_geo_alternativas and not any(
        grupo.issubset(columnas_detectadas)
        for grupo in columnas_geo_alternativas
    ):
        faltantes.append('Fundo_Raw o Turno_Raw+Valvula_Raw')

    columnas_brote_alternativas = tuple(
        set(grupo) for grupo in firma.get('columnas_brote_alternativas', tuple())
    )
    if columnas_brote_alternativas and not any(
        grupo.issubset(columnas_detectadas)
        for grupo in columnas_brote_alternativas
    ):
        faltantes.append('Brote_Raw o BrotesProd_Raw')

    if not faltantes:
        return None

    if not columnas_incompatibles and not firma.get('rechazar_por_faltantes', False):
        return None

    ruta_sugerida, _ = _detectar_ruta_sugerida(columnas_detectadas, nombre_carpeta)
    columnas_clave = sorted(
        columnas_detectadas & (columnas_obligatorias | set(firma.get('columnas_incompatibles', set())))
    )
    detalle_ruta = (
        f'Ruta sugerida: {ruta_sugerida}'
        if ruta_sugerida
        else 'Ruta sugerida: sin ruta compatible conocida en el ETL actual'
    )

    return {
        'codigo': 'LAYOUT_INCOMPATIBLE',
        'tabla': tabla_destino,
        'ruta_recibida': nombre_carpeta,
        'faltantes': faltantes,
        'columnas_detectadas_clave': columnas_clave,
        'ruta_sugerida': ruta_sugerida,
        'mensaje': (
            f'LAYOUT_INCOMPATIBLE | archivo incompatible con {nombre_carpeta} -> {tabla_destino}. '
            f'Faltantes: {", ".join(faltantes)} | '
            f'Detectadas clave: {", ".join(columnas_clave) if columnas_clave else "ninguna"} | '
            f'Motivo: {firma["motivo"]} | {detalle_ruta}'
        ),
    }


def _validar_enrutamiento_global(
    nombre_carpeta: str,
    tabla_destino: str,
    columnas_detectadas: set[str],
) -> dict | None:
    if nombre_carpeta not in _FIRMAS_RUTA_SUGERIDA:
        return None

    ruta_sugerida, score_sugerida = _detectar_ruta_sugerida(columnas_detectadas, nombre_carpeta)
    if not ruta_sugerida:
        return None

    score_actual = _score_ruta_actual(columnas_detectadas, nombre_carpeta)
    if score_actual >= 0.5:
        return None

    columnas_clave_sugeridas = sorted(
        columnas_detectadas & set(_FIRMAS_RUTA_SUGERIDA[ruta_sugerida].get('columnas_clave', set()))
    )
    return {
        'codigo': 'RUTA_CONTENIDO_INCOMPATIBLE',
        'tabla': tabla_destino,
        'ruta_recibida': nombre_carpeta,
        'ruta_sugerida': ruta_sugerida,
        'mensaje': (
            f'RUTA_CONTENIDO_INCOMPATIBLE | archivo recibido en {nombre_carpeta} -> {tabla_destino}, '
            f'pero su contenido coincide con alta confianza con la ruta {ruta_sugerida}. '
            f'Score actual: {score_actual:.2f} | Score sugerido: {score_sugerida:.2f} | '
            f'Columnas clave detectadas: {", ".join(columnas_clave_sugeridas) if columnas_clave_sugeridas else "ninguna"}'
        ),
    }


def cargar_archivo(nombre_carpeta: str,
                   ruta_archivo: Path,
                   tabla_destino: str,
                   engine) -> dict:
    """
    Carga un archivo Excel a su tabla Bronce destino.
    Retorna resumen del resultado.
    """
    resultado = {
        'archivo':   ruta_archivo.name,
        'tabla':     tabla_destino,
        'filas':     0,
        'estado':    'ERROR',
        'mensaje':   '',
    }
    ruta_trabajo: Path | None = None

    try:
        ruta_trabajo = _crear_copia_temporal_excel(ruta_archivo)

        if nombre_carpeta == 'reporte_clima':
            df = _proyectar_dataframe_clima_bronce(ruta_trabajo, tabla_destino)
        elif nombre_carpeta == 'conteo_fruta':
            df = _proyectar_dataframe_conteo_bronce(ruta_trabajo)
        elif nombre_carpeta == 'peladas':
            df = _proyectar_dataframe_peladas_bronce(ruta_trabajo)
        elif nombre_carpeta == 'induccion_floral':
            df = _proyectar_dataframe_induccion_floral_bronce(ruta_trabajo, engine)
        elif nombre_carpeta == 'tasa_crecimiento_brotes':
            df = _proyectar_dataframe_tasa_crecimiento_brotes_bronce(ruta_trabajo)
        elif nombre_carpeta == 'censo_plantas':
            df = _proyectar_dataframe_censo_plantas_bronce(ruta_trabajo)
        elif nombre_carpeta == 'telemetria_clima':
            df = _proyectar_dataframe_telemetria_clima_bronce(ruta_trabajo)
        else:
            sheet_name, header_idx = _detectar_hoja_y_header(ruta_trabajo, tabla_destino, engine)
            df = pd.read_excel(str(ruta_trabajo), sheet_name=sheet_name, header=header_idx, dtype=str, engine='calamine')
            if df.empty:
                resultado['mensaje'] = 'Archivo vacio - sin filas para cargar'
                resultado['estado'] = 'VACIO'
                return resultado
            df = normalizar_columnas(df)

        if df.empty:
            resultado['mensaje'] = 'Archivo vacio - sin filas para cargar'
            resultado['estado'] = 'VACIO'
            return resultado

        validacion_layout = _validar_layout_critico(
            nombre_carpeta,
            tabla_destino,
            {str(col) for col in df.columns},
        )
        if not validacion_layout:
            validacion_layout = _validar_enrutamiento_global(
                nombre_carpeta,
                tabla_destino,
                {str(col) for col in df.columns},
            )
        if validacion_layout:
            ruta_rechazada, archivo_bloqueado = archivar_archivo_rechazado(
                ruta_archivo,
                nombre_carpeta,
                validacion_layout['codigo'],
            )
            resultado['estado'] = 'ERROR'
            resultado['critico'] = True
            resultado['codigo'] = validacion_layout['codigo']
            resultado['ruta_sugerida'] = validacion_layout['ruta_sugerida']
            resultado['mensaje'] = (
                f'{validacion_layout["mensaje"]} | '
                f'Archivo movido a rechazados: {ruta_rechazada}'
            )
            if archivo_bloqueado:
                resultado['mensaje'] += ' | original bloqueado: se copio y se marco para omitir reproceso'
            return resultado

        df = castear_todo_a_texto(df)
        df = agregar_columnas_sistema(df, ruta_archivo.name)
        df, columnas_descartadas = _alinear_dataframe_a_tabla(df, tabla_destino, engine)
        if df.shape[1] == 0:
            resultado['estado'] = 'ERROR'
            resultado['mensaje'] = (
                'No hay columnas insertables en la tabla destino. '
                f'Columnas no mapeadas: {len(columnas_descartadas)}'
            )
            return resultado

        filas_insertadas = insertar_en_bronce(df, tabla_destino, engine)
        ruta_procesada, archivo_bloqueado = archivar_archivo(ruta_archivo, nombre_carpeta)

        resultado['filas'] = filas_insertadas
        resultado['estado'] = 'OK'
        resultado['mensaje'] = f'{filas_insertadas} filas insertadas en {tabla_destino}'
        if archivo_bloqueado:
            resultado['mensaje'] += (
                f' | archivo bloqueado: copia archivada en {ruta_procesada}'
                ' y original marcado para omitir reproceso'
            )
        if columnas_descartadas:
            detalle_columnas = _formatear_columnas_extra(columnas_descartadas)
            resultado['columnas_extras'] = sorted(str(col) for col in columnas_descartadas)
            resultado['mensaje'] += (
                f' | columnas extras: {len(columnas_descartadas)}'
                f' [{detalle_columnas}]'
            )

    except Exception as error:
        resultado['mensaje'] = str(error)
        resultado['estado'] = 'ERROR'
    finally:
        if ruta_trabajo is not None:
            try:
                ruta_trabajo.unlink(missing_ok=True)
            except Exception:
                pass

    return resultado


def ejecutar_carga_bronce() -> list[dict]:
    """
    Punto de entrada del modulo Bronce.
    Busca todos los archivos pendientes y los carga a sus tablas destino.
    Retorna lista de resultados por archivo.
    """
    import logging
    _log = logging.getLogger("ETL_Pipeline")
    engine = obtener_engine()
    pendientes = listar_carpetas_con_archivos()
    resultados = []

    if not pendientes:
        _log.info("Bronce: sin archivos pendientes.")
        return resultados

    _log.info(f"Bronce: {len(pendientes)} archivo(s) encontrado(s).")

    for nombre_carpeta, ruta_archivo, tabla_destino in pendientes:
        _log.info(f"Cargando {ruta_archivo.name} -> {tabla_destino}...")

        id_log = registrar_inicio(tabla_destino, ruta_archivo.name)
        resultado = cargar_archivo(
            nombre_carpeta, ruta_archivo, tabla_destino, engine
        )
        registrar_fin(id_log, resultado)

        estado_txt = "OK" if resultado["estado"] == "OK" else "ERROR"
        _log.info(f"[{estado_txt}] {resultado['mensaje']}")

        resultados.append(resultado)

    return resultados
