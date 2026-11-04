"""
metricas.py
===========
Utilidades para normalizar metricas operativas de cada fact del ETL.
"""

from __future__ import annotations

from collections import Counter


def normalizar_resultado_fact(resultado: dict | None) -> dict:
    """
    Homologa el payload devuelto por cada fact para reporte y auditoria.
    """
    resultado = resultado or {}
    # Soporta formato moderno (BaseFactProcessor) y formato legacy (_helpers_fact_comunes)
    insertados = int(resultado.get('insertados') or resultado.get('Filas_Insertadas', 0) or 0)
    rechazados = int(resultado.get('rechazados') or resultado.get('Nuevos_Casos_Cuarentena', 0) or 0)
    cuarentena = list(resultado.get('cuarentena', []) or [])
    leidos = int(resultado.get('leidos') or resultado.get('Filas_Leidas_Bronce', insertados + rechazados) or 0)
    if leidos < insertados + rechazados:
        leidos = insertados + rechazados

    motivos = Counter()
    for item in cuarentena:
        motivo = str(item.get('motivo', 'SIN_MOTIVO')).strip() if isinstance(item, dict) else 'SIN_MOTIVO'
        motivos[motivo or 'SIN_MOTIVO'] += 1

    top_motivos = [
        {'motivo': motivo, 'cantidad': cantidad}
        for motivo, cantidad in motivos.most_common(3)
    ]

    tasa_rechazo_pct = round((rechazados / leidos) * 100.0, 2) if leidos > 0 else 0.0
    resueltos_tiebreaker = int(resultado.get('resueltos_por_tiebreaker', 0) or 0)

    return {
        **resultado,
        'leidos': leidos,
        'insertados': insertados,
        'rechazados': rechazados,
        'cuarentena': cuarentena,
        'cuarentena_total': len(cuarentena),
        'motivos_principales': top_motivos,
        'tasa_rechazo_pct': tasa_rechazo_pct,
        'resueltos_por_tiebreaker': resueltos_tiebreaker,
    }


def formatear_resumen_fact(resultado: dict) -> list[str]:
    """
    Retorna lineas listas para consola con metricas operativas estandarizadas.
    """
    lineas = [
        (
            f"       -> {resultado['leidos']} leidos | "
            f"{resultado['insertados']} insertados | "
            f"{resultado['rechazados']} rechazados | "
            f"{resultado['cuarentena_total']} cuarentena | "
            f"{resultado['tasa_rechazo_pct']}% rechazo"
        )
    ]

    resueltos_tb = resultado.get('resueltos_por_tiebreaker', 0)
    if resueltos_tb > 0:
        lineas.append(f"          resueltos_por_tiebreaker: {resueltos_tb}")

    for item in resultado.get('motivos_principales', []):
        lineas.append(f"          motivo: {item['motivo']} ({item['cantidad']})")

    return lineas


def construir_reporte_dq_operativo(nombre_fact: str, resultado: dict | None) -> dict:
    """
    Retorna un payload estable para reporte/export operativo de DQ por fact.
    """
    resultado_normalizado = normalizar_resultado_fact(resultado)
    return {
        "fact": nombre_fact,
        "leidos": resultado_normalizado["leidos"],
        "insertados": resultado_normalizado["insertados"],
        "rechazados": resultado_normalizado["rechazados"],
        "cuarentena_total": resultado_normalizado["cuarentena_total"],
        "tasa_rechazo_pct": resultado_normalizado["tasa_rechazo_pct"],
        "motivos_principales": list(resultado_normalizado.get("motivos_principales", [])),
    }
