"""
fact_telemetria_clima.py
========================
Carga Silver.Fact_Telemetria_Clima desde Bronce.Telemetria_Clima.

Grain: Sector_Climatico x Fecha_Hora
"""

import math
import re
import pandas as pd
from typing import Any
from sqlalchemy.engine import Engine
from sqlalchemy import text

from dq.validador import normalizar_humedad
from mdm.lookup import obtener_id_tiempo as obtener_id_tiempo_dim, obtener_id_campana
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo as construir_id_tiempo, procesar_fecha
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact

TABLA_CLIMA = 'Bronce.Telemetria_Clima'
TABLA_DESTINO = 'Silver.Fact_Telemetria_Clima'


def _leer_bronce_clima(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conexion:
        resultado = conexion.execute(text(f"""
            SELECT
                ID_Telemetria_Clima,
                Semana_Raw,
                FechaHora_Raw,
                Sector_Raw,
                Temp_Exterior_Raw,
                Temp_Maxima_Raw,
                Temp_Minima_Raw,
                Humedad_Externa_Raw,
                Punto_Rocio_Raw,
                Velocidad_Max_KmH_Raw,
                Velocidad_Max_Ms_Raw,
                Lluvia_Raw,
                Intensidad_Lluvia_Raw,
                Radiacion_Solar_Raw,
                Indice_UV_Raw,
                Evapotranspiracion_Raw,
                Indice_Calor_Raw,
                Calor_Raw,
                Grados_Dia_Raw
            FROM {TABLA_CLIMA}
            WHERE Estado_Carga = 'CARGADO'
        """))
        return pd.DataFrame(resultado.fetchall(), columns=resultado.keys())


def _a_decimal(valor, decimales: int | None = None) -> float | None:
    try:
        if valor is None:
            return None
        texto = str(valor).strip()
        if not texto or texto.upper() in {'NONE', 'NULL', 'NAN'}:
            return None
        numero = float(texto.replace(',', '.'))
        if not math.isfinite(numero):
            return None
        if decimales is not None:
            numero = round(numero, decimales)
        return numero
    except (ValueError, TypeError):
        return None


def _a_entero_nulo(valor) -> int | None:
    try:
        if valor is None:
            return None
        texto = str(valor).strip()
        if texto in ('', 'None', 'nan'):
            return None
        return int(float(texto))
    except (ValueError, TypeError):
        return None


def _normalizar_sector_climatico(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto.upper() in {'NONE', 'NULL', 'NAN'}:
        return None
    return texto.upper()


def _clave_logica_clima(registro: dict) -> tuple:
    """Retorna la clave lógica del grano (Sector_Climatico, Fecha_Hora) para agrupamiento."""
    return (registro['sector_climatico'], registro['fecha_hora'])


class ProcesadorTelemetriaClima(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_CLIMA, TABLA_DESTINO, columna_id='ID_Telemetria_Clima')
        self.columnas_clave_unica = ['Sector_Climatico', 'Fecha_Hora']
        self.LIMITE_ERROR = 101.0
        self.LIMITE_CRITICO = 101.0

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # 1. Resolver tiempo de forma vectorizada
        raw_fechas = df['FechaHora_Raw'].dropna().unique()
        mapeo_fechas = {}
        for raw_f in raw_fechas:
            fecha, valida = procesar_fecha(str(raw_f), dominio='clima')
            if not valida:
                filas_invalidas = df[df['FechaHora_Raw'] == raw_f]
                for _, r in filas_invalidas.iterrows():
                    id_orig = int(r['ID_Telemetria_Clima'])
                    self.registrar_rechazo(
                        id_orig,
                        columna='FechaHora_Raw',
                        valor=raw_f,
                        motivo='FechaHora invalida en clima',
                    )
                mapeo_fechas[raw_f] = (None, None)
            else:
                id_tiempo = obtener_id_tiempo_dim(construir_id_tiempo(fecha), self.engine)
                if not id_tiempo:
                    filas_invalidas = df[df['FechaHora_Raw'] == raw_f]
                    for _, r in filas_invalidas.iterrows():
                        id_orig = int(r['ID_Telemetria_Clima'])
                        self.registrar_rechazo(
                            id_orig,
                            columna='FechaHora_Raw',
                            valor=raw_f,
                            motivo='FechaHora valida pero fuera de Dim_Tiempo',
                        )
                    mapeo_fechas[raw_f] = (None, None)
                else:
                    mapeo_fechas[raw_f] = (fecha, id_tiempo)

        df['Fecha_Evento_dt'] = df['FechaHora_Raw'].map(lambda x: mapeo_fechas.get(x, (None, None))[0])
        df['ID_Tiempo'] = df['FechaHora_Raw'].map(lambda x: mapeo_fechas.get(x, (None, None))[1])
        df_resolved = df[df['ID_Tiempo'].notna()].copy()

        if df_resolved.empty:
            return []

        # 2. Filtrar y registrar sector climático inválido
        df_resolved['Sector_Climatico'] = df_resolved['Sector_Raw'].map(_normalizar_sector_climatico)
        df_invalid_sector = df_resolved[df_resolved['Sector_Climatico'].isna()]
        for _, r in df_invalid_sector.iterrows():
            id_orig = int(r['ID_Telemetria_Clima'])
            self.registrar_rechazo(
                id_orig,
                columna='Sector_Raw',
                valor=r.get('Sector_Raw'),
                motivo='Sector climatico invalido o ausente',
            )
        df_resolved = df_resolved[df_resolved['Sector_Climatico'].notna()].copy()

        if df_resolved.empty:
            return []

        # 3. Formular lista de registros válidos antes de deduplicación/fusión
        registros_clima_validos = []
        for idx, fila in df_resolved.iterrows():
            id_origen = int(fila['ID_Telemetria_Clima'])

            humedad, error_hum = normalizar_humedad(fila.get('Humedad_Externa_Raw'))
            if error_hum:
                self.resumen['cuarentena'].append({
                    'columna': 'Humedad_Externa_Raw',
                    'valor': str(fila.get('Humedad_Externa_Raw')),
                    'motivo': error_hum.get('motivo', 'Humedad invalida'),
                    'severidad': error_hum.get('severidad', 'BAJO'),
                    'id_registro_origen': id_origen,
                })

            registros_clima_validos.append({
                'id_origen': id_origen,
                'sector_climatico': fila['Sector_Climatico'],
                'id_tiempo': int(fila['ID_Tiempo']),
                'fecha_hora': fila['Fecha_Evento_dt'],
                'semana': _a_entero_nulo(fila.get('Semana_Raw')),
                'temp_exterior': _a_decimal(fila.get('Temp_Exterior_Raw'), decimales=2),
                'temp_max': _a_decimal(fila.get('Temp_Maxima_Raw'), decimales=2),
                'temp_min': _a_decimal(fila.get('Temp_Minima_Raw'), decimales=2),
                'humedad': humedad,
                'punto_rocio': _a_decimal(fila.get('Punto_Rocio_Raw'), decimales=2),
                'vel_max_kmh': _a_decimal(fila.get('Velocidad_Max_KmH_Raw'), decimales=2),
                'vel_max_ms': _a_decimal(fila.get('Velocidad_Max_Ms_Raw'), decimales=2),
                'lluvia': _a_decimal(fila.get('Lluvia_Raw'), decimales=2),
                'intensidad_lluvia': _a_decimal(fila.get('Intensidad_Lluvia_Raw'), decimales=2),
                'radiacion': _a_decimal(fila.get('Radiacion_Solar_Raw'), decimales=2),
                'indice_uv': _a_decimal(fila.get('Indice_UV_Raw'), decimales=2),
                'evapotranspiracion': _a_decimal(fila.get('Evapotranspiracion_Raw'), decimales=2),
                'indice_calor': _a_decimal(fila.get('Indice_Calor_Raw'), decimales=2),
                'calor': _a_decimal(fila.get('Calor_Raw'), decimales=2),
                'grados_dia': _a_decimal(fila.get('Grados_Dia_Raw'), decimales=2),
            })

        # 4. Agrupamiento e "Intelligent Fusion" de duplicados en memoria
        campos_metricas = (
            'semana', 'temp_exterior', 'temp_max', 'temp_min', 'humedad', 'punto_rocio',
            'vel_max_kmh', 'vel_max_ms', 'lluvia', 'intensidad_lluvia', 'radiacion',
            'indice_uv', 'evapotranspiracion', 'indice_calor', 'calor', 'grados_dia'
        )

        payload_clima = []
        grupos = {}
        for registro in registros_clima_validos:
            grupos.setdefault(_clave_logica_clima(registro), []).append(registro)

        for clave, grupo in grupos.items():
            if len(grupo) == 1:
                r_single = grupo[0]
                payload_clima.append(r_single)
                if r_single['id_origen'] is not None:
                    self.ids_procesados.append(r_single['id_origen'])
                continue

            consolidado = {campo: [r[campo] for r in grupo if r.get(campo) is not None] for campo in campos_metricas}
            hay_conflicto = False
            for campo, valores in consolidado.items():
                if len(set(valores)) > 1:
                    hay_conflicto = True
                    break

            if not hay_conflicto:
                registro_fusionado = grupo[0].copy()
                for campo in campos_metricas:
                    registro_fusionado[campo] = consolidado[campo][0] if consolidado[campo] else None
                payload_clima.append(registro_fusionado)
                for r in grupo:
                    if r['id_origen'] is not None:
                        self.ids_procesados.append(r['id_origen'])
                continue

            # Conflicto real
            sector_climatico, fecha_hora = clave
            motivo = (
                f'Conflicto de métricas en Bronce.Telemetria_Clima: '
                f'valores distintos para el mismo Sector/Fecha_Hora. '
                f'Detalle: { {k: list(set(v)) for k, v in consolidado.items() if len(set(v)) > 1} }'
            )
            for registro in grupo:
                self.registrar_rechazo(
                    registro.get('id_origen'),
                    columna='FechaHora_Raw',
                    valor=str(fecha_hora),
                    motivo=motivo,
                )

        # 5. Formatear payload final
        payload_insert = []
        for r in payload_clima:
            id_campana = obtener_id_campana(None, None, r['fecha_hora'], self.engine)
            payload_insert.append({
                'ID_Tiempo':               r['id_tiempo'],
                'Fecha_Hora':              r['fecha_hora'],
                'Sector_Climatico':        r['sector_climatico'],
                'Semana':                  r['semana'],
                'Temp_Exterior_C':         r['temp_exterior'],
                'Temp_Maxima_C':           r['temp_max'],
                'Temp_Minima_C':           r['temp_min'],
                'Humedad_Externa_Pct':     r['humedad'],
                'Punto_Rocio_C':           r['punto_rocio'],
                'Velocidad_Max_KmH':       r['vel_max_kmh'],
                'Velocidad_Max_Ms':        r['vel_max_ms'],
                'Lluvia_mm':               r['lluvia'],
                'Intensidad_Lluvia_mm_hr': r['intensidad_lluvia'],
                'Radiacion_Solar_Wm2':     r['radiacion'],
                'Indice_UV':               r['indice_uv'],
                'Evapotranspiracion_mm':   r['evapotranspiracion'],
                'Indice_Calor':            r['indice_calor'],
                'Calor':                   r['calor'],
                'Grados_Dia':              r['grados_dia'],
                'ID_Campana':              id_campana,
                'id_origen_rastreo':       r['id_origen'],
            })
        return payload_insert


def cargar_fact_telemetria_clima(engine: Engine) -> dict:
    proc = ProcesadorTelemetriaClima(engine)

    df_clima = _leer_bronce_clima(engine)
    if df_clima.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df_clima)

    with ContextoTransaccionalETL(engine) as contexto:
        payload = proc._construir_payload(df_clima)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_TelemetriaClima')
        return proc.finalizar_proceso(contexto)
