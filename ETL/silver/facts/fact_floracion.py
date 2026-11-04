"""
fact_floracion.py
=================
Carga Silver.Fact_Floracion desde Bronce.Floracion.

Layout definitivo:
- DNI / evaluador
- modulo / turno / valvula / cama
- descripcion como variedad fuente
- plantas evaluadas / plantas en floracion
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.sql_lotes import ejecutar_en_lotes
from mdm.homologador import homologar_columna
from mdm.lookup import obtener_id_campana_anual
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import (
    a_entero_nulo as _a_entero_nulo,
    a_entero_no_negativo as _a_entero_positivo,
    finalizar_resumen_fact as _finalizar_resumen_fact,
    texto_nulo as _texto_nulo,
    validar_layout_migrado as _validar_layout_migrado_helper,
)


TABLA_ORIGEN  = 'Bronce.Floracion'
TABLA_DESTINO = 'Silver.Fact_Floracion'

SQL_INSERT_FACT = text("""
    INSERT INTO Silver.Fact_Floracion (
        ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal,
        Tipo_Evaluacion,
        Cantidad_Plantas_Evaluadas, Cantidad_Plantas_en_Floracion,
        Fecha_Evento, Fecha_Sistema, Estado_DQ
    ) VALUES (
        :id_geo, :id_tiempo, :id_variedad, :id_personal,
        :tipo_evaluacion,
        :plantas_evaluadas, :plantas_en_floracion,
        :fecha_evento, SYSDATETIME(), 'OK'
    )
