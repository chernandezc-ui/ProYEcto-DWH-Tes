"""
validador.py
============
Capa C de validación — Python puro.
Se ejecuta ANTES de insertar en Silver.
Sin consultas a la BD — solo lógica en memoria.

Reglas que aplica:
  - DNI: formato, zero-pad, nulos
  - Fechas: formato, rango campaña
  - Pesos: rango biológico 0.5–8.0g
  - Muestras: mínimo 1
  - Total plantas: mínimo 1
  - Humedad: proporción vs porcentaje
  - Test Block: detección en módulo
  - Variedades: normalización Title Case
"""

import pandas as pd
from utils.dni    import procesar_dni
from utils.fechas import describir_rango_campana, procesar_fecha, resolver_dominio_fecha
from utils.texto  import (
    normalizar_variedad,
    normalizar_nombre_persona,
    normalizar_modulo,
    es_test_block,
    limpiar_numerico_texto,
)
# ── Resultado de validación por fila ──────────────────────────
def _error(columna: str, valor, motivo: str,
           severidad: str = 'ALTO') -> dict:
    return {
        'columna':   columna,
        'valor':     valor,
        'motivo':    motivo,
        'severidad': severidad,
    }


# ── Validaciones individuales ─────────────────────────────────

def validar_dni(valor: str | None) -> tuple[str | None, dict | None]:
    """
    Limpia y valida DNI.
    Retorna (dni_limpio, error | None).
    """
    dni, valido = procesar_dni(valor)
    if not valido:
        return None, _error(
            'DNI', valor,
            'DNI inválido — debe tener 8 dígitos numéricos',
            'CRITICO'
        )
    return dni, None


def validar_fecha(valor: str | None,
                  nombre_columna: str = 'Fecha_Evento',
                  dominio: str | None = None) -> tuple:
    """
    Parsea y valida que la fecha esté dentro de la campaña.
    Retorna (fecha_datetime, error | None).
    """
    fecha, valida = procesar_fecha(valor, dominio=dominio)

    if fecha is None:
        return None, _error(
            nombre_columna, valor,
            'Fecha inválida — no se pudo parsear el formato',
            'CRITICO'
        )
    if not valida:
        rango = describir_rango_campana(dominio=dominio)
        return fecha, _error(
            nombre_columna, valor,
            f'Fecha fuera del rango de campana ({rango})',
            'ALTO'
        )
        return fecha, _error(
            nombre_columna, valor,
            'Fecha fuera del rango de campana (2025-06-01 -> 2026-06-30)',
            'ALTO'
        )
    return fecha, None


def validar_peso_baya(valor: str | None, config: dict | None = None) -> tuple[float | None, dict | None]:
    """
    Valida que el peso de baya esté en rango.
    Usa parámetros de config (PESO_BAYA_MIN, PESO_BAYA_MAX) o defaults de seguridad.
    """
    if valor is None:
        return None, _error('Peso_Baya_g', valor, 'Peso nulo', 'ALTO')

    # Obtener límites de la base de datos real o usar defaults si no hay config
    min_val = float(config.get('PESO_BAYA_MIN', 0.5)) if config else 0.5
    max_val = float(config.get('PESO_BAYA_MAX', 12.0)) if config else 12.0

    try:
        peso = float(str(valor).replace(',', '.'))
    except ValueError:
        return None, _error('Peso_Baya_g', valor,
                            'Peso no numérico', 'CRITICO')

    if not (min_val <= peso <= max_val):
        return None, _error(
            'Peso_Baya_g', valor,
            f'Peso fuera de rango biologico {min_val}-{max_val}g (recibido: {peso})',
            'CRITICO'
        )
    return peso, None


def validar_muestras(valor: str | None) -> tuple[int | None, dict | None]:
    """
    Valida que Muestras sea >= 1.
    Evita división por cero en cálculos de Peladas.
    """
    if valor is None:
        return None, _error('Muestras', valor, 'Muestras nulas', 'CRITICO')

    try:
        muestras = int(float(str(valor)))
    except ValueError:
        return None, _error('Muestras', valor,
                            'Muestras no numérico', 'CRITICO')

    if muestras < 1:
        return None, _error(
            'Muestras', valor,
            f'Muestras debe ser >= 1 (recibido: {muestras})',
            'CRITICO'
        )
    return muestras, None


def validar_total_plantas(valor: str | None) -> tuple[int | None, dict | None]:
    """
    Valida que Total_Plantas sea >= 1.
    Evita división por cero en Pct_Mortalidad PERSISTED.
    """
    if valor is None:
        return None, _error('Total_Plantas', valor,
                            'Total plantas nulo', 'CRITICO')

    try:
        plantas = int(float(str(valor)))
    except ValueError:
        return None, _error('Total_Plantas', valor,
                            'Total plantas no numérico', 'CRITICO')

    if plantas < 1:
        return None, _error(
            'Total_Plantas', valor,
            f'Total_Plantas debe ser >= 1 (recibido: {plantas})',
            'CRITICO'
        )
    return plantas, None


