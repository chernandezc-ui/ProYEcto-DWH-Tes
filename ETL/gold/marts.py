"""
marts.py
========
Refresca todos los Marts Gold desde Silver.
Operacion: TRUNCATE + INSERT, siempre desde cero.
Power BI solo conecta a estos Marts.

FIX: Gold no se publica si alguna fact critica fallo en el pipeline.
     refrescar_todos_los_marts() recibe el resumen del ETL y aborta
     si hay errores en las facts bloqueantes.
"""

import logging

from sqlalchemy.engine import Engine
from sqlalchemy import text

_log = logging.getLogger("ETL_Pipeline")

from config.parametros import obtener_int as obtener_param_int
from utils.ejecucion import CONFIG_FACTS

# Escenario "Base" de proyecciones: es el escenario oficial de producción.
def _obtener_escenario_base() -> int:
    return obtener_param_int('ESCENARIO_PROYECCION_OFICIAL', 4)

MARTS = [
    'Gold.Mart_Cosecha',
    'Gold.Mart_Proyecciones',
    'Gold.Mart_Fenologia',
    'Gold.Mart_Clima',
    'Gold.Mart_Pesos_Calibres',
    'Gold.Mart_Administrativo',
    'Gold.Mart_Fisiologia',
    'Gold.Mart_Evaluacion_Vegetativa',
    'Gold.Mart_Tasa_Crecimiento',
    'Gold.Mart_Induccion_Floral',
    'Gold.Mart_Ciclo_Poda',
    'Gold.Mart_Censo_Plantas',
]

# Fallback local — se usa solo si el pipeline no pasa facts_bloqueantes desde DB.
# Fuente de verdad: Config.Parametros_Pipeline / FACTS_BLOQUEANTES_GOLD (pipeline.py).
_FACTS_BLOQUEANTES_FALLBACK: frozenset[str] = frozenset({
    'Fact_Cosecha_SAP',
    'Fact_Conteo_Fenologico',
    'Fact_Evaluacion_Pesos',
    'Fact_Telemetria_Clima',
    'Fact_Fisiologia',
    'Fact_Peladas',
    'Fact_Induccion_Floral',
    'Fact_Tasa_Crecimiento_Brotes',
    'Fact_Ciclo_Poda',
})


def _hay_fallas_criticas(
    resumen_etl: dict,
    facts_bloqueantes: frozenset[str] | set[str] | None = None,
) -> list[str]:
    """
    Detecta facts bloqueantes que terminaron en ERROR.
    Retorna lista de nombres con error (vacia = todo OK).
    Usa facts_bloqueantes del pipeline si se provee; si no, el fallback local.
    """
    conjunto = facts_bloqueantes if facts_bloqueantes is not None else _FACTS_BLOQUEANTES_FALLBACK
    return [nombre for nombre in conjunto if f'{nombre} ERROR' in resumen_etl]


def marts_bloqueados_por_fallas(
    facts_con_error: list[str] | tuple[str, ...] | set[str],
    facts_bloqueantes: frozenset[str] | set[str] | tuple[str, ...] | None = None,
) -> set[str]:
    """
    Marts que NO deben refrescarse porque una fact bloqueante que los alimenta falló.

    - Un mart declarado en CONFIG_FACTS solo se bloquea si falló alguna de SUS facts.
    - Un mart sin fact declarada (p. ej. Mart_Proyecciones, que mezcla varias
      fuentes) no tiene dependencias explícitas: se bloquea ante cualquier falla
      bloqueante (comportamiento conservador).
    """
    conjunto = set(facts_bloqueantes) if facts_bloqueantes is not None else set(_FACTS_BLOQUEANTES_FALLBACK)
    fallidas = set(facts_con_error) & conjunto
    if not fallidas:
        return set()

    marts_con_fact = {mart for meta in CONFIG_FACTS.values() for mart in meta.get('marts', ())}
    bloqueados = {
        mart
        for nombre in fallidas
        for mart in CONFIG_FACTS.get(nombre, {}).get('marts', ())
    }
    bloqueados |= {mart for mart in MARTS if mart not in marts_con_fact}
    return bloqueados


def _truncar(conexion, mart: str) -> None:
    # No-op: los marts ahora son vistas, no se truncan físicamente.
    pass


