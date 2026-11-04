"""
reglas.py
=========
Capa B de validación — reglas dinámicas desde Config.Reglas_Validacion.
Se ejecuta DESPUÉS de Capa C y ANTES de insertar en Silver.
Las reglas se pueden modificar desde el portal Streamlit sin tocar código.
"""

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text


def cargar_reglas(engine: Engine, tabla: str) -> pd.DataFrame:
    """
    Carga las reglas activas de Config.Reglas_Validacion
    para una tabla Silver específica.
    """
    with engine.connect() as conexion:
        resultado = conexion.execute(text("""
            SELECT
                Columna,
                Tipo_Regla,
                Valor_Min,
                Valor_Max,
                Catalogo_Referencia,
                Expresion_Formato,
                Accion
            FROM Config.Reglas_Validacion
            WHERE Tabla  = :tabla
              AND Activo = 1
        """), {'tabla': tabla})

        return pd.DataFrame(resultado.fetchall(),
                            columns=resultado.keys())


def aplicar_regla_rango(df: pd.DataFrame,
                         columna: str,
                         valor_min: float | None,
                         valor_max: float | None,
                         accion: str) -> list[dict]:
    """
    Valida que los valores de una columna estén dentro del rango definido.
    """
    errores = []

    if columna not in df.columns:
        return errores

    for idx, valor in df[columna].items():
        if pd.isna(valor):
            continue
        try:
            numero = float(valor)
        except (ValueError, TypeError):
            errores.append({
                'fila':      idx,
                'columna':   columna,
                'valor':     valor,
                'motivo':    f'Valor no numérico en columna {columna}',
                'severidad': 'ALTO',
                'accion':    accion,
            })
            continue

        fuera_rango = False
        if valor_min is not None and numero < valor_min:
            fuera_rango = True
        if valor_max is not None and numero > valor_max:
            fuera_rango = True

        if fuera_rango:
            errores.append({
                'fila':      idx,
                'columna':   columna,
                'valor':     valor,
                'motivo':    f'{columna} fuera de rango [{valor_min}–{valor_max}] (recibido: {numero})',
                'severidad': 'ALTO',
                'accion':    accion,
            })

    return errores


def aplicar_regla_formato(df: pd.DataFrame,
                           columna: str,
                           expresion: str,
                           accion: str) -> list[dict]:
    """
    Valida que los valores de una columna cumplan una expresión regex.
    """
    import re
    errores = []

    if columna not in df.columns:
        return errores

    patron = re.compile(expresion)

    for idx, valor in df[columna].items():
        if pd.isna(valor):
            continue
        if not patron.match(str(valor)):
            errores.append({
                'fila':      idx,
                'columna':   columna,
                'valor':     valor,
                'motivo':    f'{columna} no cumple formato {expresion}',
                'severidad': 'ALTO',
                'accion':    accion,
            })

    return errores


def aplicar_reglas(df: pd.DataFrame,
                   tabla: str,
                   engine: Engine) -> tuple[pd.DataFrame, list[dict]]:
    """
    Aplica todas las reglas activas de Config.Reglas_Validacion
    para la tabla indicada.

    Retorna (df sin filas a RECHAZAR, lista_errores).
    """
    reglas  = cargar_reglas(engine, tabla)
    errores = []

    if reglas.empty:
        return df, errores

    for _, regla in reglas.iterrows():
        columna    = regla['Columna']
        tipo_regla = regla['Tipo_Regla']
        accion     = regla['Accion']

        if tipo_regla == 'RANGO':
            nuevos_errores = aplicar_regla_rango(
                df, columna,
                regla['Valor_Min'],
                regla['Valor_Max'],
                accion
            )
            errores.extend(nuevos_errores)

        elif tipo_regla == 'FORMATO':
            nuevos_errores = aplicar_regla_formato(
                df, columna,
                regla['Expresion_Formato'],
                accion
            )
            errores.extend(nuevos_errores)

    # Eliminar filas marcadas como RECHAZAR
    filas_rechazar = {
        e['fila'] for e in errores if e.get('accion') == 'RECHAZAR'
    }
    if filas_rechazar:
        df = df.drop(index=list(filas_rechazar)).reset_index(drop=True)

    return df, errores
