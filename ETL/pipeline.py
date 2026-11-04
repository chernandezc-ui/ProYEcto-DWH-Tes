"""
pipeline.py
===========
Orquestador principal del ETL Geographic Phenology.
Único punto de entrada; nada se corre por separado en produccion.

Uso:
    py pipeline.py
    py pipeline.py --modo-ejecucion facts --facts Fact_Telemetria_Clima
"""

import argparse
import sys
from datetime import datetime

from sqlalchemy import text

from config.conexion import limpiar_sesiones_huerfanas, verificar_conexion, obtener_engine
from config.parametros import (
    limpiar_cache as limpiar_params,
    obtener_int as obtener_param_int,
    obtener_lista as obtener_param_lista,
)
from bronce.cargador import ejecutar_carga_bronce
from mdm.lookup import limpiar_cache as limpiar_lookup

from silver.dims.dim_personal import cargar_dim_personal
from silver.dims.dim_geografia import cargar_dim_geografia
from silver.dims.dim_geografia_v2 import cargar_dim_geografia_v2

from silver.facts.fact_cosecha_sap import cargar_fact_cosecha_sap
from silver.facts.fact_conteo_fenologico import cargar_fact_conteo_fenologico
from silver.facts.fact_ciclos_fenologicos import cargar_fact_ciclos_fenologicos
from silver.facts.fact_peladas import cargar_fact_peladas
from silver.facts.fact_telemetria_clima import cargar_fact_telemetria_clima
from silver.facts.fact_evaluacion_pesos import cargar_fact_evaluacion_pesos
from silver.facts.fact_tareo import cargar_fact_tareo
from silver.facts.fact_fisiologia import cargar_fact_fisiologia
from silver.facts.fact_floracion import cargar_fact_floracion
from silver.facts.fact_induccion_floral import cargar_fact_induccion_floral
from silver.facts.fact_tasa_crecimiento_brotes import cargar_fact_tasa_crecimiento_brotes
from silver.facts.fact_censo_plantas import cargar_fact_censo_plantas
from silver.facts.fact_ciclo_poda import cargar_fact_ciclo_poda
from silver.facts.fact_evaluacion_vegetativa import cargar_fact_evaluacion_vegetativa
from silver.facts.fact_areas_plantas import cargar_fact_areas_plantas

from gold.marts import refrescar_marts_seleccionados, refrescar_todos_los_marts
from auditoria.log import registrar_inicio, registrar_fin
from utils.ejecucion import (
    DEPENDENCIA_DIM_GEOGRAFIA,
    DEPENDENCIA_DIM_PERSONAL,
    DEPENDENCIA_SP_CAMA_SYNC,
    DEPENDENCIA_SP_CAMA_VALIDACION,
    MODO_EJECUCION_COMPLETO,
    MODO_EJECUCION_FACTS,
    construir_catalogo_facts,
    normalizar_facts_solicitadas,
    obtener_facts_disponibles,
    obtener_tablas_bronce_por_dependencias,
    resolver_plan_reproceso,
)
from utils.reproceso_atomico import reconstruir_fact_atomica
from utils.metricas import formatear_resumen_fact, normalizar_resultado_fact
from utils.errores import ErrorCircuitBreakerCritico, ErrorCircuitBreakerError


import logging
import threading
from pathlib import Path

class PrettyConsoleFormatter(logging.Formatter):
    COLORS = {
        "INFO": "\033[36m",     # Cyan
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "RESET": "\033[0m"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        # Resumir el mensaje si es The statement has been terminated o error gigante
        msg = record.getMessage()
        if "IntegrityError" in msg and "[SQL:" in msg:
            # Extraer solo la esencia del integrity error
            idx = msg.find("[SQL:")
            if idx > -1:
                # Truncate at [SQL: ...
                msg = msg[:idx].strip() + " (SQL query omitted from console)"

        return f"{color}[{ts}] [{record.levelname}] {msg}{reset}"

def setup_etl_logger():
    logger = logging.getLogger("ETL_Pipeline")
    logger.setLevel(logging.INFO)
    
    # Prevenir que agregue multiples handlers si se llama varias veces
    if logger.handlers:
        return logger

    # 1. Consola Bonita
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(PrettyConsoleFormatter())
    logger.addHandler(stream_handler)

    # 2. JSON con timestamp para auditoria — preserva historial de runs (O-3)
    try:
        log_dir = Path("logs")  # relativo a CWD — ejecutar desde raíz del ETL/
        log_dir.mkdir(exist_ok=True)
        ts_nombre = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_run = log_dir / f"etl_{ts_nombre}.json"
        file_handler = logging.FileHandler(ruta_run, mode='w', encoding='utf-8')
        fmt = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "acp-etl", "message": "%(message)s"}'
        file_handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(file_handler)

        # Enlace rápido etl_last_run.json → archivo más reciente
        dest_link = log_dir / "etl_last_run.json"
        try:
            if dest_link.exists() or dest_link.is_symlink():
                dest_link.unlink()
            dest_link.symlink_to(ruta_run.name)
        except (OSError, NotImplementedError):
            # En Windows sin permisos de symlink, copiar el archivo como fallback
            try:
                import shutil
                shutil.copy2(str(ruta_run), str(dest_link))
            except Exception:
                logger.warning("No se pudo crear enlace ni copia de %s → %s", ruta_run, dest_link)
    except Exception as error:
        logger.warning("No se pudo crear file_handler de auditoria: %s", error)

    return logger

