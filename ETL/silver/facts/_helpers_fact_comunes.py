from __future__ import annotations

import re
from collections.abc import MutableSet
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    import pandas as pd

# Aliases de backcompat — implementaciones viven en utils.tipos
from utils.tipos import (
    a_entero as a_entero_nulo,
    a_entero_no_negativo,
    texto_nulo,
    obtener_valor_raw,
)

__all__ = [
    "a_entero_nulo",
    "a_entero_no_negativo",
    "texto_nulo",
    "obtener_valor_raw",
    "motivo_cuarentena_geografia",
    "registrar_rechazo",
    "finalizar_resumen_fact",
    "obtener_columnas_tabla",
    "columna_sql_dinamica",
    "asegurar_id_registro_origen",
    "leer_bronce_dinamico",
    "validar_layout_migrado",
    "parsear_valores_raw",
]


def motivo_cuarentena_geografia(resultado_geo: dict) -> str:
    estado = resultado_geo.get("estado")
    detalle = resultado_geo.get("detalle")
    complemento = f" Detalle: {detalle}" if detalle else ""

    if estado in ("TEST_BLOCK_NO_MAPEADO", "TEST_BLOCK_AMBIGUO"):
        return f"Test block (VI) sin mapeo unico en Dim_Geografia.{complemento}"
    if estado in ("PENDIENTE_CASO_ESPECIAL", "CASO_ESPECIAL_MODULO"):
        return f"Geografia especial requiere catalogacion o regla en MDM_Geografia.{complemento}"
    if estado in ("PENDIENTE_CAMA_GENERICA", "CAMA_NO_RELACION"):
        return f"Cama no relacionada a la geografia operativa.{complemento}"
    if estado in ("PENDIENTE_DIM_DUPLICADA", "GEOGRAFIA_AMBIGUA"):
        return f"La clave geografica tiene mas de un registro vigente en Silver.Dim_Geografia.{complemento}"
    if estado == "CAMA_NO_VALIDA":
        return f"Cama fuera de rango operativo permitido.{complemento}"
    if estado == "CAMA_NO_CATALOGO":
        return f"Cama valida pero no registrada en el catalogo operativo.{complemento}"
    return f"Geografia no encontrada en Silver.Dim_Geografia.{complemento}"


def registrar_rechazo(
    resumen: dict,
    ids_rechazados,
    id_origen: int | None,
    *,
    columna: str,
    valor,
    motivo: str,
    tipo_regla: str = 'DQ',
    severidad: str = 'ALTO',
) -> None:
    # DEPRECADO: usar self.registrar_rechazo() en clases que hereden BaseFactProcessor.
    resumen['rechazados'] = int(resumen.get('rechazados', 0) or 0) + 1
    if id_origen is not None:
        if isinstance(ids_rechazados, MutableSet) or hasattr(ids_rechazados, 'add'):
            ids_rechazados.add(id_origen)
        else:
            ids_rechazados.append(id_origen)
    resumen.setdefault('cuarentena', []).append({
        'columna': columna,
        'valor': valor,
        'motivo': motivo,
        'tipo_regla': tipo_regla,
        'severidad': severidad,
        'id_registro_origen': id_origen,
    })


def finalizar_resumen_fact(resumen: dict) -> dict:
    # DEPRECADO: usar proc.finalizar_proceso(contexto) en clases que hereden BaseFactProcessor.
    from utils.metricas import normalizar_resultado_fact

    return normalizar_resultado_fact(resumen)


