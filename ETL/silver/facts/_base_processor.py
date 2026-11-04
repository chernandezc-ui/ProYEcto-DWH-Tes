"""
ETL/silver/facts/_base_processor.py
===================================
Base processor para componentes Silver (Facts).

Implementa des-duplicacion nativa en SQL Server via #Temp Tables
usando CREATE TABLE + executemany, que es el unico metodo confiable
para tablas temporales de sesion en pyodbc/SQLAlchemy.

-- POR QUE NO usamos pandas.to_sql() para #Temp Tables --
pandas.to_sql() crea la tabla en una conexion interna nueva que
SQL Server no puede ver desde la conexion activa del pipeline.
El warning "not found exactly as such" confirma este problema.
La solucion correcta es CREATE TABLE #Temp + executemany en la
misma conexion de la transaccion activa.

-- METODOS DE VALIDACION CON CACHE --
_validar_y_resolver_fecha, _validar_y_resolver_geografia,
_validar_y_resolver_variedad, _validar_y_resolver_personal
encapsulan la logica de lookup + cache que estaba duplicada en
cada fact. Las clases hijas los llaman directamente en _construir_payload.
"""

from __future__ import annotations

import logging
import pandas as pd
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils import circuit_breaker
from mdm.lookup import (
    obtener_parametros_pipeline,
    obtener_reglas_validacion,
    obtener_id_tiempo,
    obtener_id_geografia,
    obtener_id_variedad,
    obtener_id_personal,
    obtener_id_campana
)
from utils.tipos import a_entero, a_decimal, obtener_valor_raw as _get_raw
from silver.facts._helpers_fact_comunes import leer_bronce_dinamico, parsear_valores_raw

_log = logging.getLogger("ETL_Pipeline")