def refrescar_mart_cosecha(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Cosecha"))
    return _contar(conexion, 'Gold.Mart_Cosecha')


def refrescar_mart_proyecciones(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Proyecciones"))
    return _contar(conexion, 'Gold.Mart_Proyecciones')


def refrescar_mart_fenologia(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Fenologia"))
    return _contar(conexion, 'Gold.Mart_Fenologia')


def refrescar_mart_clima(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Clima"))
    return _contar(conexion, 'Gold.Mart_Clima')


def refrescar_mart_pesos_calibres(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Pesos_Calibres"))
    return _contar(conexion, 'Gold.Mart_Pesos_Calibres')


def refrescar_mart_administrativo(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Administrativo"))
    return _contar(conexion, 'Gold.Mart_Administrativo')


def refrescar_mart_fisiologia(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Fisiologia"))
    return _contar(conexion, 'Gold.Mart_Fisiologia')


def refrescar_mart_evaluacion_vegetativa(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Evaluacion_Vegetativa"))
    return _contar(conexion, 'Gold.Mart_Evaluacion_Vegetativa')


def refrescar_mart_tasa_crecimiento(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Tasa_Crecimiento"))
    return _contar(conexion, 'Gold.Mart_Tasa_Crecimiento')


def refrescar_mart_induccion_floral(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Induccion_Floral"))
    return _contar(conexion, 'Gold.Mart_Induccion_Floral')


def refrescar_mart_ciclo_poda(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Ciclo_Poda"))
    return _contar(conexion, 'Gold.Mart_Ciclo_Poda')


def refrescar_mart_peladas(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Peladas"))
    return _contar(conexion, 'Gold.Mart_Peladas')


def _contar(conexion, mart: str) -> int:
    resultado = conexion.execute(text(f'SELECT COUNT(*) FROM {mart}'))
    return resultado.scalar()


def refrescar_mart_censo_plantas(conexion) -> int:
    conexion.execute(text("SELECT TOP 1 * FROM Gold.Mart_Censo_Plantas"))
    return _contar(conexion, 'Gold.Mart_Censo_Plantas')


FUNCIONES_MARTS = {
    'Gold.Mart_Cosecha': refrescar_mart_cosecha,
    'Gold.Mart_Proyecciones': refrescar_mart_proyecciones,
    'Gold.Mart_Fenologia': refrescar_mart_fenologia,
    'Gold.Mart_Clima': refrescar_mart_clima,
    'Gold.Mart_Pesos_Calibres': refrescar_mart_pesos_calibres,
    'Gold.Mart_Administrativo': refrescar_mart_administrativo,
    'Gold.Mart_Fisiologia': refrescar_mart_fisiologia,
    'Gold.Mart_Evaluacion_Vegetativa': refrescar_mart_evaluacion_vegetativa,
    'Gold.Mart_Tasa_Crecimiento': refrescar_mart_tasa_crecimiento,
    'Gold.Mart_Induccion_Floral': refrescar_mart_induccion_floral,
    'Gold.Mart_Ciclo_Poda': refrescar_mart_ciclo_poda,
    'Gold.Mart_Censo_Plantas': refrescar_mart_censo_plantas,
}


def refrescar_marts_seleccionados(
    engine: Engine,
    marts: list[str] | tuple[str, ...],
    resumen_etl: dict | None = None,
    facts_bloqueantes: frozenset[str] | set[str] | None = None,
    marts_omitidos: frozenset[str] | set[str] | None = None,
) -> dict:
    """
    Refresca solo los marts solicitados.
    facts_bloqueantes: conjunto activo del pipeline (desde DB); si None usa fallback local.
    marts_omitidos: marts que no deben refrescarse (ver marts_bloqueados_por_fallas).
    """
    marts_set = set(marts) - set(marts_omitidos or ())
    marts_solicitados = [mart for mart in MARTS if mart in marts_set]
    if not marts_solicitados:
        return {}

    if resumen_etl is not None:
        fallas = _hay_fallas_criticas(resumen_etl, facts_bloqueantes)
        if fallas:
            msg = f'Gold bloqueado - facts con error: {fallas}'
            _log.warning('[BLOCK] %s', msg)
            return {'BLOQUEADO': msg}

    resumen = {}
    with engine.begin() as conexion:
        for mart in marts_solicitados:
            _truncar(conexion, mart)

        for mart in marts_solicitados:
            filas = FUNCIONES_MARTS[mart](conexion)
            resumen[mart] = filas
            _log.info('[OK] %s: %s filas', mart, filas)

    return resumen


def refrescar_todos_los_marts(
    engine: Engine,
    resumen_etl: dict | None = None,
    facts_bloqueantes: frozenset[str] | set[str] | None = None,
    marts_omitidos: frozenset[str] | set[str] | None = None,
) -> dict:
    """
    Refresca todos los Marts Gold en orden. TRUNCATE + INSERT, siempre desde cero.
    facts_bloqueantes: conjunto activo del pipeline (desde DB); si None usa fallback local.
    marts_omitidos: marts que no deben refrescarse (ver marts_bloqueados_por_fallas).
    """
    if resumen_etl is not None:
        fallas = _hay_fallas_criticas(resumen_etl, facts_bloqueantes)
        if fallas:
            msg = f'Gold bloqueado - facts con error: {fallas}'
            _log.warning('[BLOCK] %s', msg)
            return {'BLOQUEADO': msg}

    resumen = {}
    omitidos = set(marts_omitidos or ())

    with engine.begin() as conexion:
        for mart in MARTS:
            if mart not in omitidos:
                _truncar(conexion, mart)

        for mart, funcion in FUNCIONES_MARTS.items():
            if mart in omitidos:
                continue
            filas = funcion(conexion)
            resumen[mart] = filas
            _log.info('[OK] %s: %s filas', mart, filas)

    return resumen