def obtener_columnas_tabla(engine: Engine, tabla_completa: str) -> set[str]:
    esquema, tabla = tabla_completa.split(".")
    with engine.connect() as conexion:
        resultado = conexion.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :esquema
                  AND TABLE_NAME = :tabla
                """
            ),
            {"esquema": esquema, "tabla": tabla},
        )
        return {str(fila[0]) for fila in resultado.fetchall()}


def columna_sql_dinamica(columnas_disponibles: set[str], nombre_columna: str) -> str:
    """
    Retorna el nombre de columna si existe en la tabla, o un CAST(NULL) con alias
    si aún no fue migrada. Permite SELECT defensivo sin romper en layouts parciales.
    """
    if nombre_columna in columnas_disponibles:
        return nombre_columna
    return f"CAST(NULL AS NVARCHAR(MAX)) AS {nombre_columna}"


def asegurar_id_registro_origen(df: "pd.DataFrame", columna_id: str) -> "pd.DataFrame":
    """
    Garantiza que el DataFrame exponga la PK también con el nombre canónico
    'ID_Registro_Origen', sin perder la columna con el nombre real de la PK.

    Contrato uniforme de rastreo: varios facts construyen su payload leyendo
    fila.get('ID_Registro_Origen'), mientras que leer_bronce_dinamico devuelve
    la PK con su nombre físico (ID_Induccion_Floral, ID_Floracion, etc.). Sin
    este espejo, id_origen quedaba None en cada fila → los rechazos no marcaban
    RECHAZADO y los insertados no marcaban PROCESADO (reproceso perpetuo).
    """
    if columna_id in df.columns and 'ID_Registro_Origen' not in df.columns:
        df = df.copy()
        df['ID_Registro_Origen'] = df[columna_id]
    return df


def leer_bronce_dinamico(
    engine: Engine,
    tabla: str,
    columna_id: str,
    columnas_opcionales: list[str],
    *,
    filtro_estado: bool = True,
) -> "pd.DataFrame":
    """
    Lee una tabla Bronce con SELECT defensivo: columnas fijas + columnas opcionales
    que se sustituyen por NULL si aún no existen (layouts en migración parcial).

    Args:
        tabla: nombre completo 'Esquema.Tabla'
        columna_id: columna PK, siempre incluida sin fallback
        columnas_opcionales: columnas _Raw deseadas (pueden no existir todavía)
        filtro_estado: si True, agrega WHERE Estado_Carga = 'CARGADO'
    """
    import pandas as pd

    disponibles = obtener_columnas_tabla(engine, tabla)
    select_cols = [columna_id] + [
        columna_sql_dinamica(disponibles, col) for col in columnas_opcionales
    ]
    where = "WHERE Estado_Carga = 'CARGADO'" if filtro_estado and 'Estado_Carga' in disponibles else ""
    sql = f"SELECT {', '.join(select_cols)} FROM {tabla} {where}"
    with engine.connect() as conexion:
        resultado = conexion.execute(text(sql))
        df = pd.DataFrame(resultado.fetchall(), columns=resultado.keys())
    return asegurar_id_registro_origen(df, columna_id)


def validar_layout_migrado(
    engine: Engine,
    *,
    tabla_origen: str,
    tabla_destino: str,
    columna_id: str,
    columnas_bronce_requeridas: set[str],
    columnas_silver_requeridas: set[str],
    nombre_layout: str,
) -> str:
    columnas_bronce = obtener_columnas_tabla(engine, tabla_origen)
    columnas_silver = obtener_columnas_tabla(engine, tabla_destino)

    faltantes_bronce = sorted(columnas_bronce_requeridas - columnas_bronce)
    faltantes_silver = sorted(columnas_silver_requeridas - columnas_silver)

    if faltantes_bronce or faltantes_silver:
        raise RuntimeError(
            f"La migracion definitiva de {nombre_layout} no esta aplicada. "
            f"Bronce faltantes: {faltantes_bronce or 'ninguno'} | "
            f"Silver faltantes: {faltantes_silver or 'ninguno'}"
        )

    return columna_id


def parsear_valores_raw(texto: str | None) -> dict[str, str]:
    if texto is None:
        return {}

    crudo = str(texto).strip()
    if not crudo:
        return {}

    resultado: dict[str, str] = {}
    for parte in re.split(r"\s*\|\s*", crudo):
        if "=" not in parte:
            continue
        clave, valor = parte.split("=", 1)
        clave = str(clave).strip()
        valor = str(valor).strip()
        if clave:
            resultado[clave] = valor
    return resultado


def derivar_fecha_iso_semana(anio, semana) -> str | None:
    """
    Deriva 'YYYY-MM-DD' (lunes de la semana ISO) a partir de Año + Semana.
    Fuentes como Evaluacion_Pesos / Floracion / Induccion no traen fecha
    explícita, sólo año y semana calendario. Retorna None si no es derivable.
    """
    import datetime

    if anio is None or semana is None:
        return None
    a_txt = str(anio).strip()
    s_txt = re.sub(r'[^0-9]', '', str(semana))
    if not a_txt or a_txt.lower() == 'nan' or not s_txt:
        return None
    try:
        year = int(float(a_txt))
        week = int(s_txt)
        if not (1 <= week <= 53):
            return None
        return datetime.datetime.strptime(f'{year}-W{week:02d}-1', '%G-W%V-%u').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None