def normalizar_humedad(valor: str | None) -> tuple[float | None, dict | None]:
    """
    Detecta si la humedad viene como proporción (0–1) o porcentaje (0–100).
    Si viene como proporción la convierte a porcentaje.
    """
    if valor is None:
        return None, _error('Humedad_Relativa_Pct', valor,
                            'Humedad nula', 'ALTO')

    try:
        humedad = float(str(valor).replace(',', '.'))
    except ValueError:
        return None, _error('Humedad_Relativa_Pct', valor,
                            'Humedad no numérica', 'ALTO')

    # Detectar proporción → convertir a porcentaje
    if 0 <= humedad <= 1:
        humedad = humedad * 100

    if not (0 <= humedad <= 100):
        return None, _error(
            'Humedad_Relativa_Pct', valor,
            f'Humedad fuera de rango 0-100 (recibido: {humedad})',
            'ALTO'
        )
    return humedad, None


# ── Validador por tipo de tabla ───────────────────────────────

def validar_dataframe(df: pd.DataFrame,
                      tipo_tabla: str) -> tuple[pd.DataFrame, list[dict]]:
    """
    Aplica validaciones Capa C según el tipo de tabla.
    Retorna (df_limpio, lista_errores).

    Los errores NO eliminan la fila del DataFrame —
    se reportan para que cuarentena.py decida qué hacer.
    """
    errores = []
    df      = df.copy()

    # ── DNI ──────────────────────────────────────────────────
    if 'DNI_Raw' in df.columns:
        def procesar_col_dni(valor):
            dni, error = validar_dni(valor)
            if error:
                errores.append(error)
            return dni
        df['DNI_Procesado'] = df['DNI_Raw'].apply(procesar_col_dni)

    # ── Fecha ─────────────────────────────────────────────────
    if 'Fecha_Raw' in df.columns:
        dominio_fecha = resolver_dominio_fecha(tipo_tabla)
        def procesar_col_fecha(valor):
            fecha, error = validar_fecha(valor, dominio=dominio_fecha)
            if error:
                errores.append(error)
            return fecha
        df['Fecha_Procesada'] = df['Fecha_Raw'].apply(procesar_col_fecha)

    # ── Peso baya ─────────────────────────────────────────────
    if tipo_tabla == 'evaluacion_pesos' and 'PesoBaya_Raw' in df.columns:
        def procesar_col_peso(valor):
            peso, error = validar_peso_baya(valor)
            if error:
                errores.append(error)
            return peso
        df['Peso_Baya_Procesado'] = df['PesoBaya_Raw'].apply(procesar_col_peso)

    # ── Muestras ──────────────────────────────────────────────
    if tipo_tabla == 'peladas' and 'Muestras_Raw' in df.columns:
        def procesar_col_muestras(valor):
            muestras, error = validar_muestras(valor)
            if error:
                errores.append(error)
            return muestras
        df['Muestras_Procesado'] = df['Muestras_Raw'].apply(procesar_col_muestras)

    # ── Total plantas ─────────────────────────────────────────
    if tipo_tabla in {'sanidad', 'sanidad_activo'} and 'Total_Plantas_Raw' in df.columns:
        def procesar_col_plantas(valor):
            plantas, error = validar_total_plantas(valor)
            if error:
                errores.append(error)
            return plantas
        df['Total_Plantas_Procesado'] = df['Total_Plantas_Raw'].apply(procesar_col_plantas)

    # ── Humedad ───────────────────────────────────────────────
    if 'Humedad_Raw' in df.columns:
        def procesar_col_humedad(valor):
            humedad, error = normalizar_humedad(valor)
            if error:
                errores.append(error)
            return humedad
        df['Humedad_Procesado'] = df['Humedad_Raw'].apply(procesar_col_humedad)

    # ── Variedad ──────────────────────────────────────────────
    if 'Variedad_Raw' in df.columns:
        df['Variedad_Procesado'] = df['Variedad_Raw'].apply(normalizar_variedad)

    # ── Módulo + Test Block ───────────────────────────────────
    if 'Modulo_Raw' in df.columns:
        df['Es_Test_Block']      = df['Modulo_Raw'].apply(es_test_block)
        df['Modulo_Procesado']   = df['Modulo_Raw'].apply(normalizar_modulo)

    # ── Nombres de personal ───────────────────────────────────
    if 'Evaluador_Raw' in df.columns:
        df['Evaluador_Procesado'] = df['Evaluador_Raw'].apply(
            normalizar_nombre_persona
        )

    return df, errores


def hay_criticos(errores: list[dict]) -> bool:
    """
    Retorna True si hay al menos un error CRITICO.
    El pipeline debe detenerse si hay críticos.
    """
    return any(e['severidad'] == 'CRITICO' for e in errores)
