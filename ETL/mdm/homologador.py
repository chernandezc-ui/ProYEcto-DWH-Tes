"""
homologador.py
==============
HomologaciÃ³n de texto libre via Levenshtein (rapidfuzz).
Resuelve aliases de variedades contra MDM.Diccionario_Homologacion.

Flujo:
  1. Match exacto en el diccionario (Aprobado_Por IS NOT NULL)
  2. Si no â†’ Levenshtein contra valores canÃ³nicos aprobados
  3. score >= 0.85 â†’ homologaciÃ³n automÃ¡tica
  4. score < 0.85 â†’ MDM.Cuarentena para revisiÃ³n humana

DDL v2 â€” MDM.Diccionario_Homologacion:
  Columnas reales: ID_Homologacion, Texto_Crudo, Valor_Canonico,
    Tabla_Origen, Campo_Origen, Score_Levenshtein,
    Aprobado_Por NVARCHAR(20), Fecha_Aprobacion, Veces_Aplicado
  NO existe columna Aprobado BIT â€” se usa Aprobado_Por para distinguir
    aprobados  : Aprobado_Por IS NOT NULL AND Aprobado_Por != 'PENDIENTE'
    pendientes : Aprobado_Por = 'PENDIENTE' o IS NULL
"""

import pandas as pd
try:
    from rapidfuzz import fuzz, process
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Falta la dependencia 'rapidfuzz' en el entorno actual. "
        "Instala las dependencias del proyecto antes de ejecutar el ETL."
    ) from exc
from sqlalchemy.engine import Engine
from sqlalchemy import text
from datetime import datetime

from utils.contexto_transaccional import RecursoDB, administrar_recurso_db
from utils.texto import (
    compactar_variedad_para_match,
    normalizar_variedad,
    normalizar_variedad_para_match,
    quitar_tildes,
)


import logging
_log = logging.getLogger("ETL_Pipeline")

UMBRAL_AUTO = 0.85