class BaseFactProcessor:
    # Niveles de calidad del circuit breaker (porcentaje de rechazo real sobre leídos)
    LIMITE_WARNING = circuit_breaker.UMBRAL_WARNING_DEFAULT
    LIMITE_ERROR = circuit_breaker.UMBRAL_ERROR_DEFAULT
    LIMITE_CRITICO = circuit_breaker.UMBRAL_CRITICO_DEFAULT

    def __init__(self, engine: Engine, tabla_origen: str, tabla_destino: str, columna_id: str = None):
        self.engine = engine
        self.tabla_origen = tabla_origen
        self.tabla_destino = tabla_destino
        
        # Cargar configuración real de la base de datos
        self.config_params = obtener_parametros_pipeline(engine)
        self.reglas_dq = obtener_reglas_validacion(engine)
        
        # Prioridad: 1. Parametro explicito, 2. Guess por nombre de tabla
        self.columna_id = columna_id or f"ID_{self.tabla_origen.split('.')[-1]}"
        
        self.columnas_clave_unica: list[str] = []
        self.ids_procesados: list[int] = []
        self.ids_rechazados: list[int] = []
        
        self.resumen = {
            'leidos': 0,
            'insertados': 0,
            'rechazados': 0,
            'cuarentena': [],
            'rechazados_ids': [], # Nueva estructura para reporte de calidad refinado
            'resueltos_por_tiebreaker': 0,  # Duplicados intra-batch resueltos por timestamp
        }
        
        # Cache interna para lookups frecuentes
        self._cache_personal: dict[str, int | None] = {}
        self._cache_variedades: dict[str, int | None] = {}
        self._cache_geografia: dict[tuple, dict | None] = {}
        self._cache_tiempo: dict[Any, int | None] = {}

    def registrar_rechazo(
        self,
        id_origen: int,
        columna: str,
        valor: Any,
        motivo: str,
        tipo_regla: str = 'DQ',
        severidad: str = 'ALTO',
        fila: dict | None = None,
        es_duplicado_interno: bool = False,
    ) -> None:
        """
        Registra un rechazo en el resumen y lo prepara para la tabla MDM.Cuarentena.
        """
        # Si tenemos la fila, intentamos extraer el nombre del archivo para dar contexto
        contexto_archivo = ""
        if fila is not None:
            nombre_archivo = None
            if isinstance(fila, dict):
                nombre_archivo = fila.get('Nombre_Archivo')
            elif hasattr(fila, 'get'):
                nombre_archivo = fila.get('Nombre_Archivo')
            elif 'Nombre_Archivo' in fila:
                nombre_archivo = fila['Nombre_Archivo']
            if nombre_archivo:
                contexto_archivo = f"[{nombre_archivo}] "

        self.resumen['rechazados'] = self.resumen.get('rechazados', 0) + 1
        self.resumen['rechazados_ids'].append({
            'id': id_origen,
            'es_duplicado_externo': False,
            'es_duplicado_interno': es_duplicado_interno,
        })
        if id_origen is not None:
            self.ids_rechazados.append(id_origen)
        self.resumen['cuarentena'].append({
            'columna': columna,
            'valor': str(valor) if valor is not None else 'NULL',
            'motivo': f"{contexto_archivo}{motivo}",
            'severidad': severidad,
            'tipo_regla': tipo_regla,
            'id_registro_origen': id_origen,
        })

    # ── utilidades de extraccion y conversion ──────────────────────────────────

    def parsear_raw(self, texto: str | None) -> dict[str, str]:
        """Envuelve parsear_valores_raw de helpers."""
        return parsear_valores_raw(texto)

    def get_raw_val(self, fila: Any, col: str, dict_raw: dict | None = None) -> Any:
        """
        Busca un valor de forma robusta:
        1. En la fila (DataFrame/Dict) con el nombre exacto.
        2. En el dict_raw (Valores_Raw) con el nombre exacto.
        3. En el dict_raw de forma insensible a mayúsculas/minúsculas.
        """
        # 1. Intento exacto en fila
        if hasattr(fila, 'get'):
            val = fila.get(col)
        elif hasattr(fila, col):
            val = getattr(fila, col)
        else:
            val = None
        
        if val is not None and str(val).strip() not in ('', 'None', 'nan'):
            return val

        if not dict_raw:
            return None

        # 2. Intento exacto en dict_raw
        val = dict_raw.get(col)
        if val is not None and str(val).strip() not in ('', 'None', 'nan'):
            return val
        
        # 3. Búsqueda insensible a mayúsculas/minúsculas en dict_raw
        col_lower = col.lower()
        for k, v in dict_raw.items():
            if k.lower() == col_lower:
                if v is not None and str(v).strip() not in ('', 'None', 'nan'):
                    return v
        
        return None

    def a_int(self, valor: Any) -> int | None:
        """Conversion segura a entero."""
        return a_entero(valor)

    def a_decimal(self, valor: Any) -> float | None:
        """Conversion segura a decimal."""
        return a_decimal(valor)

    def leer_bronce(self, columnas_raw: list[str], filtro_estado: bool = True) -> Any:
        """
        Lee la tabla origen usando el helper dinamico. 
        Evita duplicar la logica de SELECT y COLUMN_NAME en cada fact.
        """
        return leer_bronce_dinamico(
            self.engine, 
            self.tabla_origen, 
            self.columna_id, 
            columnas_raw, 
            filtro_estado=filtro_estado
        )

    # ── validaciones con cache (reutilizables por todas las clases hijas) ────────

    def _validar_y_resolver_fecha(
        self,
        id_origen: int,
        valor_fecha: Any,
        dominio: str,
    ) -> Any | None:
        """
        Llama procesar_fecha() + obtener_id_tiempo() con cache interno.
        Registra rechazo automaticamente si la fecha es invalida.
        Retorna el objeto fecha (date/datetime) o None si falla.
        """
        from utils.fechas import procesar_fecha, obtener_id_tiempo

        cache_key = (str(valor_fecha), dominio)
        if cache_key in self._cache_tiempo:
            resultado = self._cache_tiempo[cache_key]
            if resultado is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='Fecha_Raw',
                    valor=valor_fecha,
                    motivo='Fecha invalida o fuera de campana',
                )
            return resultado

        fecha, valida = procesar_fecha(valor_fecha, dominio=dominio)
        if not valida:
            self._cache_tiempo[cache_key] = None
            self.registrar_rechazo(
                id_origen,
                columna='Fecha_Raw',
                valor=valor_fecha,
                motivo='Fecha invalida o fuera de campana',
            )
            return None

        self._cache_tiempo[cache_key] = fecha
        return fecha

    def _resolver_geografia_base(
        self,
        fundo: Any,
        sector: Any,
        modulo: Any,
        turno: Any = None,
        valvula: Any = None,
        cama: Any = None,
    ) -> dict | None:
        from mdm.lookup import resolver_geografia
        return resolver_geografia(fundo, sector, modulo, self.engine, turno=turno, valvula=valvula, cama=cama)

    def _validar_y_resolver_geografia(
        self,
        id_origen: int,
        fundo: Any,
        modulo_raw: Any,
        turno: Any = None,
        valvula: Any = None,
        cama: Any = None,
        sector: Any = None,
    ) -> dict | None:
        """
        Llama es_test_block() + normalizar_modulo() + resolver_geografia() con cache.
        Registra rechazo automaticamente si la geografia no se resuelve.
        Retorna el dict resultado_geo (con 'id_geografia') o None si falla.

        sector es opcional y mantenido como keyword-only para compatibilidad
        con facts que no lo traen (la mayoria). Solo Conteo_Fenologico lo usa.
        """
        from utils.texto import es_test_block, normalizar_modulo
        from silver.facts._helpers_fact_comunes import motivo_cuarentena_geografia

        modulo = normalizar_modulo(modulo_raw)
        cache_key = (str(fundo), str(sector), str(modulo), str(turno), str(valvula), str(cama))

        if cache_key in self._cache_geografia:
            resultado = self._cache_geografia[cache_key]
            if resultado is None or not resultado.get('id_geografia'):
                self.registrar_rechazo(
                    id_origen,
                    columna='Modulo_Raw',
                    valor=f"Fundo={fundo} | Sector={sector} | Modulo={modulo_raw} | Turno={turno} | Valvula={valvula}",
                    motivo=motivo_cuarentena_geografia(resultado or {}),
                    tipo_regla='MDM',
                )
                return None
            return resultado

        resultado = self._resolver_geografia_base(fundo, sector, modulo, turno=turno, valvula=valvula, cama=cama)
        self._cache_geografia[cache_key] = resultado

        if not resultado or not resultado.get('id_geografia'):
            self.registrar_rechazo(
                id_origen,
                columna='Modulo_Raw',
                valor=f"Fundo={fundo} | Sector={sector} | Modulo={modulo_raw} | Turno={turno} | Valvula={valvula}",
                motivo=motivo_cuarentena_geografia(resultado or {}),
                tipo_regla='MDM',
            )
            return None

        return resultado

    def _validar_y_resolver_variedad(
        self,
        id_origen: int,
        variedad_canonica: Any,
        variedad_raw: Any = None,
    ) -> int | None:
        """
        Llama obtener_id_variedad() con cache interno.
        Registra rechazo automaticamente si no hay match en Dim_Variedad.
        Retorna ID_Variedad (int) o None si falla.
        """
        from mdm.lookup import obtener_id_variedad

        cache_key = str(variedad_canonica)
        if cache_key in self._cache_variedades:
            id_var = self._cache_variedades[cache_key]
            if id_var is None:
                self.registrar_rechazo(
                    id_origen,
                    columna='Variedad_Raw',
                    valor=variedad_raw if variedad_raw is not None else variedad_canonica,
                    motivo='Variedad sin match en Dim_Variedad',
                    tipo_regla='MDM',
                )
            return id_var

        id_var = obtener_id_variedad(variedad_canonica, self.engine)
        self._cache_variedades[cache_key] = id_var

        if not id_var:
            self.registrar_rechazo(
                id_origen,
                columna='Variedad_Raw',
                valor=variedad_raw if variedad_raw is not None else variedad_canonica,
                motivo='Variedad sin match en Dim_Variedad',
                tipo_regla='MDM',
            )
            return None

        return id_var

    def _validar_y_resolver_personal(
        self,
        valor_dni: Any,
    ) -> int | None:
        """
        Llama procesar_dni() + obtener_id_personal() con cache interno.
        NO registra rechazo: personal ausente es aceptable (retorna None/-1).
        Retorna ID_Personal (int) o None si el DNI no es resolvible.
        """
        from utils.dni import procesar_dni
        from mdm.lookup import obtener_id_personal

        cache_key = str(valor_dni)
        if cache_key in self._cache_personal:
            return self._cache_personal[cache_key]

        dni, _ = procesar_dni(valor_dni)
        id_personal = obtener_id_personal(dni, self.engine)
        self._cache_personal[cache_key] = id_personal
        return id_personal

    # ── helpers internos ───────────────────────────────────────────────────────

    def _tipo_sql_para_valor(self, valor: Any) -> str:
        """Infiere el tipo SQL Server para un valor no-nulo (string sin sizing)."""
        import datetime
        if isinstance(valor, bool):
            return "BIT"
        if isinstance(valor, int):
            return "BIGINT"
        if isinstance(valor, float):
            return "FLOAT"
        if isinstance(valor, (datetime.date, datetime.datetime)):
            return "DATETIME2"
        return "NVARCHAR"  # placeholder; el sizing real lo hace _inferir_tipo_columna

    def _inferir_tipo_columna(self, lista_dicts: list[dict], col: str) -> str:
        """
        Devuelve el tipo SQL para 'col' escaneando el batch completo.
        Para strings, dimensiona NVARCHAR al tamaño real (no NVARCHAR(MAX) fijo)
        para permitir fast_executemany sin reventar memoria.
        """
        tipo_no_str = None
        max_len = 0
        for row in lista_dicts:
            val = row.get(col)
            if val is None:
                continue
            if isinstance(val, str):
                if len(val) > max_len:
                    max_len = len(val)
            elif tipo_no_str is None:
                tipo_no_str = self._tipo_sql_para_valor(val)
        if tipo_no_str is not None:
            return tipo_no_str
        if max_len == 0:
            return "NVARCHAR(100)"
        if max_len <= 50:
            return "NVARCHAR(100)"
        if max_len <= 250:
            return "NVARCHAR(500)"
        if max_len <= 1000:
            return "NVARCHAR(2000)"
        if max_len <= 3500:
            return "NVARCHAR(4000)"
        return "NVARCHAR(MAX)"

    def _crear_y_cargar_temp(
        self,
        conexion,
        nombre_temp: str,
        cols_con_tipos: list[tuple[str, str]],
        lista_dicts: list[dict],
        columnas: list[str],
    ) -> None:
        """
        Delega en utils.sql_lotes.crear_e_insertar_temp: crea la #Temp table y
        la carga en la misma sesión/transacción activa del pipeline.

        Centraliza el patrón DROP/CREATE/INSERT que antes estaba duplicado entre
        _crear_tabla_temp_en_sesion + _insertar_en_temp aquí y en sql_lotes.
        """
        from utils.sql_lotes import crear_e_insertar_temp
        datos = [tuple(row.get(c) for c in columnas) for row in lista_dicts]
        crear_e_insertar_temp(conexion, nombre_temp, cols_con_tipos, datos)

    def _limpiar_duplicados_internos(self, lista_dicts: list[dict]) -> list[dict]:
        """
        Detecta duplicados dentro del mismo batch (Excel).

        Si self.columna_tiebreaker_timestamp está definida, aplica la política
        "último timestamp gana": entre filas con la misma clave se conserva la
        de mayor timestamp; los descartados NO van a Cuarentena (son re-mediciones
        legítimas, no errores de datos).

        Sin tiebreaker (comportamiento original): se conserva el primero visto y
        el duplicado se registra como DUPLICADO_INTERNO severidad MEDIO.
        """
        if not self.columnas_clave_unica:
            return lista_dicts

        import pandas as pd
        
        def normalizar_valor_clave(val):
            if val is None or pd.isna(val) or val is pd.NaT:
                return None
            val_str = str(val).strip()
            val_lower = val_str.lower()
            if val_lower in ("none", "nan", "null", "nat", "undefined", ""):
                return None
            try:
                val_float = float(val)
                if val_float.is_integer():
                    return int(val_float)
                return val_float
            except (ValueError, TypeError):
                pass
            return val_str

        def normalizar_ts(ts_val):
            if ts_val is None or pd.isna(ts_val) or ts_val is pd.NaT:
                return pd.Timestamp.min
            try:
                ts_pd = pd.to_datetime(ts_val)
                if pd.isna(ts_pd) or ts_pd is pd.NaT:
                    return pd.Timestamp.min
                if ts_pd.tzinfo is not None:
                    ts_pd = ts_pd.tz_localize(None)
                return ts_pd
            except Exception:
                return pd.Timestamp.min

        tiebreaker = getattr(self, 'columna_tiebreaker_timestamp', None)

        if tiebreaker:
            mejor: dict[tuple, dict] = {}
            score_desempate: dict[tuple, tuple] = {}
            resueltos_por_tiebreaker = 0
            
            for row in lista_dicts:
                clave = tuple(normalizar_valor_clave(row.get(c)) for c in self.columnas_clave_unica)
                ts_norm = normalizar_ts(row.get(tiebreaker))
                
                id_rastreo = -1
                id_raw = row.get('id_origen_rastreo')
                if id_raw is not None:
                    try:
                        id_rastreo = int(id_raw)
                    except (ValueError, TypeError):
                        pass
                
                score_actual = (ts_norm, id_rastreo)
                
                if clave not in mejor:
                    mejor[clave] = row
                    score_desempate[clave] = score_actual
                else:
                    score_previo = score_desempate[clave]
                    if score_actual > score_previo:
                        mejor[clave] = row
                        score_desempate[clave] = score_actual
                    resueltos_por_tiebreaker += 1
                    
            if resueltos_por_tiebreaker:
                self.resumen['resueltos_por_tiebreaker'] = (
                    self.resumen.get('resueltos_por_tiebreaker', 0) + resueltos_por_tiebreaker
                )
                _log.info(
                    f"[{self.tabla_destino}] Dedup intra-batch por tiebreaker "
                    f"'{tiebreaker}': {resueltos_por_tiebreaker} descartado(s), "
                    f"queda la medición más reciente."
                )
            return list(mejor.values())

        # Comportamiento original sin tiebreaker
        vistos = set()
        lista_limpia = []

        for row in lista_dicts:
            clave = tuple(normalizar_valor_clave(row.get(c)) for c in self.columnas_clave_unica)

            if clave in vistos:
                id_origen = row.get("id_origen_rastreo")
                if id_origen is not None:
                    valor_resumen = " | ".join([str(v) for v in clave])
                    self.registrar_rechazo(
                        id_origen=id_origen,
                        columna=",".join(self.columnas_clave_unica),
                        valor=valor_resumen,
                        motivo=f"Registro duplicado dentro del mismo archivo para {self.tabla_destino}",
                        tipo_regla='DUPLICADO_INTERNO',
                        severidad='MEDIO',
                        fila=row,
                        es_duplicado_interno=True,
                    )
                    if id_origen in self.ids_procesados:
                        self.ids_procesados.remove(id_origen)
            else:
                vistos.add(clave)
                lista_limpia.append(row)

        return lista_limpia

    def pre_limpiar_duplicados_batch(self, df: pd.DataFrame, columnas_clave_negocio: list[str]) -> pd.DataFrame:
        """
        Deduplica un DataFrame de Bronce antes de procesarlo, para evitar trabajo en vano.
        Útil para Facts con mucho volumen y duplicados técnicos.
        """
        if df.empty or not columnas_clave_negocio:
            return df
            
        # Detectar la columna de ID (original o alias común)
        col_id_actual = self.columna_id
        if col_id_actual not in df.columns and 'ID_Registro_Origen' in df.columns:
            col_id_actual = 'ID_Registro_Origen'
        elif col_id_actual not in df.columns:
            # Si no hay ID, no podemos trackear el descarte, solo deduplicamos
            _log.warning(f"[{self.tabla_destino}] No se encontró columna ID ({self.columna_id}) para trackear descartes.")
            return df.drop_duplicates(subset=[c for c in columnas_clave_negocio if c in df.columns], keep='first')

        # Aseguramos que las columnas de negocio existen en el DF
        cols_finales = [c for c in columnas_clave_negocio if c in df.columns]
        if not cols_finales:
            return df

        # ── Guarda anti-catastrofe (raiz del bug Tasa_Crecimiento 2026-05) ──
        # Si alguna columna de la clave esta 100% NULL en el batch (tipico de un
        # desfase de esquema enmascarado por columna_sql_dinamica), la clave es
        # degenerada: colapsaria filas legitimas en falsos "duplicados" que se
        # marcarian PROCESADO sin insertarse jamas (perdida silenciosa). Mejor NO
        # deduplicar aqui y dejar que el grano real + WHERE NOT EXISTS resuelvan.
        cols_todo_null = [c for c in cols_finales if df[c].isna().all()]
        if cols_todo_null:
            _log.warning(
                f"[{self.tabla_destino}] pre-dedup OMITIDO: columnas de clave 100%% NULL "
                f"{cols_todo_null} (clave degenerada). Se evita descarte masivo erroneo."
            )
            return df

        # Capturar IDs de los que vamos a descartar (los que NO son el 'first')
        df_duplicados = df[df.duplicated(subset=cols_finales, keep='first')]
        if not df_duplicados.empty:
            ids_a_descartar = df_duplicados[col_id_actual].dropna().unique().tolist()
            self.ids_procesados.extend([int(i) for i in ids_a_descartar])
            _log.info(f"Deduplicación temprana: {len(ids_a_descartar)} IDs marcados para descarte (redundantes).")

            # NUEVO: Enviar cada duplicado descartado a cuarentena
            for _, row in df_duplicados.iterrows():
                id_origen = row.get(col_id_actual)
                if pd.notna(id_origen):
                    valores_clave = " | ".join([str(row.get(c)) for c in cols_finales])
                    self.registrar_rechazo(
                        id_origen=int(id_origen),
                        columna=",".join(cols_finales),
                        valor=valores_clave,
                        motivo=f"Registro duplicado idéntico descartado tempranamente",
                        tipo_regla='DUPLICADO_BRONCE_EXACTO',
                        severidad='BAJO',
                        fila=row.to_dict(),
                        es_duplicado_interno=True
                    )

        # Mantenemos el primero de cada grupo
        df_limpio = df.drop_duplicates(subset=cols_finales, keep='first')
        return df_limpio

    # ── metodo principal ───────────────────────────────────────────────────────

    def _ejecutar_insercion_masiva_segura(
        self,
        contexto: ContextoTransaccionalETL,
        lista_dicts: list[dict],
        nombre_temp: str,
    ) -> None:
        """
        Deduplicacion y carga masiva en 5 pasos sin consumir RAM del servidor.

        1. Deduplicación interna: limpia duplicados dentro del mismo batch.
        2. Inferir tipos SQL escaneando el batch completo por columna.
        3+4. Crear #Temp e insertar batch vía crear_e_insertar_temp (helper compartido).
        5. Detectar duplicados con INNER JOIN contra la tabla destino.
        6. Insertar solo los NO-duplicados con WHERE NOT EXISTS / MERGE tiebreaker.
        """
        if not lista_dicts:
            return

        _log.info(f"DEBUG: Comenzando _ejecutar_insercion_masiva_segura para {len(lista_dicts)} registros...")

        # 0. Inyección automática de ID_Campana (Nueva Arquitectura)
        if any('ID_Campana' not in row for row in lista_dicts):
            from mdm.lookup import obtener_id_campana
            _cache_campana_local: dict[tuple, Any] = {}
            lista_original = lista_dicts
            lista_dicts = []
            
            for row in lista_original:
                if 'ID_Campana' not in row:
                    id_geo  = row.get('ID_Geografia')
                    id_var  = row.get('ID_Variedad')
                    id_mod  = row.get('_id_modulo_catalogo')
                    fecha   = row.get('Fecha_Evento') or row.get('Fecha') or row.get('Fecha_Cosecha')
                    fecha_k = str(fecha)[:10] if fecha is not None else None
                    clave   = (id_geo, id_var, id_mod, fecha_k)
                    
                    if clave not in _cache_campana_local:
                        _cache_campana_local[clave] = obtener_id_campana(id_geo, id_var, fecha, self.engine, id_modulo_catalogo=id_mod)
                    
                    id_campana = _cache_campana_local[clave]
                    row['ID_Campana'] = id_campana
                
                lista_dicts.append(row)

        _log.info("DEBUG: Inyección ID_Campana terminada. Iniciando limpieza duplicados internos...")
        # 1. Deduplicación interna en memoria (para evitar IntegrityError en el INSERT final)
        lista_dicts_limpia = self._limpiar_duplicados_internos(lista_dicts)
        
        if not lista_dicts_limpia:
             return

        # Convertir tipos numpy a nativos de Python para evitar fallos de inferencia y de pyodbc
        import numpy as np
        def to_python_type(val):
            if isinstance(val, (np.integer, np.int64, np.int32, np.int16, np.int8)):
                return int(val)
            if isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            if isinstance(val, np.bool_):
                return bool(val)
            if pd.isna(val):
                return None
            return val

        lista_dicts_limpia = [
            {k: to_python_type(v) for k, v in row.items()}
            for row in lista_dicts_limpia
        ]

        _log.info("DEBUG: Conversión de tipos Python terminada. Listando cols y tipos SQL...")
        conexion = contexto._conexion_activa()
        todas_cols = list(lista_dicts_limpia[0].keys())

        # 2. Inferir tipos SQL escaneando el batch completo por columna
        # (Se calcula una única vez con la lista limpia completa para asegurar consistencia de tipos en el esquema de la temporal)
        cols_con_tipos: list[tuple[str, str]] = [
            (col, self._inferir_tipo_columna(lista_dicts_limpia, col))
            for col in todas_cols
        ]

        # Obtener columnas reales de la tabla destino en base de datos para evitar error 42S22 (columna no existe en destino)
        partes_tabla = self.tabla_destino.split('.')
        esquema = partes_tabla[0] if len(partes_tabla) > 1 else 'dbo'
        tabla = partes_tabla[-1]
        sql_cols = text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = :esquema AND TABLE_NAME = :tabla
        """)
        columnas_reales = {row[0] for row in conexion.execute(sql_cols, {"esquema": esquema, "tabla": tabla}).fetchall()}

        # 5. Detectar duplicados (Filtrando columnas que existen en el destino para evitar error 42S22)
        columnas_fisicas_key = [c for c in self.columnas_clave_unica if c in todas_cols and c != 'id_origen_rastreo' and c in columnas_reales]
        if not columnas_fisicas_key:
            raise ValueError(
                f"[{self.tabla_destino}] columnas_clave_unica no tiene interseccion con las columnas de la tabla real. "
                f"Clave definida: {self.columnas_clave_unica} | Columnas reales: {columnas_reales}"
            )
        clausula_on_tmp = " AND ".join([f"(tmp.[{c}] = dest.[{c}] OR (tmp.[{c}] IS NULL AND dest.[{c}] IS NULL))" for c in columnas_fisicas_key])
        clausula_on_src = " AND ".join([f"(src.[{c}] = dest.[{c}] OR (src.[{c}] IS NULL AND dest.[{c}] IS NULL))" for c in columnas_fisicas_key])

        # Columnas físicas para INSERT/UPDATE (excluir auxiliares internas, de rastreo y las que no existen en la base de datos real)
        columnas_dest = [c for c in todas_cols if c != 'id_origen_rastreo' and not c.endswith('_Virtual') and not c.startswith('_') and c in columnas_reales]

        tiebreaker = getattr(self, 'columna_tiebreaker_timestamp', None)

        _log.info(f"DEBUG: Preparando inserción en chunks de 50000 para tabla real. Cols destino: {len(columnas_dest)}")
        # Hacemos chunking físico (lotes de 50,000 registros) para evitar bloqueos y consumo excesivo en tempdb/SQL Server
        chunk_size = 50000
        for chunk_idx in range(0, len(lista_dicts_limpia), chunk_size):
            chunk_batch = lista_dicts_limpia[chunk_idx:chunk_idx+chunk_size]
            if not chunk_batch:
                continue

            _log.info(f"DEBUG: Ejecutando chunk {chunk_idx // chunk_size + 1}...")
            # Asegurar de eliminar la tabla temporal por si quedó colgada de alguna iteración previa
            conexion.execute(text(f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"))

            # 3+4. Crear #Temp e insertar batch en un solo paso (helper compartido)
            self._crear_y_cargar_temp(conexion, nombre_temp, cols_con_tipos, chunk_batch, todas_cols)

            if tiebreaker and tiebreaker in todas_cols:
                # 6-TB. MERGE "último timestamp gana"
                col_update = ", ".join(
                    [f"dest.[{c}] = src.[{c}]" for c in columnas_dest if c not in columnas_fisicas_key]
                )
                col_insert_list = ", ".join([f"[{c}]" for c in columnas_dest])
                col_values_list = ", ".join([f"src.[{c}]" for c in columnas_dest])

                sql_merge = text(f"""
                    MERGE {self.tabla_destino} AS dest
                    USING {nombre_temp} AS src
                    ON ({clausula_on_src})
                    WHEN MATCHED AND ISNULL(src.[{tiebreaker}], '19000101') > ISNULL(dest.[Fecha_Sistema], '19000101')
                        THEN UPDATE SET {col_update}
                    WHEN NOT MATCHED BY TARGET
                        THEN INSERT ({col_insert_list}) VALUES ({col_values_list})
                    OUTPUT $action
                    OPTION (RECOMPILE);
                """)
                filas_accion = conexion.execute(sql_merge).fetchall()
                n_insert = sum(1 for r in filas_accion if r[0] == 'INSERT')
                n_update = sum(1 for r in filas_accion if r[0] == 'UPDATE')
                self.resumen['insertados'] += n_insert
                self.resumen.setdefault('actualizados_por_tiebreaker', 0)
                self.resumen['actualizados_por_tiebreaker'] += n_update
                if n_update > 0:
                    _log.info(
                        f"[{self.tabla_destino}] MERGE tiebreaker chunk {chunk_idx // chunk_size + 1}: "
                        f"{n_insert} INSERT, {n_update} UPDATE."
                    )
            else:
                # 5-orig. Detectar duplicados externos y marcarlos
                sql_duplicados = text(f"""
                    SELECT tmp.[id_origen_rastreo]
                    FROM {nombre_temp} tmp
                    INNER JOIN {self.tabla_destino} dest ON {clausula_on_tmp}
                """)
                duplicados = conexion.execute(sql_duplicados).fetchall()
                ids_duplicados = {int(d[0]) for d in duplicados if d[0] is not None}

                for id_dup in ids_duplicados:
                    if 'rechazados_ids' not in self.resumen:
                        self.resumen['rechazados_ids'] = []
                    self.resumen['rechazados_ids'].append({
                        'id': id_dup,
                        'es_duplicado_externo': True
                    })
                    if id_dup in self.ids_procesados:
                        self.ids_procesados.remove(id_dup)
                    self.ids_rechazados.append(id_dup)

                # 6-orig. INSERT solo los nuevos via WHERE NOT EXISTS
                col_select = ", ".join([f"tmp.[{c}]" for c in columnas_dest])
                col_insert = ", ".join([f"[{c}]" for c in columnas_dest])

                sql_insert = text(f"""
                    INSERT INTO {self.tabla_destino} ({col_insert})
                    SELECT {col_select}
                    FROM {nombre_temp} tmp
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {self.tabla_destino} dest
                        WHERE {clausula_on_tmp}
                    )
                    OPTION (RECOMPILE)
                """)
                resultado = conexion.execute(sql_insert)
                self.resumen['insertados'] += resultado.rowcount

            # 7. Limpieza
            conexion.execute(text(f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"))

    def _vectorized_get_raw_val(self, df: pd.DataFrame, v_raw_df: pd.DataFrame, col: str) -> pd.Series:
        """
        Versión vectorizada de get_raw_val. Busca el valor en la columna exacta de 'df',
        o en su defecto en la columna de 'v_raw_df' (de forma exacta o case-insensitive).
        Retorna una Series indexada igual que df.
        """
        # 1. Intento exacto en df
        if col in df.columns:
            s = df[col]
            valid_mask = s.notna() & (s.astype(str).str.strip() != '') & (s.astype(str) != 'None') & (s.astype(str) != 'nan')
            if valid_mask.any():
                return s.where(valid_mask, None)
        
        # 2. Intento exacto en v_raw_df
        if not v_raw_df.empty and col in v_raw_df.columns:
            s2 = v_raw_df[col]
            valid_mask2 = s2.notna() & (s2.astype(str).str.strip() != '') & (s2.astype(str) != 'None') & (s2.astype(str) != 'nan')
            if valid_mask2.any():
                return s2.where(valid_mask2, None)
                
        # 3. Búsqueda insensible a mayúsculas/minúsculas en v_raw_df
        if not v_raw_df.empty:
            col_lower = col.lower()
            for c in v_raw_df.columns:
                if c.lower() == col_lower:
                    s3 = v_raw_df[c]
                    valid_mask3 = s3.notna() & (s3.astype(str).str.strip() != '') & (s3.astype(str) != 'None') & (s3.astype(str) != 'nan')
                    if valid_mask3.any():
                        return s3.where(valid_mask3, None)
                        
        return pd.Series([None] * len(df), index=df.index)

    def _get_val_loc(self, row: pd.Series, v_raw: pd.Series, col: str) -> Any:
        """
        Obtiene un valor local para formateo final, revisando en row o en v_raw (incluso case-insensitive).
        """
        if col in row.index:
            val = row[col]
            if val is not None and str(val).strip() not in ('', 'None', 'nan'):
                return val
        if col in v_raw.index:
            val = v_raw[col]
            if val is not None and str(val).strip() not in ('', 'None', 'nan'):
                return val
        col_lower = col.lower()
        for idx in v_raw.index:
            if idx.lower() == col_lower:
                val = v_raw[idx]
                if val is not None and str(val).strip() not in ('', 'None', 'nan'):
                    return val
        return None

    def resolver_dimensiones_batch(
        self,
        df: pd.DataFrame,
        col_fecha: str,
        col_modulo: str,
        col_variedad: str | None = None,
        col_dni: str | None = None,
        col_fundo: str | None = None,
        col_turno: str | None = None,
        col_valvula: str | None = None,
        col_cama: str | None = None,
        col_sector: str | None = None,
        dominio_fecha: str = 'comun',
    ) -> pd.DataFrame:
        """
        Resuelve y valida de manera vectorizada y en batch todas las dimensiones clave
        (Fecha, Variedad, Personal, Geografía).
        Agrupa los lookups por valores únicos para lograr velocidad de C y reducir
        accesos a diccionarios en un factor de 100x a 1000x.
        Filtra y registra en Cuarentena en lote las filas rechazadas.
        """
        if df.empty:
            return df

        df_valid = df.copy()
        
        # Identificar columna ID original
        col_id_origen = self.columna_id
        if col_id_origen not in df_valid.columns:
            col_id_origen = 'ID_Registro_Origen'

        # --- 1. RESOLVER FECHA ---
        raw_fechas = df_valid[col_fecha].dropna().unique()
        mapeo_fechas = {}
        for raw_f in raw_fechas:
            from utils.fechas import procesar_fecha, obtener_id_tiempo
            fecha, valida = procesar_fecha(raw_f, dominio=dominio_fecha)
            if not valida:
                # Reclamar todos los ids origen con esta fecha inválida
                filas_invalidas = df_valid[df_valid[col_fecha] == raw_f]
                for _, r in filas_invalidas.iterrows():
                    id_orig = int(r[col_id_origen])
                    self.registrar_rechazo(
                        id_orig,
                        columna=col_fecha,
                        valor=raw_f,
                        motivo='Fecha invalida o fuera de campana',
                    )
                mapeo_fechas[raw_f] = (None, None)
            else:
                id_tiempo = obtener_id_tiempo(fecha)
                mapeo_fechas[raw_f] = (fecha, id_tiempo)
                
        df_valid['Fecha_Evento_dt'] = df_valid[col_fecha].map(lambda x: mapeo_fechas.get(x, (None, None))[0])
        df_valid['ID_Tiempo'] = df_valid[col_fecha].map(lambda x: mapeo_fechas.get(x, (None, None))[1])
        df_valid = df_valid[df_valid['ID_Tiempo'].notna()]

        if df_valid.empty:
            return df_valid

        # --- 2. RESOLVER VARIEDAD ---
        if col_variedad:
            col_var_lookup = 'Variedad_Canonica' if 'Variedad_Canonica' in df_valid.columns else col_variedad
            raw_vars = df_valid[col_var_lookup].dropna().unique()
            mapeo_vars = {}
            for rv in raw_vars:
                from mdm.lookup import obtener_id_variedad
                id_var = obtener_id_variedad(rv, self.engine)
                if not id_var:
                    filas_invalidas = df_valid[df_valid[col_var_lookup] == rv]
                    for _, r in filas_invalidas.iterrows():
                        id_orig = int(r[col_id_origen])
                        raw_val_orig = r.get(col_variedad) if col_variedad else rv
                        self.registrar_rechazo(
                            id_orig,
                            columna='Variedad_Raw',
                            valor=raw_val_orig,
                            motivo='Variedad sin match en Dim_Variedad',
                            tipo_regla='MDM',
                        )
                    mapeo_vars[rv] = None
                else:
                    mapeo_vars[rv] = id_var
            df_valid['ID_Variedad'] = df_valid[col_var_lookup].map(lambda x: mapeo_vars.get(x))
            df_valid = df_valid[df_valid['ID_Variedad'].notna()]

        if df_valid.empty:
            return df_valid

        # --- 3. RESOLVER PERSONAL ---
        if col_dni:
            raw_dnis = df_valid[col_dni].dropna().unique()
            mapeo_dnis = {}
            for rd in raw_dnis:
                from utils.dni import procesar_dni
                from mdm.lookup import obtener_id_personal
                dni, _ = procesar_dni(rd)
                id_pers = obtener_id_personal(dni, self.engine)
                mapeo_dnis[rd] = id_pers
            df_valid['ID_Personal'] = df_valid[col_dni].map(lambda x: mapeo_dnis.get(x, -1))
        else:
            df_valid['ID_Personal'] = -1

        # --- 4. RESOLVER GEOGRAFIA ---
        fundo_series = df_valid[col_fundo] if col_fundo and col_fundo in df_valid.columns else pd.Series([None] * len(df_valid), index=df_valid.index)
        sector_series = df_valid[col_sector] if col_sector and col_sector in df_valid.columns else pd.Series([None] * len(df_valid), index=df_valid.index)
        modulo_series = df_valid[col_modulo]
        turno_series = df_valid[col_turno] if col_turno and col_turno in df_valid.columns else pd.Series([None] * len(df_valid), index=df_valid.index)
        valvula_series = df_valid[col_valvula] if col_valvula and col_valvula in df_valid.columns else pd.Series([None] * len(df_valid), index=df_valid.index)
        cama_series = df_valid[col_cama] if col_cama and col_cama in df_valid.columns else pd.Series([None] * len(df_valid), index=df_valid.index)

        df_geo_keys = pd.DataFrame({
            'fundo': fundo_series,
            'sector': sector_series,
            'modulo': modulo_series,
            'turno': turno_series,
            'valvula': valvula_series,
            'cama': cama_series
        }, index=df_valid.index)

        from mdm.lookup import _geo_token, _geo_nombre_token, FUNDO_DEFECTO
        df_geo_keys['f_tok'] = df_geo_keys['fundo'].map(lambda x: _geo_nombre_token(x) or FUNDO_DEFECTO)
        df_geo_keys['s_tok'] = df_geo_keys['sector'].map(_geo_nombre_token)
        df_geo_keys['m_tok'] = df_geo_keys['modulo'].map(_geo_token)
        df_geo_keys['t_tok'] = df_geo_keys['turno'].map(_geo_token)
        df_geo_keys['v_tok'] = df_geo_keys['valvula'].map(_geo_token)
        df_geo_keys['c_tok'] = df_geo_keys['cama'].map(_geo_token)

        df_geo_keys['clave_geo'] = list(zip(
            df_geo_keys['f_tok'],
            df_geo_keys['s_tok'],
            df_geo_keys['m_tok'],
            df_geo_keys['t_tok'],
            df_geo_keys['v_tok'],
            df_geo_keys['c_tok']
        ))

        unique_geos = df_geo_keys['clave_geo'].unique()
        mapeo_geos = {}
        for gkey in unique_geos:
            f, s, m, t, v, c = gkey
            mapeo_geos[gkey] = self._resolver_geografia_base(f, s, m, turno=t, valvula=v, cama=c)

        df_valid['_res_geo_dict'] = df_geo_keys['clave_geo'].map(mapeo_geos)
        geo_valid_mask = df_valid['_res_geo_dict'].map(lambda d: d is not None and d.get('id_geografia') is not None)

        df_invalid_geo = df_valid[~geo_valid_mask]
        if not df_invalid_geo.empty:
            from silver.facts._helpers_fact_comunes import motivo_cuarentena_geografia
            for idx, r in df_invalid_geo.iterrows():
                id_orig = int(r[col_id_origen])
                res_dict = r['_res_geo_dict'] or {}
                fundo_val = r.get(col_fundo) if col_fundo else None
                modulo_val = r.get(col_modulo)
                turno_val = r.get(col_turno) if col_turno else None
                valvula_val = r.get(col_valvula) if col_valvula else None
                self.registrar_rechazo(
                    id_orig,
                    columna=col_modulo,
                    valor=f"Fundo={fundo_val} | Modulo={modulo_val} | Turno={turno_val} | Valvula={valvula_val}",
                    motivo=motivo_cuarentena_geografia(res_dict),
                    tipo_regla='MDM',
                )

        df_valid = df_valid[geo_valid_mask]
        df_valid['ID_Geografia'] = df_valid['_res_geo_dict'].map(lambda d: d['id_geografia'])
        df_valid['_id_modulo_catalogo'] = df_valid['_res_geo_dict'].map(lambda d: d.get('id_modulo_catalogo'))
        
        # Eliminar columnas temporales
        df_valid = df_valid.drop(columns=['_res_geo_dict'])
        return df_valid

    # ── finalizacion ───────────────────────────────────────────────────────────

    def finalizar_proceso(self, contexto: ContextoTransaccionalETL) -> dict:
        """Marca estados de carga, reporta cuarentena y evalua el Circuit Breaker."""
        
        if self.ids_procesados:
            contexto.marcar_estado_carga(self.tabla_origen, self.columna_id, self.ids_procesados)
        if self.ids_rechazados:
            contexto.marcar_estado_carga(self.tabla_origen, self.columna_id, self.ids_rechazados, estado='RECHAZADO')
        if self.resumen.get('cuarentena'):
            contexto.enviar_cuarentena(self.tabla_origen, self.resumen['cuarentena'])

        # ── Resumen de Continuidad ─────────────────────────────────────────────
        
        # 3. Calcular rechazo real (ignoring already existing technical duplicates)
        # Solo contamos como rechazo de CALIDAD lo que no es un duplicado externo
        lista_rechazos = self.resumen.get('rechazados_ids', [])
        rechazos_reales = [
            r for r in lista_rechazos
            if not r.get('es_duplicado_externo', False)
            and not r.get('es_duplicado_interno', False)
        ]
        unique_ids_rechazados = len(set(r['id'] for r in rechazos_reales))
        
        total_leidos = self.resumen.get('leidos', 0)
        breaker = circuit_breaker.evaluar(
            total_leidos, unique_ids_rechazados,
            umbrales=circuit_breaker.UmbralesCircuitBreaker(
                warning=self.LIMITE_WARNING, error=self.LIMITE_ERROR, critico=self.LIMITE_CRITICO,
            ),
            tabla=self.tabla_destino,
        )
        porcentaje_rechazo = breaker.porcentaje_rechazo
        
        # 4. Reporte final
        insertados_total = self.resumen.get('insertados', 0)
        _log.info(f"-> {total_leidos} leidos | {insertados_total} insertados | {unique_ids_rechazados} rechazados reales | {int(porcentaje_rechazo)}% rechazo real")

        # ── Deteccion de PERDIDA SILENCIOSA / desync (Bug #5) ─────────────────
        # Se leyo volumen significativo de Bronce pero nada se inserto NI se
        # rechazo: firma inequivoca de clave de grano degenerada, desfase de
        # esquema enmascarado, o estado de carga mal marcado. Antes esto pasaba
        # inadvertido (caso Tasa_Crecimiento: 418K leidos -> 0 Silver). Se emite
        # ERROR visible y se expone una bandera para el orquestador/auditoria.
        posible_perdida_silenciosa = (
            total_leidos >= 50 and insertados_total == 0 and unique_ids_rechazados == 0
        )
        if posible_perdida_silenciosa:
            _log.error(
                f"[POSIBLE PERDIDA SILENCIOSA] {self.tabla_destino}: {total_leidos} leidos, "
                f"0 insertados y 0 rechazados. Revisar clave de grano / layout Bronce / Estado_Carga."
            )

        # Evaluar nunca hace commit, rollback ni lanza por severidad. El flujo
        # incremental decide después del commit; el reproceso atómico decide
        # antes del commit externo para conservar la fact anterior al fallar.
        if breaker.nivel:
            _log.log(
                logging.WARNING if breaker.nivel == 'WARNING' else logging.ERROR,
                "[CIRCUIT BREAKER %s] %s", breaker.nivel, breaker.mensaje,
            )

        return {
            'Tabla_Destino': self.tabla_destino,
            'Filas_Leidas_Bronce': total_leidos,
            'Filas_Insertadas': self.resumen.get('insertados', 0),
            'Nuevos_Casos_Cuarentena': unique_ids_rechazados,
            'cuarentena': self.resumen.get('cuarentena', []),
            'Bloqueo_Integridad': breaker.nivel == "WARNING",  # Contrato legado, conservar compatibilidad
            'Dependencias_Incumplidas': [],
            'resueltos_por_tiebreaker': self.resumen.get('resueltos_por_tiebreaker', 0),
            'posible_perdida_silenciosa': posible_perdida_silenciosa,
            # El llamador aplica el dictamen a su límite transaccional.
            'breaker_nivel': breaker.nivel,
            'breaker_mensaje': breaker.mensaje if breaker.nivel else None,
            'breaker_porcentaje': porcentaje_rechazo,
            'breaker_total_leidos': total_leidos,
            'breaker_rechazados': unique_ids_rechazados,
        }