""")


def _validar_layout_migrado(engine: Engine) -> str:
    return _validar_layout_migrado_helper(
        engine,
        tabla_origen=TABLA_ORIGEN,
        tabla_destino=TABLA_DESTINO,
        columna_id='ID_Floracion',
        columnas_bronce_requeridas={
            'ID_Floracion',
            'Fecha_Raw',
            'DNI_Raw',
            'Modulo_Raw',
            'Turno_Raw',
            'Valvula_Raw',
            'Cama_Raw',
            'Descripcion_Raw',
            'Evaluacion_Raw',
        },
        columnas_silver_requeridas={
            'ID_Personal',
            'Tipo_Evaluacion',
            'Cantidad_Plantas_Evaluadas',
            'Cantidad_Plantas_en_Floracion',
        },
        nombre_layout='Evaluacion_Vegetativa',
    )


def _marcar_estado_por_firma(recurso_db, claves: list[dict], estado: str) -> None:
    if not claves:
        return

    sentencia = text(f"""
        UPDATE TOP (1) {TABLA_ORIGEN}
        SET Estado_Carga = :estado_carga
        WHERE Estado_Carga IN ('CARGADO', 'RECHAZADO', 'PROCESADO')
          AND ISNULL(Fecha_Raw, '') = ISNULL(:fecha_raw, '')
          AND ISNULL(DNI_Raw, '') = ISNULL(:dni_raw, '')
          AND ISNULL(Modulo_Raw, '') = ISNULL(:modulo_raw, '')
          AND ISNULL(Turno_Raw, '') = ISNULL(:turno_raw, '')
          AND ISNULL(Valvula_Raw, '') = ISNULL(:valvula_raw, '')
          AND ISNULL(Cama_Raw, '') = ISNULL(:cama_raw, '')
          AND ISNULL(N_Plantas_Evaluadas_Raw, '') = ISNULL(:plantas_evaluadas_raw, '')
          AND ISNULL(N_Plantas_en_Floracion_Raw, '') = ISNULL(:plantas_floracion_raw, '')
    """)
    payload = [
        {
            **clave,
            'estado_carga': estado,
        }
        for clave in claves
    ]
    ejecutar_en_lotes(recurso_db, sentencia, payload)


class ProcesadorFloracion(BaseFactProcessor):
    def __init__(self, engine: Engine, columna_id: str):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id=columna_id)
        self.columnas_clave_unica = ['ID_Geografia', 'ID_Tiempo', 'ID_Variedad', 'ID_Personal', 'Tipo_Evaluacion']
        self._columna_id = columna_id
        self._claves_procesadas: list[dict] = []
        self._claves_rechazadas: list[dict] = []

    def _firma_fila(self, fila: dict) -> dict:
        def _no_nan(val):
            import pandas as pd
            return None if pd.isna(val) else val

        return {
            'fecha_raw':             _no_nan(fila.get('Fecha_Raw')),
            'dni_raw':               _no_nan(fila.get('DNI_Raw')),
            'modulo_raw':            _no_nan(fila.get('Modulo_Raw')),
            'turno_raw':             _no_nan(fila.get('Turno_Raw')),
            'valvula_raw':           _no_nan(fila.get('Valvula_Raw')),
            'cama_raw':              _no_nan(fila.get('Cama_Raw')),
            'plantas_evaluadas_raw': _no_nan(fila.get('N_Plantas_Evaluadas_Raw')),
            'plantas_floracion_raw': _no_nan(fila.get('N_Plantas_en_Floracion_Raw')),
        }

    def _rechazar_fila(self, id_origen, columna, valor, motivo, fila, tipo_regla='DQ') -> None:
        self.registrar_rechazo(id_origen or 0, columna, valor, motivo, tipo_regla=tipo_regla)
        if id_origen is None:
            self._claves_rechazadas.append(self._firma_fila(fila))

    def _construir_payload(self, df) -> list[dict]:
        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)

        # 2. Derivar fecha de forma vectorizada
        def _get_fecha_floracion(r_fecha, v_r):
            fecha_str = r_fecha
            if not fecha_str or str(fecha_str).strip() in ('', 'None', 'nan'):
                ano_val = v_r.get('Ano_Raw') or v_r.get('Anio_Raw')
                semana_val = v_r.get('Sem_Calendario_Raw') or v_r.get('Semana_Raw')
                if ano_val and semana_val:
                    try:
                        import re
                        import datetime
                        year = int(float(str(ano_val).strip()))
                        week_str = re.sub(r'[^0-9]', '', str(semana_val))
                        week = int(week_str) if week_str else 1
                        fecha_str = datetime.datetime.strptime(f'{year}-W{week:02d}-1', "%G-W%V-%u").strftime('%Y-%m-%d')
                    except Exception:
                        pass
                if not fecha_str or str(fecha_str).strip() in ('', 'None', 'nan'):
                    campana_val = v_r.get('Campana_Raw')
                    if campana_val:
                        import re
                        numeros = re.findall(r'\d+', str(campana_val))
                        if numeros:
                            primer_num = int(numeros[0])
                            year_campana = primer_num + 2000 if primer_num < 100 else primer_num
                            fecha_str = f'{year_campana}-01-01'
                if not fecha_str or str(fecha_str).strip() in ('', 'None', 'nan'):
                    fecha_str = '2015-01-01'
            return str(fecha_str)

        df['_Deriv_Fecha_Temp'] = [
            _get_fecha_floracion(df.loc[idx, 'Fecha_Raw'], v_raw_df.loc[idx])
            for idx in df.index
        ]

        # 3. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Deriv_Fecha_Temp',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo=None,
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            col_cama='Cama_Raw',
            col_dni='DNI_Raw',
            dominio_fecha='evaluacion_vegetativa'
        )

        if df_resolved.empty:
            return []

        v_raw_resolved = v_raw_df.loc[df_resolved.index]

        # Identificar columna ID original
        col_id_origen = self.columna_id
        if col_id_origen not in df_resolved.columns:
            col_id_origen = 'ID_Registro_Origen'

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = _a_entero_nulo(r.get(col_id_origen))
            v_r = v_raw_resolved.loc[idx]

            plantas_eval_raw = r.get('N_Plantas_Evaluadas_Raw')
            if pd.isna(plantas_eval_raw) or str(plantas_eval_raw).strip() == '':
                plantas_eval_raw = v_r.get('pEvaluadas_Raw')

            plantas_flor_raw = r.get('N_Plantas_en_Floracion_Raw')
            if pd.isna(plantas_flor_raw) or str(plantas_flor_raw).strip() == '':
                plantas_flor_raw = v_r.get('PlantasConInduccion_Raw')

            plantas_evaluadas = _a_entero_positivo(plantas_eval_raw)
            if plantas_evaluadas is None or plantas_evaluadas == 0:
                self._rechazar_fila(id_origen, 'N_Plantas_Evaluadas_Raw', plantas_eval_raw, 'Cantidad de plantas evaluadas invalida', r)
                continue

            plantas_en_floracion = _a_entero_positivo(plantas_flor_raw)
            if plantas_en_floracion is None or plantas_en_floracion > plantas_evaluadas:
                self._rechazar_fila(id_origen, 'N_Plantas_en_Floracion_Raw', plantas_flor_raw, 'Plantas en floracion invalida o mayor al total evaluado', r)
                continue

            if id_origen is not None:
                self.ids_procesados.append(id_origen)
            else:
                self._claves_procesadas.append(self._firma_fila(r))

            payload.append({
                'ID_Geografia':                    r['ID_Geografia'],
                '_id_modulo_catalogo':             r['_id_modulo_catalogo'],
                'ID_Tiempo':                       int(r['ID_Tiempo']),
                'ID_Variedad':                     int(r['ID_Variedad']),
                'ID_Personal':                     int(r['ID_Personal']),
                'Tipo_Evaluacion':                 _texto_nulo(r.get('Evaluacion_Raw')) or 'SIN_TIPO',
                'Cantidad_Plantas_Evaluadas':      plantas_evaluadas,
                'Cantidad_Plantas_en_Floracion':   plantas_en_floracion,
                'Fecha_Evento':                    r['Fecha_Evento_dt'],
                'ID_Campana':                      obtener_id_campana_anual(r['Fecha_Evento_dt'], self.engine),
                'Estado_DQ':                       'OK',
                'id_origen_rastreo':               id_origen or 0,
            })

        payload_agrupado = {}
        for row in payload:
            clave = (row['ID_Geografia'], row['ID_Tiempo'], row['ID_Variedad'], row['ID_Personal'], row['Tipo_Evaluacion'])
            if clave not in payload_agrupado:
                payload_agrupado[clave] = row
            else:
                existente = payload_agrupado[clave]
                existente['Cantidad_Plantas_Evaluadas'] += row.get('Cantidad_Plantas_Evaluadas', 0)
                existente['Cantidad_Plantas_en_Floracion'] += row.get('Cantidad_Plantas_en_Floracion', 0)

        return list(payload_agrupado.values())

    def finalizar_proceso(self, contexto) -> dict:
        conexion = contexto._conexion_activa()
        if self._claves_procesadas:
            _marcar_estado_por_firma(conexion, self._claves_procesadas, 'PROCESADO')
        if self._claves_rechazadas:
            _marcar_estado_por_firma(conexion, self._claves_rechazadas, 'RECHAZADO')
        return super().finalizar_proceso(contexto)


def cargar_fact_floracion(engine: Engine) -> dict:
    proc = ProcesadorFloracion(engine, columna_id='ID_Floracion')

    # El layout real de Bronce.Floracion tiene la variedad en Variedad_Raw (100% poblada)
    # y las métricas (pEvaluadas, PlantasConInduccion) empacadas en Valores_Raw.
    cols_raw = [
        'Fecha_Raw', 'DNI_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw', 'Cama_Raw',
        'Variedad_Raw', 'Evaluacion_Raw', 'N_Plantas_Evaluadas_Raw', 'N_Plantas_en_Floracion_Raw',
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
            columna_id_origen='ID_Floracion',
        )
        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_Floracion')

        return proc.finalizar_proceso(contexto)