def _clave_variedad(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor_normalizado = normalizar_variedad_para_match(valor)
    if not valor_normalizado:
        return None
    return quitar_tildes(valor_normalizado).lower()


def _clave_variedad_compacta(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor_normalizado = compactar_variedad_para_match(valor)
    if not valor_normalizado:
        return None
    return quitar_tildes(valor_normalizado).lower()


def cargar_diccionario(engine: Engine,
                        tabla_origen: str) -> pd.DataFrame:
    """
    Carga entradas aprobadas del diccionario para una tabla origen.
    Aprobado = Aprobado_Por IS NOT NULL AND != 'PENDIENTE'
    """
    with administrar_recurso_db(engine) as conexion:
        resultado = conexion.execute(text("""
            SELECT
                Texto_Crudo,
                Valor_Canonico,
                Score_Levenshtein,
                Veces_Aplicado
            FROM MDM.Diccionario_Homologacion
            WHERE Tabla_Origen  = :tabla_origen
              AND Aprobado_Por IS NOT NULL
              AND Aprobado_Por != 'PENDIENTE'
        """), {'tabla_origen': tabla_origen})

        df = pd.DataFrame(resultado.fetchall(), columns=resultado.keys())
        if df.empty:
            return df
        df['Clave_Texto_Crudo'] = df['Texto_Crudo'].map(_clave_variedad)
        df['Clave_Texto_Crudo_Compacta'] = df['Texto_Crudo'].map(_clave_variedad_compacta)
        df['Clave_Valor_Canonico'] = df['Valor_Canonico'].map(_clave_variedad)
        df['Clave_Valor_Canonico_Compacta'] = df['Valor_Canonico'].map(_clave_variedad_compacta)
        return df


def cargar_catalogo_variedades(engine: Engine) -> pd.DataFrame:
    """
    Carga el catalogo canonico de variedades.
    Fuente de verdad para homologacion inicial:
    - MDM.Catalogo_Variedades activas
    - fallback a Silver.Dim_Variedad
    """
    with administrar_recurso_db(engine) as conexion:
        resultado = conexion.execute(text("""
            SELECT Nombre_Canonico AS Valor_Canonico
            FROM MDM.Catalogo_Variedades
            WHERE Es_Activa = 1

            UNION

            SELECT Nombre_Variedad AS Valor_Canonico
            FROM Silver.Dim_Variedad
        """))

        df = pd.DataFrame(resultado.fetchall(), columns=resultado.keys())
        if df.empty:
            return df

        df['Clave_Valor_Canonico'] = df['Valor_Canonico'].map(_clave_variedad)
        df['Clave_Valor_Canonico_Compacta'] = df['Valor_Canonico'].map(_clave_variedad_compacta)
        df = df.dropna(subset=['Clave_Valor_Canonico'])
        df = df.drop_duplicates(subset=['Clave_Valor_Canonico'], keep='first')
        return df


def buscar_match_exacto(valor: str,
                         diccionario: pd.DataFrame) -> str | None:
    if diccionario.empty:
        return None
    clave = _clave_variedad(valor)
    if clave is not None:
        coincidencia = diccionario[diccionario['Clave_Texto_Crudo'] == clave]
        canonicos = coincidencia['Valor_Canonico'].dropna().unique().tolist()
        if len(canonicos) == 1:
            return canonicos[0]

    clave_compacta = _clave_variedad_compacta(valor)
    if clave_compacta is None:
        return None

    coincidencia = diccionario[diccionario['Clave_Texto_Crudo_Compacta'] == clave_compacta]
    canonicos = coincidencia['Valor_Canonico'].dropna().unique().tolist()
    return canonicos[0] if len(canonicos) == 1 else None


def buscar_match_catalogo(valor: str,
                           catalogo: pd.DataFrame) -> str | None:
    if catalogo.empty:
        return None

    clave = _clave_variedad(valor)
    if clave is not None:
        coincidencia = catalogo[catalogo['Clave_Valor_Canonico'] == clave]
        canonicos = coincidencia['Valor_Canonico'].dropna().unique().tolist()
        if len(canonicos) == 1:
            return canonicos[0]

    clave_compacta = _clave_variedad_compacta(valor)
    if clave_compacta is None:
        return None

    coincidencia = catalogo[catalogo['Clave_Valor_Canonico_Compacta'] == clave_compacta]
    canonicos = coincidencia['Valor_Canonico'].dropna().unique().tolist()
    return canonicos[0] if len(canonicos) == 1 else None


def buscar_match_levenshtein(valor: str,
                              catalogo: pd.DataFrame) -> tuple[str | None, float]:
    if catalogo.empty:
        return None, 0.0

    valor_normalizado = normalizar_variedad_para_match(valor)
    if not valor_normalizado:
        return None, 0.0

    catalogo_match = catalogo.dropna(subset=['Clave_Valor_Canonico']).drop_duplicates(
        subset=['Clave_Valor_Canonico'], keep='first'
    )
    candidatos = catalogo_match['Clave_Valor_Canonico'].tolist()
    resultado  = process.extractOne(valor_normalizado, candidatos, scorer=fuzz.token_sort_ratio)

    if resultado is None:
        return None, 0.0

    match_clave, score, _ = resultado
    score_norm = score / 100.0

    if score_norm < UMBRAL_AUTO:
        return None, score_norm

    coincidencia = catalogo_match[catalogo_match['Clave_Valor_Canonico'] == match_clave]
    canonicos = coincidencia['Valor_Canonico'].dropna().unique().tolist()
    return (canonicos[0], score_norm) if len(canonicos) == 1 else (None, score_norm)


def buscar_sugerencia_levenshtein(valor: str,
                                   catalogo: pd.DataFrame) -> tuple[str | None, float]:
    if catalogo.empty:
        return None, 0.0

    valor_normalizado = normalizar_variedad_para_match(valor)
    if not valor_normalizado:
        return None, 0.0

    catalogo_match = catalogo.dropna(subset=['Clave_Valor_Canonico']).drop_duplicates(
        subset=['Clave_Valor_Canonico'], keep='first'
    )
    candidatos = catalogo_match['Clave_Valor_Canonico'].tolist()
    resultado = process.extractOne(valor_normalizado, candidatos, scorer=fuzz.token_sort_ratio)
    if resultado is None:
        return None, 0.0

    match_clave, score, _ = resultado
    coincidencia = catalogo_match[catalogo_match['Clave_Valor_Canonico'] == match_clave]
    canonicos = coincidencia['Valor_Canonico'].dropna().unique().tolist()
    return (canonicos[0] if len(canonicos) == 1 else None), score / 100.0


def registrar_homologacion(recurso_db: RecursoDB,
                            tabla_origen: str,
                            campo_origen: str,
                            texto_crudo: str,
                            valor_canonico: str,
                            score: float,
                            aprobado: bool = True) -> None:
    """
    Registra o actualiza una entrada en MDM.Diccionario_Homologacion.
    aprobado=True  â†’ Aprobado_Por = 'SISTEMA'
    aprobado=False â†’ Aprobado_Por = 'PENDIENTE' (requiere revisiÃ³n humana)
    """
    aprobado_por = 'SISTEMA' if aprobado else 'PENDIENTE'

    with administrar_recurso_db(recurso_db) as conexion:
        existe = conexion.execute(text("""
            SELECT COUNT(*)
            FROM MDM.Diccionario_Homologacion
            WHERE Tabla_Origen = :tabla_origen
              AND Texto_Crudo  = :texto_crudo
        """), {
            'tabla_origen': tabla_origen,
            'texto_crudo':  texto_crudo,
        }).scalar()

        if existe:
            if aprobado:
                conexion.execute(text("""
                    UPDATE MDM.Diccionario_Homologacion
                    SET Valor_Canonico     = :valor_canonico,
                        Score_Levenshtein  = :score,
                        Aprobado_Por       = :aprobado_por,
                        Fecha_Aprobacion   = :fecha_aprobacion,
                        Veces_Aplicado     = Veces_Aplicado + 1
                    WHERE Tabla_Origen = :tabla_origen
                      AND Texto_Crudo  = :texto_crudo
                """), {
                    'tabla_origen':      tabla_origen,
                    'texto_crudo':       texto_crudo,
                    'valor_canonico':    valor_canonico,
                    'score':             round(score, 4),
                    'aprobado_por':      aprobado_por,
                    'fecha_aprobacion':  datetime.now(),
                })
            else:
                conexion.execute(text("""
                    UPDATE MDM.Diccionario_Homologacion
                    SET Valor_Canonico    = COALESCE(Valor_Canonico, :valor_canonico),
                        Score_Levenshtein = :score,
                        Veces_Aplicado    = Veces_Aplicado + 1
                    WHERE Tabla_Origen = :tabla_origen
                      AND Texto_Crudo  = :texto_crudo
                """), {
                    'tabla_origen':      tabla_origen,
                    'texto_crudo':       texto_crudo,
                    'valor_canonico':    valor_canonico,
                    'score':             round(score, 4),
                })
        else:
            conexion.execute(text("""
                INSERT INTO MDM.Diccionario_Homologacion (
                    Texto_Crudo, Valor_Canonico,
                    Tabla_Origen, Campo_Origen,
                    Score_Levenshtein,
                    Aprobado_Por, Fecha_Aprobacion,
                    Veces_Aplicado
                ) VALUES (
                    :texto_crudo, :valor_canonico,
                    :tabla_origen, :campo_origen,
                    :score,
                    :aprobado_por, :fecha_aprobacion,
                    1
                )
            """), {
                'texto_crudo':       texto_crudo,
                'valor_canonico':    valor_canonico,
                'tabla_origen':      tabla_origen,
                'campo_origen':      campo_origen,
                'score':             round(score, 4),
                'aprobado_por':      aprobado_por,
                'fecha_aprobacion':  datetime.now() if aprobado else None,
            })


def homologar_valor(valor: str | None,
                    diccionario: pd.DataFrame,
                    catalogo: pd.DataFrame) -> tuple[str | None, str, str | None, float]:
    """
    Homologa un valor contra el diccionario canónico.
    Retorna (valor_homologado, estado, sugerencia_canonico, score).
    """
    if not valor or not str(valor).strip():
        return None, 'NULO', None, 0.0

    valor = str(valor).strip()

    canonico = buscar_match_exacto(valor, diccionario)
    if canonico:
        return canonico, 'EXACTO', canonico, 1.0

    canonico = buscar_match_catalogo(valor, catalogo)
    if canonico:
        return canonico, 'CATALOGO', canonico, 1.0

    canonico, score = buscar_match_levenshtein(valor, catalogo)
    if canonico:
        return canonico, 'LEVENSHTEIN', canonico, score

    sugerencia, score = buscar_sugerencia_levenshtein(valor, catalogo)
    return None, 'CUARENTENA', (sugerencia or normalizar_variedad(valor) or valor), score


def registrar_homologaciones_batch(recurso_db: RecursoDB,
                                   tabla_origen: str,
                                   campo_origen: str,
                                   resoluciones: list[dict]) -> None:
    """
    Realiza una actualización/inserción masiva de resoluciones en el diccionario.
    """
    if not resoluciones:
        return

    # Agrupar por (Texto_Crudo, Valor_Canonico) para consolidar Veces_Aplicado
    consolidado: dict[tuple, dict] = {}
    for res in resoluciones:
        key = (res['texto_crudo'], res['valor_canonico'])
        if key not in consolidado:
            consolidado[key] = res
            consolidado[key]['veces'] = 1
        else:
            consolidado[key]['veces'] += 1

    _log.info(f"  Registrando {len(consolidado)} resoluciones únicas en el diccionario...")
    
    ahora = datetime.now()
    with administrar_recurso_db(recurso_db) as conexion:
        for (texto, canonico), info in consolidado.items():
            aprobado = info['estado'] != 'CUARENTENA'
            aprobado_por = 'SISTEMA' if aprobado else 'PENDIENTE'
            score = info['score']
            veces = info['veces']

            # Nota: para un sistema Senior, esto debería ser un MERGE masivo vía #Temp table.
            # Por ahora lo mantenemos en un bucle pero dentro de UNA sola transacción.
            conexion.execute(text("""
                IF EXISTS (SELECT 1 FROM MDM.Diccionario_Homologacion WHERE Tabla_Origen = :t AND Texto_Crudo = :txt)
                BEGIN
                    UPDATE MDM.Diccionario_Homologacion
                    SET Valor_Canonico = CASE WHEN :aprobado = 1 THEN :can ELSE ISNULL(Valor_Canonico, :can) END,
                        Score_Levenshtein = :score,
                        Aprobado_Por = CASE WHEN :aprobado = 1 THEN :usr ELSE Aprobado_Por END,
                        Fecha_Aprobacion = CASE WHEN :aprobado = 1 THEN :fec ELSE Fecha_Aprobacion END,
                        Veces_Aplicado = Veces_Aplicado + :v
                    WHERE Tabla_Origen = :t AND Texto_Crudo = :txt
                END
                ELSE
                BEGIN
                    INSERT INTO MDM.Diccionario_Homologacion (
                        Texto_Crudo, Valor_Canonico, Tabla_Origen, Campo_Origen,
                        Score_Levenshtein, Aprobado_Por, Fecha_Aprobacion, Veces_Aplicado
                    ) VALUES (
                        :txt, :can, :t, :c, :score, :usr, 
                        CASE WHEN :aprobado = 1 THEN :fec ELSE NULL END, :v
                    )
                END
            """), {
                't': tabla_origen, 'txt': texto, 'can': canonico, 'c': campo_origen,
                'score': round(score, 4), 'usr': aprobado_por, 'fec': ahora, 
                'v': veces, 'aprobado': 1 if aprobado else 0
            })


def homologar_columna(df: pd.DataFrame,
                       columna_raw: str,
                       columna_destino: str,
                       tabla_origen: str,
                       recurso_db: RecursoDB,
                       columna_id_origen: str | None = None) -> tuple[pd.DataFrame, list[dict]]:
    """
    Homologa una columna completa del DataFrame de forma eficiente.
    """
    _log.info(f"  Homologando columna '{columna_raw}' via MDM...")
    diccionario = cargar_diccionario(recurso_db, tabla_origen)
    catalogo = cargar_catalogo_variedades(recurso_db)

    cuarentenas = []
    resultados  = []
    pendientes_registro = []
    cache_resoluciones: dict[str, tuple[str | None, str, str | None, float]] = {}

    valores_raw = df[columna_raw].tolist()
    valores_id = df[columna_id_origen].tolist() if columna_id_origen and columna_id_origen in df.columns else [None] * len(df)

    for i, (valor, valor_id) in enumerate(zip(valores_raw, valores_id)):
        if pd.isna(valor):
            valor = None
            
        clave_cache = _clave_variedad(valor)
        if clave_cache is None:
            valor_token = '' if valor is None else str(valor).strip().lower()
            clave_cache = f'__RAW__::{valor_token}'

        if clave_cache in cache_resoluciones:
            homologado, estado, sugerencia, score = cache_resoluciones[clave_cache]
        else:
            homologado, estado, sugerencia, score = homologar_valor(valor, diccionario, catalogo)
            cache_resoluciones[clave_cache] = (homologado, estado, sugerencia, score)
            
            # Solo registramos en el diccionario la primera vez que vemos el valor en este batch
            if estado != 'NULO':
                pendientes_registro.append({
                    'texto_crudo': str(valor).strip() if valor else '',
                    'valor_canonico': sugerencia,
                    'estado': estado,
                    'score': score
                })

        resultados.append(homologado)

        if estado == 'CUARENTENA':
            id_registro_origen = None
            if pd.notna(valor_id):
                try:
                    id_registro_origen = int(valor_id)
                except (TypeError, ValueError):
                    id_registro_origen = None

            cuarentenas.append({
                'columna':           columna_raw,
                'valor':             valor,
                'motivo':            'Variedad no reconocida — requiere revisión en MDM',
                'tipo_regla':        'CATALOGO',
                'score_levenshtein': round(score, 4),
                'severidad':         'ALTO',
                'id_registro_origen': id_registro_origen,
            })

    # Registro masivo de resoluciones
    registrar_homologaciones_batch(recurso_db, tabla_origen, columna_raw, pendientes_registro)

    df[columna_destino] = resultados
    return df, cuarentenas