etl_logger = setup_etl_logger()

def _imprimir(msg: str = ""):
    txt = str(msg).strip()
    if txt and not txt.startswith("=="):
        etl_logger.info(txt)




CATALOGO_FACTS = construir_catalogo_facts({
    'Fact_Cosecha_SAP':           cargar_fact_cosecha_sap,
    'Fact_Conteo_Fenologico':     cargar_fact_conteo_fenologico,
    'Fact_Ciclos_Fenologicos':     cargar_fact_ciclos_fenologicos,
    'Fact_Peladas':               cargar_fact_peladas,
    'Fact_Telemetria_Clima':      cargar_fact_telemetria_clima,
    'Fact_Evaluacion_Pesos':      cargar_fact_evaluacion_pesos,
    'Fact_Tareo':                 cargar_fact_tareo,
    'Fact_Fisiologia':            cargar_fact_fisiologia,
    'Fact_Floracion':             cargar_fact_floracion,
    'Fact_Induccion_Floral':      cargar_fact_induccion_floral,
    'Fact_Tasa_Crecimiento_Brotes': cargar_fact_tasa_crecimiento_brotes,
    'Fact_Censo_Plantas':         cargar_fact_censo_plantas,
    'Fact_Ciclo_Poda':            cargar_fact_ciclo_poda,
    'Fact_Evaluacion_Vegetativa': cargar_fact_evaluacion_vegetativa,
    'Fact_Areas_Plantas':         cargar_fact_areas_plantas,
})


# M9 — Whitelist de tablas permitidas para SQL dinámico.
# Incluye tablas destino Silver y fuentes Bronce declaradas en el catálogo.
_TABLAS_PERMITIDAS: frozenset[str] = frozenset(
    meta['tabla_destino']
    for meta in CATALOGO_FACTS.values()
) | frozenset(
    tabla
    for meta in CATALOGO_FACTS.values()
    for tabla in meta.get('fuentes_bronce', ())
)


def _validar_tabla(tabla: str) -> None:
    """Verifica que la tabla sea una de las permitidas por el catálogo."""
    if tabla not in _TABLAS_PERMITIDAS:
        raise ValueError(f"Tabla '{tabla}' no está en el catálogo de facts permitidos.")


DEFAULT_CAMA_MIN_PERMITIDA = 0        # mínimo lógico de camas por geografía
DEFAULT_CAMA_MAX_PERMITIDA = 100      # máximo operacional; valores mayores se rechazan
DEFAULT_MAX_CAMAS_POR_GEOGRAFIA = 100  # límite de camas distintas permitidas por unidad geográfica
DEFAULT_SP_CAMA_MODO_APLICAR = 1      # 1 = aplicar cambios en BD; 0 = dry-run solo lectura
DEFAULT_ESTADOS_BLOQUEANTES_CALIDAD_CAMA = ('RIESGO_CONTAMINACION',)
DEFAULT_TABLAS_BRONCE_SP_CAMA = tuple(
    obtener_tablas_bronce_por_dependencias((
        DEPENDENCIA_SP_CAMA_SYNC,
        DEPENDENCIA_SP_CAMA_VALIDACION,
    ))
)
DEFAULT_FACTS_BLOQUEANTES_GOLD = tuple(CATALOGO_FACTS.keys())


