"""
fact_tasa_crecimiento_brotes.py
===============================
Carga Silver.Fact_Tasa_Crecimiento_Brotes desde Bronce.Tasa_Crecimiento_Brotes.

LAYOUT REAL (verificado en BD, mayo 2026)
-----------------------------------------
- Las columnas dedicadas Medida_Raw / Ensayo_Raw / Tipo_Tallo_Raw /
  Condicion_Raw / Codigo_Origen_Raw / Fecha_Poda_Aux_Raw / Campana_Raw
  NO existen en Bronce: viven empacadas dentro de `Valores_Raw`
  (formato 'Clave=Valor | Clave=Valor | ...').
- El esquema destino fue refactorizado (refactor_silver_2026_05.sql, sección E):
  se dropearon 8 columnas (Medida_Crecimiento, Codigo_Ensayo, Dias_Desde_Poda,
  Fecha_Poda_Aux, etc.) y se agregaron `Planta_Brote NVARCHAR(50)` y
  `Cantidad INT`. El grano único es:
      (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal,
       Tipo_Tallo, Estado_Vegetativo, Planta_Brote).

Mapeo aplicado:
  Planta_Brote  <- Valores_Raw['Ensayo_Raw']      (ej. 'P4B4')
  Cantidad      <- round(Valores_Raw['Medida_Raw']) (medida de crecimiento; INT)
  Tipo_Tallo    <- Valores_Raw['Tipo_Tallo_Raw']
  ID_Condicion  <- resolver(Valores_Raw['Condicion_Raw'])
  Estado_Vegetativo <- columna Estado_Vegetativo_Raw

CAVEAT: Silver.Cantidad es INT; Medida_Raw puede traer decimales (ej. 3.5) que se
redondean. Si se requiere fidelidad sub-unidad, migrar Cantidad -> DECIMAL(10,2).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from mdm.homologador import homologar_columna
from mdm.bridges_tasa_crecimiento import (
    garantizar_bridge_geografia_cama,
    resolver_id_cama,
    resolver_id_condicion,
)
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    a_entero_nulo as _a_entero_nulo,
    finalizar_resumen_fact as _finalizar_resumen_fact,
    texto_nulo as _texto_nulo,
    validar_layout_migrado as _validar_layout_migrado_helper,
)


TABLA_ORIGEN = 'Bronce.Tasa_Crecimiento_Brotes'
TABLA_DESTINO = 'Silver.Fact_Tasa_Crecimiento_Brotes'


def _a_decimal_nulo(valor) -> float | None:
    try:
        if valor is None:
            return None
        texto = str(valor).strip().replace(',', '.')
        if texto in ('', 'None', 'nan'):
            return None
        return float(texto)
    except (ValueError, TypeError):
        return None


def validar_layout_migrado(engine: Engine) -> str:
    """Falla fuerte si Bronce/Silver no traen las columnas del layout real."""
    return _validar_layout_migrado_helper(
        engine,
        tabla_origen=TABLA_ORIGEN,
        tabla_destino=TABLA_DESTINO,
        columna_id='ID_Tasa_Crecimiento',
        columnas_bronce_requeridas={
            'ID_Tasa_Crecimiento',
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Estado_Vegetativo_Raw',
            'Variedad_Raw',
            'Valores_Raw',
            'Estado_Carga',
        },
        columnas_silver_requeridas={
            'ID_Geografia',
            'ID_Tiempo',
            'ID_Variedad',
            'ID_Personal',
            'ID_Condicion',
            'Tipo_Tallo',
            'Estado_Vegetativo',
            'Planta_Brote',
            'Cantidad',
        },
        nombre_layout='Tasa_Crecimiento_Brotes',
    )


class ProcesadorTasaCrecimientoBrotes(BaseFactProcessor):
    def __init__(self, engine: Engine, columna_id: str):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id=columna_id)
        # Grano: debe coincidir con UX_Fact_TCBrotes_Grain en la BD.
        self.columnas_clave_unica = [
            'ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal',
            'Tipo_Tallo', 'Estado_Vegetativo', 'Planta_Brote',
        ]
        self._columna_id = columna_id
        # Pares (id_geografia, id_cama, fecha) para upsert al Bridge_Geografia_Cama
        # tras la insercion masiva (no impacta el path caliente).
        self._pares_geo_cama: dict[tuple[int, int], object] = {}

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)

        # 2. Mapear columnas derivadas vectorialmente
        planta_brote_s = self._vectorized_get_raw_val(df, v_raw_df, 'Planta_Brote_Raw')
        ensayo_s = self._vectorized_get_raw_val(df, v_raw_df, 'Ensayo_Raw')
        df['_Planta_Brote_Temp'] = planta_brote_s.fillna(ensayo_s).map(_texto_nulo)

        medida_s = self._vectorized_get_raw_val(df, v_raw_df, 'Cantidad_Raw')
        medida_raw_s = self._vectorized_get_raw_val(df, v_raw_df, 'Medida_Raw')
        df['_Medida_Temp'] = medida_s.fillna(medida_raw_s).map(_a_decimal_nulo)

        tallo_s = self._vectorized_get_raw_val(df, v_raw_df, 'Tallo_Raw')
        tallo_raw_s = self._vectorized_get_raw_val(df, v_raw_df, 'Tipo_Tallo_Raw')
        df['_Tallo_Temp'] = tallo_s.fillna(tallo_raw_s).map(_texto_nulo)

        condicion_s = self._vectorized_get_raw_val(df, v_raw_df, 'Evaluacion_Raw')
        condicion_raw_s = self._vectorized_get_raw_val(df, v_raw_df, 'Condicion_Raw')
        df['_Condicion_Temp'] = condicion_s.fillna(condicion_raw_s).map(_texto_nulo)

        # 3. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='Fecha_Raw',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo=None,
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_cama='Cama_Raw',
            col_dni='DNI_Raw',
            dominio_fecha='tasa_crecimiento_brotes'
        )

        if df_resolved.empty:
            return []

        # Identificar columna ID original
        col_id_origen = self.columna_id
        if col_id_origen not in df_resolved.columns:
            col_id_origen = 'ID_Registro_Origen'

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = _a_entero_nulo(r.get(col_id_origen))

            planta_brote = r['_Planta_Brote_Temp']
            if planta_brote is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='Planta_Brote_Raw',
                    valor=r.get('Planta_Brote_Raw'),
                    motivo='Identificador planta-brote vacio o invalido',
                    fila=r,
                )
                continue

            medida = r['_Medida_Temp']
            if medida is None or medida < 0:
                self.registrar_rechazo(
                    id_origen,
                    columna='Cantidad_Raw',
                    valor=r.get('Cantidad_Raw'),
                    motivo='Medida de crecimiento invalida o negativa',
                    fila=r,
                )
                continue

            cantidad = int(round(medida))
            tipo_tallo = r['_Tallo_Temp']
            condicion = r['_Condicion_Temp']

            id_cama = resolver_id_cama(r.get('Cama_Raw'), self.engine)
            id_condicion = resolver_id_condicion(condicion, self.engine)

            id_geo = r['ID_Geografia']
            if id_geo is not None and id_cama is not None:
                clave_par = (int(id_geo), int(id_cama))
                fecha_evento = r['Fecha_Evento_dt']
                fecha_actual = fecha_evento.date() if hasattr(fecha_evento, 'date') else fecha_evento
                fecha_existente = self._pares_geo_cama.get(clave_par)
                if fecha_existente is None or fecha_actual < fecha_existente:
                    self._pares_geo_cama[clave_par] = fecha_actual

            self.ids_procesados.append(id_origen)

            payload.append({
                'ID_Geografia':       id_geo,
                '_id_modulo_catalogo': r['_id_modulo_catalogo'],
                'ID_Tiempo':          int(r['ID_Tiempo']),
                'ID_Variedad':        int(r['ID_Variedad']),
                'ID_Personal':        int(r['ID_Personal']),
                'ID_Condicion':       id_condicion,
                'Tipo_Evaluacion':    condicion,
                'Estado_Vegetativo':  _texto_nulo(r.get('Estado_Vegetativo_Raw')),
                'Tipo_Tallo':         tipo_tallo,
                'Planta_Brote':       planta_brote,
                'Cantidad':           cantidad,
                'Fecha_Evento':       fecha_evento,
                'Estado_DQ':          'OK',
                'id_origen_rastreo':  id_origen,
            })
        return payload

    def _sincronizar_bridges(self, contexto: ContextoTransaccionalETL) -> None:
        """
        Post-insercion:
        1. Garantiza filas en Bridge_Geografia_Cama para cada (geo, cama) usado.
        2. Rellena ID_Condicion en Bridge_Modulo_Campana cuando aun es NULL,
           tomando la condicion mayoritaria observada en el fact por
           (modulo, variedad, campana). Idempotente.
        """
        if not self._pares_geo_cama:
            return

        conexion = contexto._conexion_activa()

        for (id_geo, id_cama), fecha_inicio in self._pares_geo_cama.items():
            garantizar_bridge_geografia_cama(conexion, id_geo, id_cama, fecha_inicio)


def cargar_fact_tasa_crecimiento_brotes(engine: Engine) -> dict:
    # Fail-loud si el layout no está migrado (Fase 0): mejor abortar que NULL-ear silencioso.
    validar_layout_migrado(engine)

    proc = ProcesadorTasaCrecimientoBrotes(engine, columna_id='ID_Tasa_Crecimiento')

    # Incluye columnas físicas dedicadas (Planta_Brote_Raw, Cantidad_Raw, Tallo_Raw, Condicion_Raw)
    # para que Silver lea directamente sin depender de Valores_Raw.
    # Valores_Raw se mantiene como fallback para registros historicos (pre-fix).
    cols_raw = [
        'Fecha_Raw', 'DNI_Raw', 'Evaluador_Raw', 'Modulo_Raw', 'Turno_Raw',
        'Valvula_Raw', 'Cama_Raw', 'Variedad_Raw', 'Estado_Vegetativo_Raw',
        'Planta_Brote_Raw', 'Cantidad_Raw', 'Tallo_Raw', 'Evaluacion_Raw',
        'Valores_Raw', 'Nombre_Archivo',
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Tasa_Crecimiento',
        )

        # Clave de deduplicacion: debe coincidir con el grano real del Fact en Silver.
        # No incluimos Cantidad_Raw ya que es la métrica de medición, no parte del grano único,
        # lo que evita falsos registros no-duplicados en el batch y cuarentenas.
        df = proc.pre_limpiar_duplicados_batch(df, [
            'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Cama_Raw',
            'Fecha_Raw', 'Variedad_Raw', 'DNI_Raw',
            'Tallo_Raw', 'Estado_Vegetativo_Raw', 'Planta_Brote_Raw',
        ])

        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_TasaCrecimientoBrotes')
        proc._sincronizar_bridges(contexto)

        return proc.finalizar_proceso(contexto)
