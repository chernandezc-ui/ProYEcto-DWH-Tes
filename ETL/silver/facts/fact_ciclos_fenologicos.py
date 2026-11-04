"""
fact_ciclos_fenologicos.py
==========================
Carga Silver.Fact_Ciclos_Fenologicos desde Bronce.Ciclos_Fenologicos.

Esta tabla recibe evaluaciones de fases fenológicas (FFase1, FFase2, Crema, etc.)
realizadas por evaluadores en una cama / módulo / variedad específica.

Formato Bronce.Valores_Raw: texto plano con pares clave=valor separados por '|'.
Ejemplo:
    Fecha_Subida_Raw=02/02/2026 18:35:17 | Nombres_Raw=MARIA DEL CARMEN | \\
    Evaluacion_Raw=Poda general | Cama_Raw=23 | Fecha_detalle_Raw=2026-02-02 | \\
    Dia_Raw=6 | Categoria_Raw=FFase2 | Cantidad_Raw=13

Grain: Geografía × Tiempo × Variedad × Cama × Tipo_Evaluacion × ID_Estado_Fenologico

NO confundir con:
  - Bronce.Evaluacion_Calidad_Poda → fact_ciclo_poda (calidad física del corte)
  - Bronce.Fenologia                → fact_conteo_fenologico
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from utils.texto import titulo
from mdm.homologador import homologar_columna
from mdm.lookup import obtener_id_cinta, obtener_id_estado_fenologico
from silver.facts._base_processor import BaseFactProcessor
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact
from utils.tipos import a_decimal as _a_decimal, a_entero as _a_entero


TABLA_ORIGEN  = 'Bronce.Ciclos_Fenologicos'
TABLA_DESTINO = 'Silver.Fact_Ciclos_Fenologicos'


def _parsear_valores_raw(valores_raw: str | None) -> dict[str, str]:
    """
    Parsea el campo Valores_Raw de la forma 'clave=valor | clave=valor | ...'
    y devuelve un dict {clave: valor}. Tolerante: ignora tokens malformados.
    """
    resultado: dict[str, str] = {}
    if not valores_raw or not isinstance(valores_raw, str):
        return resultado
    for token in valores_raw.split('|'):
        token = token.strip()
        if '=' not in token:
            continue
        clave, _, valor = token.partition('=')
        clave = clave.strip()
        valor = valor.strip()
        if clave:
            resultado[clave] = valor
    return resultado


class ProcesadorCiclosFenologicos(BaseFactProcessor):
    def __init__(self, engine: Engine):
        super().__init__(engine, TABLA_ORIGEN, TABLA_DESTINO, columna_id='ID_Ciclo_Fenologico')
        # Grain: Geo + Tiempo + Variedad + Cama + Tipo_Evaluacion + ID_Estado_Fenologico
        self.columnas_clave_unica = [
            'ID_Geografia', 'ID_Tiempo', 'ID_Variedad',
            'Cama', 'Tipo_Evaluacion', 'ID_Estado_Fenologico',
            'ID_Cinta', 'Organo',
        ]
        self.columna_tiebreaker_timestamp = 'Fecha_Sistema'
        
        # Cargar mapeo de DNI -> Nombre_Completo de Dim_Personal en memoria
        self._nombre_evaluadores = {}
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT DNI, Nombre_Completo FROM Silver.Dim_Personal")).fetchall()
                self._nombre_evaluadores = {str(r[0]).strip(): str(r[1]).strip() for r in res if r[0]}
        except Exception as e:
            print(f"[DEBUG] Error al cargar cache de evaluadores: {e}")

    def _construir_payload(self, df: pd.DataFrame) -> list[dict]:
        import re
        import datetime as _dt
        from mdm.lookup import obtener_id_estado_fenologico, obtener_id_cinta

        # 1. Parsear Valores_Raw en lote
        v_raw_df = pd.DataFrame([self.parsear_raw(x) for x in df['Valores_Raw']], index=df.index)

        # 2. Derivar fecha de forma vectorizada
        def _get_fecha_ciclo(r_fecha, v_r):
            fecha_str = v_r.get('Fecha_detalle_Raw') or r_fecha
            if not fecha_str or str(fecha_str).strip() in ('', 'None', 'nan'):
                ano_val = v_r.get('Ano_Raw') or v_r.get('Anio_Raw') or v_r.get('A_o_Raw')
                semana_val = v_r.get('Semana_Raw')
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
                            if year_campana > 2026: year_campana = 2026
                            fecha_str = f'{year_campana}-01-01'
                if not fecha_str or str(fecha_str).strip() in ('', 'None', 'nan'):
                    fecha_str = '2015-01-01'
            return str(fecha_str)

        df['_Deriv_Fecha_Temp'] = [
            _get_fecha_ciclo(df.loc[idx, 'Fecha_Raw'], v_raw_df.loc[idx])
            for idx in df.index
        ]

        # 3. Resolver dimensiones en batch
        df_resolved = self.resolver_dimensiones_batch(
            df,
            col_fecha='_Deriv_Fecha_Temp',
            col_modulo='Modulo_Raw',
            col_variedad='Variedad_Canonica',
            col_fundo='Fundo_Raw',
            col_turno='Turno_Raw',
            col_valvula='Valvula_Raw',
            dominio_fecha='ciclos_fenologicos'
        )

        if df_resolved.empty:
            return []

        # 4. Cap de fechas > 2026-06-30
        mask_cap = df_resolved['Fecha_Evento_dt'] > pd.Timestamp('2026-06-30')
        if mask_cap.any():
            df_resolved.loc[mask_cap, 'Fecha_Evento_dt'] = pd.Timestamp('2026-06-30')
            id_tiempo_capped = obtener_id_tiempo(pd.Timestamp('2026-06-30'))
            df_resolved.loc[mask_cap, 'ID_Tiempo'] = id_tiempo_capped

        # 5. Parsear de nuevo Valores_Raw para el subconjunto resuelto
        v_raw_resolved = v_raw_df.loc[df_resolved.index]

        payload = []
        for idx, r in df_resolved.iterrows():
            id_origen = int(r['ID_Ciclo_Fenologico'])
            self.ids_procesados.append(id_origen)

            v_r = v_raw_resolved.loc[idx]

            def _safe_str(val):
                if pd.isna(val): return None
                s = str(val).strip()
                return s if s and s.lower() not in ('nan', 'none') else None

            categoria_raw = titulo(_safe_str(r.get('Etapa_Fenologica_Raw')) or _safe_str(v_r.get('Stage_Raw')) or _safe_str(v_r.get('Categoria_Raw')))
            id_estado = obtener_id_estado_fenologico(categoria_raw, self.engine)
            if id_estado is None:
                continue

            id_cinta = obtener_id_cinta(_safe_str(r.get('Color_Raw')), self.engine)

            evaluador_raw = _safe_str(r.get('Evaluador_Raw'))
            evaluador_nombre = self._nombre_evaluadores.get(evaluador_raw, evaluador_raw) if evaluador_raw else None

            payload.append({
                'ID_Geografia':          r['ID_Geografia'],
                '_id_modulo_catalogo':   r['_id_modulo_catalogo'],
                'ID_Tiempo':             int(r['ID_Tiempo']),
                'ID_Variedad':           int(r['ID_Variedad']),
                'Cama':                  _safe_str(v_r.get('Cama_Raw')),
                'ID_Cinta':              id_cinta,
                'Organo':                _safe_str(r.get('Organo_Raw')),
                'Tipo_Evaluacion':       titulo(_safe_str(v_r.get('Evaluacion_Raw'))) or 'HISTORICO',
                'ID_Estado_Fenologico':  id_estado,
                'Evaluador':             evaluador_nombre,
                'Fecha_Evento':          r['Fecha_Evento_dt'],
                'Fecha_Sistema':         r.get('Fecha_Sistema'),
                'Estado_DQ':             'OK',
                'id_origen_rastreo':     id_origen,
            })
        return payload


def cargar_fact_ciclos_fenologicos(engine: Engine) -> dict:
    proc = ProcesadorCiclosFenologicos(engine)

    cols_raw = [
        'Fecha_Raw', 'Modulo_Raw', 'Turno_Raw', 'Valvula_Raw',
        'Variedad_Raw', 'Evaluador_Raw',
        'Color_Raw', 'Organo_Raw',
        'Etapa_Fenologica_Raw',
        'Valores_Raw',
        'Fecha_Sistema',
    ]
    df = proc.leer_bronce(cols_raw)
    if df.empty:
        return _finalizar_resumen_fact(proc.resumen)
    proc.resumen['leidos'] = len(df)

    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()
        df, cuar_var = homologar_columna(
            df, 'Variedad_Raw', 'Variedad_Canonica', TABLA_ORIGEN, conexion,
            columna_id_origen='ID_Ciclo_Fenologico',
        )

        # Deduplicar a nivel batch antes de construir payload (incluyendo Etapa,
        # Organo y Color para evitar pérdidas masivas de información).
        df = proc.pre_limpiar_duplicados_batch(
            df, [
                'Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 
                'Etapa_Fenologica_Raw', 'Color_Raw', 'Organo_Raw', 
                'Valores_Raw'
            ]
        )

        proc.resumen['cuarentena'].extend(cuar_var)

        payload = proc._construir_payload(df)
        proc._ejecutar_insercion_masiva_segura(contexto, payload, '#Temp_CiclosFenologicos')

        return proc.finalizar_proceso(contexto)