def _deduplicar_textos(valores: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    vistos: list[str] = []
    for valor in valores:
        texto = str(valor).strip()
        if texto and texto not in vistos:
            vistos.append(texto)
    return tuple(vistos)


def _cargar_configuracion_operativa() -> dict:
    facts_bloqueantes_raw = obtener_param_lista(
        'FACTS_BLOQUEANTES_GOLD',
        DEFAULT_FACTS_BLOQUEANTES_GOLD,
    )
    if len(facts_bloqueantes_raw) == 1 and facts_bloqueantes_raw[0] == '*':
        facts_bloqueantes = tuple(CATALOGO_FACTS.keys())
    else:
        facts_bloqueantes = tuple(normalizar_facts_solicitadas(facts_bloqueantes_raw))
        if not facts_bloqueantes:
            facts_bloqueantes = DEFAULT_FACTS_BLOQUEANTES_GOLD

    estados_bloqueantes = tuple(
        str(item).strip().upper()
        for item in obtener_param_lista(
            'ESTADOS_BLOQUEANTES_CALIDAD_CAMA',
            DEFAULT_ESTADOS_BLOQUEANTES_CALIDAD_CAMA,
        )
        if str(item).strip()
    ) or DEFAULT_ESTADOS_BLOQUEANTES_CALIDAD_CAMA

    return {
        'cama_min_permitida': obtener_param_int('CAMA_MIN_PERMITIDA', DEFAULT_CAMA_MIN_PERMITIDA),
        'cama_max_permitida': obtener_param_int('CAMA_MAX_PERMITIDA', DEFAULT_CAMA_MAX_PERMITIDA),
        'max_camas_por_geografia': obtener_param_int(
            'MAX_CAMAS_POR_GEOGRAFIA',
            DEFAULT_MAX_CAMAS_POR_GEOGRAFIA,
        ),
        'sp_cama_modo_aplicar': obtener_param_int(
            'SP_CAMA_MODO_APLICAR',
            DEFAULT_SP_CAMA_MODO_APLICAR,
        ),
        'tablas_bronce_sp_cama': _deduplicar_textos(
            obtener_param_lista(
                'TABLAS_BRONCE_SP_CAMA',
                DEFAULT_TABLAS_BRONCE_SP_CAMA,
            )
        ),
        'facts_bloqueantes_gold': facts_bloqueantes,
        'estados_bloqueantes_calidad_cama': _deduplicar_textos(estados_bloqueantes),
    }


def _gold_debe_bloquearse(
    facts_con_error: list[str] | tuple[str, ...],
    facts_bloqueantes_gold: list[str] | tuple[str, ...],
) -> bool:
    return bool(set(facts_con_error).intersection(facts_bloqueantes_gold))


def _estado_calidad_cama_bloqueante(
    estado_calidad: str | None,
    estados_bloqueantes: list[str] | tuple[str, ...],
) -> bool:
    return str(estado_calidad or '').strip().upper() in {
        str(item).strip().upper()
        for item in estados_bloqueantes
        if str(item).strip()
    }


class ErrorEjecucionPipeline(RuntimeError):
    def __init__(self, errores: list[str]) -> None:
        self.errores = list(errores)
        super().__init__(' | '.join(self.errores))




def _encabezado() -> datetime:
    inicio = datetime.now()
    _imprimir()
    _imprimir('=' * 60)
    _imprimir('  DWH Geographic Phenology - ETL Pipeline')
    _imprimir(f'  Inicio: {inicio.strftime("%Y-%m-%d %H:%M:%S")}')
    _imprimir('=' * 60)
    _imprimir()
    return inicio


def _paso(numero: int, total: int, descripcion: str) -> None:
    """Imprime el encabezado de un paso del pipeline: '[01/23] Descripción'."""
    _imprimir(f'[{numero:02d}/{total}] {descripcion}')


def _resumen_fact(resultado: dict) -> None:
    for linea in formatear_resumen_fact(resultado):
        _imprimir(linea)


def _resumen_final(inicio: datetime, resumen: dict) -> None:
    fin = datetime.now()
    duracion = round((fin - inicio).total_seconds(), 2)
    _imprimir()
    _imprimir('=' * 60)
    _imprimir('  RESUMEN FINAL')
    _imprimir('=' * 60)
    for clave, valor in resumen.items():
        _imprimir(f'  {clave:45} {valor}')
    _imprimir(f'  {"Duracion total":45} {duracion}s')
    _imprimir('=' * 60)
    _imprimir()


def _ejecutar_sp_upsert_cama(
    engine,
    modo_aplicar: int = DEFAULT_SP_CAMA_MODO_APLICAR,
    cama_min_permitida: int = DEFAULT_CAMA_MIN_PERMITIDA,
    cama_max_permitida: int = DEFAULT_CAMA_MAX_PERMITIDA,
) -> dict:
    with engine.begin() as conexion:
        fila = conexion.execute(text("""
            EXEC Silver.sp_Upsert_Cama_Desde_Bronce
                @Modo_Aplicar = :modo_aplicar,
                @Cama_Min_Permitida = :cama_min_permitida,
                @Cama_Max_Permitida = :cama_max_permitida
        """), {
            'modo_aplicar': int(modo_aplicar),
            'cama_min_permitida': int(cama_min_permitida),
            'cama_max_permitida': int(cama_max_permitida),
        }).fetchone()

    if not fila:
        return {
            'Filas_Bronce_Leidas': 0,
            'Filas_Evaluadas': 0,
            'Combinaciones_Aptas_Distintas': 0,
            'Insert_Catalogo_Real': 0,
            'Insert_Bridge_Real': 0,
        }
    return dict(fila._mapping)


def _ejecutar_sp_validar_camas(
    engine,
    cama_max_permitida: int = DEFAULT_CAMA_MAX_PERMITIDA,
    max_camas_por_geografia: int = DEFAULT_MAX_CAMAS_POR_GEOGRAFIA,
) -> dict:
    with engine.connect() as conexion:
        fila = conexion.execute(text("""
            EXEC Silver.sp_Validar_Calidad_Camas
                @Cama_Max_Permitida = :cama_max_permitida,
                @Max_Camas_Por_Geografia = :max_camas_por_geografia
        """), {
            'cama_max_permitida': int(cama_max_permitida),
            'max_camas_por_geografia': int(max_camas_por_geografia),
        }).fetchone()

    if not fila:
        return {
            'Cama_Fuera_Regla': None,
            'Geografias_Saturadas': None,
            'Estado_Calidad_Cama': 'SIN_RESULTADO',
        }
    return dict(fila._mapping)


def _ejecutar_sp_sincronizar_campanas(engine) -> None:
    with engine.begin() as conexion:
        conexion.execute(text("EXEC Silver.sp_Sincronizar_Periodos_Campana"))


def _sincronizar_bridges_geografia(engine) -> None:
    sps = [
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Vegetativa;",
        "EXEC MDM.usp_Popular_Bridge_Geo_Campana_Condicion_Cosecha;",
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Conteo_Fenologico;",
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Evaluacion_Pesos;",
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Censo_Plantas;",
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Floracion;",
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Fisiologia;",
        "EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Tasa_Crecimiento;"
    ]
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conexion:
        for sp in sps:
            try:
                conexion.execute(text(sp))
            except Exception as e:
                # If a specific SP fails, log it and continue so the rest can run
                _imprimir(f'  [ADVERTENCIA] Fallo al ejecutar {sp}: {e}')


def _obtener_contexto_sql(engine) -> dict:
    with engine.connect() as conexion:
        fila = conexion.execute(text("""
            SELECT
                CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(128)) AS servidor,
                DB_NAME() AS base_datos
        """)).fetchone()
    if not fila:
        return {'servidor': 'DESCONOCIDO', 'base_datos': 'DESCONOCIDA'}
    return dict(fila._mapping)


def _contar_bridge_geografia_cama(engine) -> int:
    with engine.connect() as conexion:
        return int(conexion.execute(text("""
            SELECT COUNT(*)
            FROM Silver.Dim_Geografia
            WHERE ID_Cama_Catalogo <> 0
        """)).scalar() or 0)


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Pipeline ETL ACP')
    parser.add_argument(
        '--modo-ejecucion',
        choices=[MODO_EJECUCION_COMPLETO, MODO_EJECUCION_FACTS],
        default=MODO_EJECUCION_COMPLETO,
    )
    parser.add_argument(
        '--facts',
        nargs='+',
        default=None,
        help=f"Facts a reprocesar. Disponibles: {', '.join(obtener_facts_disponibles())}",
    )
    parser.add_argument(
        '--sin-dependencias',
        action='store_true',
        help='Omite dependencias previas del reproceso parcial.',
    )
    parser.add_argument(
        '--sin-gold',
        action='store_true',
        help='Omite el refresh de marts Gold afectados.',
    )
    parser.add_argument(
        '--sin-relectura-bronce',
        action='store_true',
        help='No reabre filas PROCESADO/RECHAZADO en Bronce antes del reproceso.',
    )
    return parser.parse_args()


def _contar_filas_tabla(engine, tabla: str) -> int:
    _validar_tabla(tabla)
    with engine.connect() as conexion:
        return int(conexion.execute(text(f'SELECT COUNT(*) FROM {tabla}')).scalar() or 0)


def _limpiar_fact_destino(engine, tabla_destino: str) -> int:
    _validar_tabla(tabla_destino)
    filas_antes = _contar_filas_tabla(engine, tabla_destino)
    with engine.begin() as conexion:
        conexion.execute(text(f'DELETE FROM {tabla_destino}'))
    return filas_antes


def _reiniciar_estado_carga_bronce(engine, tabla_bronce: str) -> int:
    _validar_tabla(tabla_bronce)
    with engine.begin() as conexion:
        resultado = conexion.execute(text(f"""
            UPDATE {tabla_bronce}
            SET Estado_Carga = 'CARGADO'
            WHERE Estado_Carga IN ('PROCESADO', 'RECHAZADO')
        """))
        return int(resultado.rowcount or 0)


def _ejecutar_dependencia_reproceso(
    engine,
    dependencia: str,
    resumen: dict,
    config_operativa: dict,
) -> None:
    if dependencia == DEPENDENCIA_DIM_PERSONAL:
        r = cargar_dim_personal(engine)
        resumen['Dim_Personal insertados'] = r['insertados']
        resumen['Dim_Personal actualizados'] = r['actualizados']
        return

    if dependencia == DEPENDENCIA_DIM_GEOGRAFIA:
        r = cargar_dim_geografia_v2(engine)
        resumen['Dim_Geografia insertados'] = r.get('insertados', 0)
        resumen['Dim_Geografia cerrados'] = r.get('cerrados', 0)
        resumen['Dim_Geografia sin_cambios'] = r.get('sin_cambios', 0)
        return

    if dependencia == DEPENDENCIA_SP_CAMA_SYNC:
        bridge_antes = _contar_bridge_geografia_cama(engine)
        r = _ejecutar_sp_upsert_cama(
            engine,
            modo_aplicar=config_operativa['sp_cama_modo_aplicar'],
            cama_min_permitida=config_operativa['cama_min_permitida'],
            cama_max_permitida=config_operativa['cama_max_permitida'],
        )
        bridge_despues = _contar_bridge_geografia_cama(engine)
        resumen['SP_Cama filas evaluadas'] = r.get('Filas_Evaluadas', 0)
        resumen['SP_Cama aptas'] = r.get('Combinaciones_Aptas_Distintas', 0)
        resumen['SP_Cama insert catalogo'] = r.get('Insert_Catalogo_Real', 0)
        resumen['SP_Cama insert bridge'] = r.get('Insert_Bridge_Real', 0)
        resumen['Bridge camas antes'] = bridge_antes
        resumen['Bridge camas despues'] = bridge_despues
        if r.get('Combinaciones_Aptas_Distintas', 0) > 0 and bridge_despues == 0:
            raise RuntimeError(
                'SP_Cama inconsistente: hay combinaciones aptas pero Silver.Bridge_Geografia_Cama sigue en 0.'
            )
        return

    if dependencia == DEPENDENCIA_SP_CAMA_VALIDACION:
        r = _ejecutar_sp_validar_camas(
            engine,
            cama_max_permitida=config_operativa['cama_max_permitida'],
            max_camas_por_geografia=config_operativa['max_camas_por_geografia'],
        )
        resumen['SP_Cama fuera regla'] = r.get('Cama_Fuera_Regla')
        resumen['SP_Cama geo saturadas'] = r.get('Geografias_Saturadas')
        resumen['SP_Cama estado calidad'] = r.get('Estado_Calidad_Cama')
        if _estado_calidad_cama_bloqueante(
            r.get('Estado_Calidad_Cama'),
            config_operativa['estados_bloqueantes_calidad_cama'],
        ):
            raise RuntimeError(f"Calidad cama en estado {r.get('Estado_Calidad_Cama')}.")
        return

    raise ValueError(f'Dependencia no soportada: {dependencia}')


def _preparar_fact_reproceso(engine, nombre_fact: str, meta_fact: dict, forzar_relectura_bronce: bool) -> dict:
    if not forzar_relectura_bronce and meta_fact.get('releer_bronce_por_estado', True):
        raise ValueError(
            f'{nombre_fact} requiere relectura de Bronce para reconstruirse sin perder historia.'
        )

    filas_bronce_reabiertas = 0
    if forzar_relectura_bronce and meta_fact.get('releer_bronce_por_estado', True):
        for tabla_bronce in meta_fact.get('fuentes_bronce', ()):
            filas_bronce_reabiertas += _reiniciar_estado_carga_bronce(engine, tabla_bronce)

    filas_destino_eliminadas = _limpiar_fact_destino(engine, meta_fact['tabla_destino'])
    return {
        'filas_bronce_reabiertas': filas_bronce_reabiertas,
        'filas_destino_eliminadas': filas_destino_eliminadas,
    }


def _registrar_errores_resumen(resumen: dict, errores: list[str]) -> None:
    resumen['Errores pipeline'] = len(errores)
    for indice, error in enumerate(errores, start=1):
        resumen[f'Pipeline error {indice}'] = error


def _ejecutar_fact(nombre: str, tabla_destino: str, funcion, engine, resumen: dict) -> str | None:
    id_log = registrar_inicio(tabla_destino, f'PIPELINE_FACT:{nombre}')
    r = {'insertados': 0, 'rechazados': 0, 'cuarentena': []}

    try:
        r = funcion(engine)
        r = normalizar_resultado_fact(r)
        _resumen_fact(r)
        resumen[nombre] = r.get('insertados', 0)
        resumen[f'{nombre} leidos'] = r.get('leidos', 0)
        resumen[f'{nombre} rechazados'] = r.get('rechazados', 0)
        resumen[f'{nombre} rechazo pct'] = f"{r.get('tasa_rechazo_pct', 0.0)}%"
        if r.get('posible_perdida_silenciosa'):
            resumen[f'{nombre} ALERTA'] = 'POSIBLE_PERDIDA_SILENCIOSA (0 insertados y 0 rechazados con Bronce leido)'
        if r.get('resueltos_por_tiebreaker', 0) > 0:
            resumen[f'{nombre} resueltos_por_tiebreaker'] = r.get('resueltos_por_tiebreaker', 0)
        for indice, item in enumerate(r.get('motivos_principales', []), start=1):
            resumen[f'{nombre} motivo {indice}'] = f"{item['motivo']} ({item['cantidad']})"

        # ── Bug 2 (2026-05-26): lanzar el breaker DESPUES de que la
        # transaccion del Fact haya commiteado. _base_processor.finalizar_proceso
        # ya NO lanza internamente; expone breaker_nivel / breaker_mensaje en
        # el resultado. Aqui replicamos el contrato externo previo (CRITICO ->
        # ErrorCircuitBreakerCritico, ERROR -> ErrorCircuitBreakerError) pero
        # con Silver YA persistida (no se pierde trabajo).
        nivel_breaker = r.get('breaker_nivel') if isinstance(r, dict) else None
        if nivel_breaker in ('CRITICO', 'ERROR'):
            mensaje_breaker = r.get('breaker_mensaje') or f'Circuit breaker {nivel_breaker}'
            resumen[f'{nombre} CIRCUIT_BREAKER'] = mensaje_breaker
            registrar_fin(id_log, {
                'estado': 'CB_CRITICO' if nivel_breaker == 'CRITICO' else 'CB_ERROR',
                'filas': r.get('insertados', 0),
                'filas_leidas': r.get('leidos', 0),
                'rechazadas': r.get('rechazados', 0),
                'mensaje': mensaje_breaker,
            })
            if nivel_breaker == 'CRITICO':
                raise ErrorCircuitBreakerCritico(mensaje_breaker)
            raise ErrorCircuitBreakerError(mensaje_breaker)

        registrar_fin(id_log, {
            'estado': 'OK',
            'filas': r.get('insertados', 0),
            'filas_leidas': r.get('leidos', 0),
            'rechazadas': r.get('rechazados', 0),
            'mensaje': '',
        })
        return None
    except ErrorCircuitBreakerCritico as error:
        # Rechazo >= LIMITE_CRITICO: abortar el pipeline completo, no continuar
        _imprimir(f'  CIRCUIT BREAKER CRITICO en {nombre}: {error}')
        resumen[f'{nombre} CIRCUIT_BREAKER'] = str(error)
        registrar_fin(id_log, {
            'estado': 'CB_CRITICO',  # Auditoria.Log_Carga.Estado_Proceso VARCHAR(20)
            'filas': 0,
            'rechazadas': r.get('rechazados', 0),
            'mensaje': str(error),
        })
        raise
    except Exception as error:
        # Algunas excepciones (pyodbc, SQLAlchemy) tienen str(error) vacio.
        # Incluir tipo + traceback en log para no perder pista.
        import traceback as _tb
        descripcion = str(error) or type(error).__name__
        mensaje_error = f'{nombre}: {descripcion}'
        _imprimir(f'  ERROR en {mensaje_error}')
        _imprimir(_tb.format_exc())
        resumen[f'{nombre} ERROR'] = descripcion
        registrar_fin(id_log, {
            'estado': 'ERROR',
            'filas': 0,
            'rechazadas': r.get('rechazados', 0),
            'mensaje': descripcion,
        })
        return mensaje_error


def ejecutar_reproceso_facts(
    facts_solicitadas: list[str] | tuple[str, ...],
    incluir_dependencias: bool = True,
    refrescar_gold: bool = True,
    forzar_relectura_bronce: bool = True,
) -> None:
    inicio = _encabezado()
    engine = obtener_engine()
    plan = resolver_plan_reproceso(
        facts_solicitadas=facts_solicitadas,
        incluir_dependencias=incluir_dependencias,
        refrescar_gold=refrescar_gold,
    )
    if not forzar_relectura_bronce:
        facts_incrementales = [
            nombre_fact
            for nombre_fact in plan['facts']
            if CATALOGO_FACTS[nombre_fact].get('releer_bronce_por_estado', True)
        ]
        if facts_incrementales:
            raise ValueError(
                'El reproceso sin relectura de Bronce solo aplica a facts full-read. '
                f'No permitido para: {facts_incrementales}'
            )
    total = 3 + len(plan['dependencias']) + len(plan['facts']) + (1 if plan['marts'] else 0)
    resumen = {
        'Modo ejecucion': 'REPROCESO_FACTS',
        'Facts solicitadas': ', '.join(plan['facts']),
    }
    errores_pipeline: list[str] = []
    facts_con_error: list[str] = []

    paso_actual = 1
    _paso(paso_actual, total, 'Verificando conexion SQL Server...')
    if not verificar_conexion():
        _imprimir('Sin conexion. Pipeline detenido.')
        sys.exit(1)
    limpiar_sesiones_huerfanas()
    contexto_sql = _obtener_contexto_sql(engine)
    resumen['Servidor SQL'] = contexto_sql.get('servidor')
    resumen['Base SQL'] = contexto_sql.get('base_datos')

    paso_actual += 1
    _paso(paso_actual, total, 'Limpiando cache...')
    limpiar_lookup()
    limpiar_params()
    config_operativa = _cargar_configuracion_operativa()

    for dependencia in plan['dependencias']:
        paso_actual += 1
        _paso(paso_actual, total, f'Ejecutando dependencia {dependencia}...')
        _ejecutar_dependencia_reproceso(engine, dependencia, resumen, config_operativa)

    # Serializar los reruns: varias facts pueden compartir una fuente Bronce.
    # Cada reconstruccion revierte destino, estados y cuarentena si falla.
    for nombre_fact in plan['facts']:
        paso_actual += 1
        meta_fact = CATALOGO_FACTS[nombre_fact]
        _paso(paso_actual, total, f'Reprocesando {nombre_fact} (Atomico)...')

        def cargar_atomico(_engine, nombre=nombre_fact, meta=meta_fact):
            try:
                prep, resultado = reconstruir_fact_atomica(
                    _engine,
                    lambda recurso: _preparar_fact_reproceso(
                        recurso, nombre, meta, forzar_relectura_bronce),
                    lambda recurso: normalizar_resultado_fact(meta['funcion'](recurso)),
                )
                resumen[f'{nombre} bronce reabiertas'] = prep['filas_bronce_reabiertas']
                resumen[f'{nombre} destino limpiado'] = prep['filas_destino_eliminadas']
                return resultado
            finally:
                # Los lookups pueden contener IDs creados por una carga revertida.
                limpiar_lookup()

        error_fact = _ejecutar_fact(
            nombre_fact, meta_fact['tabla_destino'], cargar_atomico, engine, resumen)
        if error_fact:
            errores_pipeline.append(error_fact)
            facts_con_error.append(nombre_fact)

    if plan['marts']:
        paso_actual += 1
        if _gold_debe_bloquearse(facts_con_error, config_operativa['facts_bloqueantes_gold']):
            _paso(paso_actual, total, 'Omitiendo Marts Gold por errores previos...')
            resumen['Gold estado'] = 'OMITIDO_POR_ERROR_EN_FACTS'
        else:
            _paso(paso_actual, total, 'Refrescando Marts Gold impactados...')
            try:
                resumen_marts = refrescar_marts_seleccionados(engine, plan['marts'], resumen_etl=resumen, facts_bloqueantes=frozenset(config_operativa['facts_bloqueantes_gold']))
                for mart, valor in resumen_marts.items():
                    resumen[mart] = valor if isinstance(valor, int) else valor
            except Exception as error:
                mensaje_error = f'Gold: {error}'
                _imprimir(f'  ERROR en {mensaje_error}')
                resumen['Gold ERROR'] = str(error)
                errores_pipeline.append(mensaje_error)

    paso_actual += 1
    _paso(paso_actual, total, 'Finalizando...')
    if errores_pipeline:
        _registrar_errores_resumen(resumen, errores_pipeline)
    _resumen_final(inicio, resumen)
    if errores_pipeline:
        raise ErrorEjecucionPipeline(errores_pipeline)


def ejecutar() -> None:
    inicio = _encabezado()
    engine = obtener_engine()
    total = 23
    resumen = {}
    errores_pipeline: list[str] = []
    facts_con_error: list[str] = []

    _paso(1, total, 'Verificando conexion SQL Server...')
    if not verificar_conexion():
        _imprimir('Sin conexion. Pipeline detenido.')
        sys.exit(1)
    limpiar_sesiones_huerfanas()
    contexto_sql = _obtener_contexto_sql(engine)
    resumen['Servidor SQL'] = contexto_sql.get('servidor')
    resumen['Base SQL'] = contexto_sql.get('base_datos')

    _paso(2, total, 'Verificando esquema de objetos criticos en DB...')
    try:
        from utils.verificacion_esquema import verificar_objetos_criticos
        verificar_objetos_criticos(engine)
    except RuntimeError as _e_esquema:
        _imprimir(str(_e_esquema))
        raise ErrorEjecucionPipeline([f'Verificacion de esquema fallida: {_e_esquema}'])

    _paso(3, total, 'Limpiando cache...')
    limpiar_lookup()
    limpiar_params()
    config_operativa = _cargar_configuracion_operativa()

    _paso(4, total, 'Cargando archivos Excel a Bronce...')
    resultados_bronce = ejecutar_carga_bronce()
    resumen['Bronce archivos'] = len(resultados_bronce)
    resumen['Bronce filas'] = sum(r['filas'] for r in resultados_bronce)
    tablas_bronce_ok = {
        r.get('tabla')
        for r in resultados_bronce
        if r.get('estado') == 'OK'
    }
    error_critico_bronce = next((r for r in resultados_bronce if r.get('critico')), None)
    if error_critico_bronce:
        resumen['Bronce error critico'] = error_critico_bronce.get('codigo', 'ERROR_CRITICO')
        resumen['Bronce detalle'] = error_critico_bronce.get('mensaje', '')
        _imprimir('  ERROR CRITICO EN BRONCE. Pipeline detenido antes de Silver/Gold.')
        _imprimir(f'  {error_critico_bronce.get("mensaje", "")}')
        _resumen_final(inicio, resumen)
        raise ErrorEjecucionPipeline([
            f'Bronce critico: {error_critico_bronce.get("mensaje", "")}'
        ])

    _paso(5, total, 'Cargando Dim_Personal (SCD1)...')
    r = cargar_dim_personal(engine)
    resumen['Dim_Personal insertados'] = r['insertados']
    resumen['Dim_Personal actualizados'] = r['actualizados']

    _paso(6, total, 'Sincronizando Dim_Geografia (arquitectura catálogos)...')
    r = cargar_dim_geografia_v2(engine)
    resumen['Dim_Geografia insertados'] = r.get('insertados', 0)
    resumen['Dim_Geografia cerrados'] = r.get('cerrados', 0)
    resumen['Dim_Geografia sin_cambios'] = r.get('sin_cambios', 0)

    _paso(7, total, 'Sincronizando catalogo/bridge de cama via SP...')
    try:
        if tablas_bronce_ok & set(config_operativa['tablas_bronce_sp_cama']):
            bridge_antes = _contar_bridge_geografia_cama(engine)
            r = _ejecutar_sp_upsert_cama(
                engine,
                modo_aplicar=config_operativa['sp_cama_modo_aplicar'],
                cama_min_permitida=config_operativa['cama_min_permitida'],
                cama_max_permitida=config_operativa['cama_max_permitida'],
            )
            bridge_despues = _contar_bridge_geografia_cama(engine)
            resumen['SP_Cama filas evaluadas'] = r.get('Filas_Evaluadas', 0)
            resumen['SP_Cama aptas'] = r.get('Combinaciones_Aptas_Distintas', 0)
            resumen['SP_Cama insert catalogo'] = r.get('Insert_Catalogo_Real', 0)
            resumen['SP_Cama insert bridge'] = r.get('Insert_Bridge_Real', 0)
            resumen['Bridge camas antes'] = bridge_antes
            resumen['Bridge camas despues'] = bridge_despues

            if r.get('Combinaciones_Aptas_Distintas', 0) > 0 and bridge_despues == 0:
                mensaje = (
                    'SP_Cama inconsistente: hay combinaciones aptas pero '
                    'Silver.Bridge_Geografia_Cama sigue en 0.'
                )
                _imprimir(f'  ERROR: {mensaje}')
                resumen['SP_Cama inconsistencia'] = mensaje
                raise ErrorEjecucionPipeline([f'SP_Cama inconsistencia: {mensaje}'])
        else:
            resumen['SP_Cama estado'] = 'OMITIDO_SIN_TABLAS_CON_CAMA_EN_ESTA_CORRIDA'
            _imprimir('  SP_Cama omitido: no ingresaron tablas Bronce con cama en esta corrida.')
    except ErrorEjecucionPipeline:
        raise
    except Exception as error:
        _imprimir(f'  ERROR en SP_Cama_Upsert: {error}')
        resumen['SP_Cama_Upsert ERROR'] = str(error)
        raise ErrorEjecucionPipeline([f'SP_Cama_Upsert: {error}']) from error

    _paso(8, total, 'Validando calidad de cama via SP...')
    try:
        r = _ejecutar_sp_validar_camas(
            engine,
            cama_max_permitida=config_operativa['cama_max_permitida'],
            max_camas_por_geografia=config_operativa['max_camas_por_geografia'],
        )
        resumen['SP_Cama fuera regla'] = r.get('Cama_Fuera_Regla')
        resumen['SP_Cama geo saturadas'] = r.get('Geografias_Saturadas')
        resumen['SP_Cama estado calidad'] = r.get('Estado_Calidad_Cama')
        if _estado_calidad_cama_bloqueante(
            r.get('Estado_Calidad_Cama'),
            config_operativa['estados_bloqueantes_calidad_cama'],
        ):
            _imprimir(f"  ERROR: Calidad cama en estado {r.get('Estado_Calidad_Cama')}. Pipeline detenido.")
            raise ErrorEjecucionPipeline([
                f"Calidad cama bloqueante: {r.get('Estado_Calidad_Cama')}"
            ])
    except ErrorEjecucionPipeline:
        raise
    except Exception as error:
        _imprimir(f'  ERROR en SP_Cama_Validacion: {error}')
        resumen['SP_Cama_Validacion ERROR'] = str(error)
        raise ErrorEjecucionPipeline([f'SP_Cama_Validacion: {error}']) from error

    # 1. Separar Fact_Ciclo_Poda y los demás hechos
    resto_facts = {n: mf for n, mf in CATALOGO_FACTS.items() if n != 'Fact_Ciclo_Poda'}
    poda_meta = CATALOGO_FACTS.get('Fact_Ciclo_Poda')

    # 2. Ejecutar Fact_Ciclo_Poda secuencialmente primero
    if poda_meta:
        nombre = 'Fact_Ciclo_Poda'
        numero = int(poda_meta['orden'])
        tabla_destino = poda_meta['tabla_destino']
        funcion = poda_meta['funcion']
        _paso(numero, total, f'Cargando {nombre} (Secuencial)...')
        error_fact = _ejecutar_fact(nombre, tabla_destino, funcion, engine, resumen)
        if error_fact:
            errores_pipeline.append(error_fact)
            facts_con_error.append(nombre)
        else:
            _paso(10, total, 'Sincronizando bridge de campanas via SP...')
            try:
                _ejecutar_sp_sincronizar_campanas(engine)
                resumen['SP_Campanas_Sync'] = 'OK'
                limpiar_lookup()
            except Exception as error:
                _imprimir(f'  ERROR en SP_Sincronizar_Campanas: {error}')
                resumen['SP_Campanas_Sync ERROR'] = str(error)
                errores_pipeline.append(f'SP_Sincronizar_Campanas: {error}')
                facts_con_error.append('SP_Campanas_Sync')

    # 3. Ejecutar los hechos restantes en paralelo
    if resto_facts:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        _imprimir(f"Cargando {len(resto_facts)} hechos en paralelo (max_workers=4)...")

        _resumen_lock = threading.Lock()

        def _ejecutar_fact_paralelo(nombre_f, meta_f):
            thread_res = {}
            err = _ejecutar_fact(nombre_f, meta_f['tabla_destino'], meta_f['funcion'], engine, thread_res)
            return nombre_f, err, thread_res

        with ThreadPoolExecutor(max_workers=4) as executor:
            futuros = {executor.submit(_ejecutar_fact_paralelo, nf, mf): nf for nf, mf in resto_facts.items()}
            for futuro in as_completed(futuros):
                nf = futuros[futuro]
                try:
                    nombre_f, err, thread_res = futuro.result()
                    with _resumen_lock:
                        resumen.update(thread_res)
                    if err:
                        errores_pipeline.append(err)
                        facts_con_error.append(nf)
                except ErrorCircuitBreakerCritico:
                    raise  # propagar circuit breaker sin atrapar
                except Exception as ex:
                    _imprimir(f"  ERROR crítico en hilo de {nf}: {ex}")
                    errores_pipeline.append(f"{nf}: {ex}")
                    facts_con_error.append(nf)


    if _gold_debe_bloquearse(facts_con_error, config_operativa['facts_bloqueantes_gold']):
        _paso(22, total, 'Omitiendo Marts Gold por errores previos...')
        resumen['Gold estado'] = 'OMITIDO_POR_ERROR_EN_FACTS'
    else:
        _paso(21, total, 'Sincronizando Bridges de Geografia y Campana...')
        try:
            _sincronizar_bridges_geografia(engine)
            resumen['Bridges Geografia'] = 'OK'
        except Exception as error:
            _imprimir(f'  ERROR sincronizando Bridges: {error}')
            resumen['Bridges Geografia ERROR'] = str(error)

        _paso(22, total, 'Refrescando Marts Gold...')
        try:
            resumen_marts = refrescar_todos_los_marts(engine, resumen_etl=resumen, facts_bloqueantes=frozenset(config_operativa['facts_bloqueantes_gold']))
            for mart, valor in resumen_marts.items():
                resumen[mart] = valor if isinstance(valor, int) else valor
        except Exception as error:
            mensaje_error = f'Gold: {error}'
            _imprimir(f'  ERROR en {mensaje_error}')
            resumen['Gold ERROR'] = str(error)
            errores_pipeline.append(mensaje_error)

    _paso(23, total, 'Finalizando...')
    if errores_pipeline:
        _registrar_errores_resumen(resumen, errores_pipeline)
    _resumen_final(inicio, resumen)
    if errores_pipeline:
        raise ErrorEjecucionPipeline(errores_pipeline)


if __name__ == '__main__':
    argumentos = _parsear_argumentos()

    if argumentos.modo_ejecucion == MODO_EJECUCION_FACTS:
        ejecutar_reproceso_facts(
            facts_solicitadas=argumentos.facts,
            incluir_dependencias=not argumentos.sin_dependencias,
            refrescar_gold=not argumentos.sin_gold,
            forzar_relectura_bronce=not argumentos.sin_relectura_bronce,
        )
    else:
        ejecutar()
