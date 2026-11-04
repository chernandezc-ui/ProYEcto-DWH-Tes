"""Orquestación de proyecciones: validar, leer, calcular y guardar.

El cálculo puro vive en dominio.proyecciones. ejecutar_proyeccion conserva
el contrato existente de calcular y persistir; también puede utilizarse el
calculador puro directamente para obtener resultados sin efectos externos.
"""

from __future__ import annotations

import asyncio

import pandas as pd

from dominio.proyecciones import (
    DECAY_FACTOR,
    DELTA_PRODUCTIVAS,
    ESTADOS_POR_SEMANA,
    ID_ESTADO_MAP,
    MATRIZ_INPUTS_DEFAULT,
    PLANTAS_POR_PUNTO,
    ErrorValidacionProyeccion,
    _semanas_en_anio,
    calcular_pct_productivas,
    calcular_proyeccion,
    cerrar_matriz,
    kg_unidad_semana,
    lookup_peso_baya,
    normalizar_matriz_inputs,
    preparar_parametros,
    validar_matriz_inputs,
)
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger
import repositorios.repo_proyecciones as repo

# Reexportar los helpers anteriores conserva consumidores del módulo de servicio.
log = obtener_logger(__name__)
_CLAVE_MATRIZ = 'PROY_SIXWEEK_MATRIZ_INPUTS'


async def guardar_resultado_proyeccion(
    df_detalle: pd.DataFrame,
    id_tiempo: int,
    margen_pesimista: float,
    margen_optimista: float,
) -> None:
    """Guardar un detalle calculado con parámetros previamente validados."""
    if df_detalle.empty:
        return
    resumen = await asyncio.to_thread(
        repo.guardar_proyeccion, df_detalle, id_tiempo, margen_pesimista, margen_optimista,
    )
    if (
        not isinstance(resumen, dict)
        or resumen.get('insertados') != len(df_detalle)
        or resumen.get('saltados') != 0
        or resumen.get('errores') != []
    ):
        # No registrar el resumen crudo: sus errores pueden incluir SQL/inputs.
        log.error('Guardado incompleto de proyección', extra={'filas_esperadas': len(df_detalle)})
        raise ErrorBaseDatos('No se pudo guardar completamente la proyección.')


async def ejecutar_proyeccion(
    id_tiempo: int,
    matriz_inputs: dict[str, dict[int, float | None]] | None = None,
    margen_pesimista: float = 0.9906,
    margen_optimista: float = 1.0107,
    modulo: int | None = None,
    variedad: str | None = None,
    condicion: str | None = None,
    fundo: str | None = None,
) -> dict:
    # Validar antes de cualquier lectura, incluso si las fuentes estarían vacías.
    _, matriz = preparar_parametros(id_tiempo, matriz_inputs, margen_pesimista, margen_optimista)
    margen_pesimista, margen_optimista = float(margen_pesimista), float(margen_optimista)
    conteo, plantas, pesos = await asyncio.to_thread(
        repo.extraer_datos_granulares, id_tiempo, modulo, variedad, condicion, fundo,
    )
    resultado = await asyncio.to_thread(
        calcular_proyeccion, conteo, plantas, pesos, id_tiempo,
        matriz, margen_pesimista, margen_optimista,
    )
    await guardar_resultado_proyeccion(
        resultado['df_detalle'], id_tiempo, margen_pesimista, margen_optimista,
    )
    return resultado


async def obtener_matriz_proyeccion() -> dict:
    return await asyncio.to_thread(repo.leer_param_json, _CLAVE_MATRIZ) or {}


async def guardar_matriz_proyeccion(matriz: dict) -> dict:
    normalizada = normalizar_matriz_inputs(matriz)
    guardada = await asyncio.to_thread(
        repo.guardar_param_json, _CLAVE_MATRIZ, normalizada,
        'Matriz de inputs % maduración Six-Week',
    )
    if not guardada:
        raise ErrorBaseDatos('No se pudo guardar la matriz de proyección.')
    return {'ok': True}


async def obtener_fechas_disponibles() -> list[int]:
    return await asyncio.to_thread(repo.obtener_fechas_disponibles)
