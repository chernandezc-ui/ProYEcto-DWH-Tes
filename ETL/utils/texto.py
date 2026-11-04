"""
texto.py
========
Utilidades para normalización de texto libre.
Variedades, nombres de personal y geografía llegan
con mayúsculas inconsistentes, tildes y espacios extra.
"""

import re
import unicodedata


def normalizar_espacio(valor: str | None) -> str | None:
    """
    Elimina espacios al inicio, final y dobles internos.
    """
    if valor is None:
        return None
    return re.sub(r'\s+', ' ', str(valor).strip())


def titulo(valor: str | None) -> str | None:
    """
    Aplica Title Case — primera letra de cada palabra en mayúscula.
    Usa .title() de Python que maneja tildes correctamente.
    Ejemplo: 'BILOXI' → 'Biloxi', 'sekoya pop' → 'Sekoya Pop'
    """
    if valor is None:
        return None
    return normalizar_espacio(valor).title()


def mayusculas(valor: str | None) -> str | None:
    """
    Convierte a mayúsculas — para códigos y siglas.
    """
    if valor is None:
        return None
    return normalizar_espacio(valor).upper()


def quitar_tildes(valor: str | None) -> str | None:
    """
    Elimina tildes para comparaciones insensibles a acentos.
    Útil para lookup en MDM antes de Levenshtein.
    """
    if valor is None:
        return None
    return ''.join(
        caracter for caracter in unicodedata.normalize('NFD', valor)
        if unicodedata.category(caracter) != 'Mn'
    )


def normalizar_variedad(valor: str | None) -> str | None:
    """
    Normalización estándar para nombres de variedad:
    - Quita espacios extra
    - Aplica Title Case
    Ejemplo: '  BILOXY  ' → 'Biloxy'
    """
    if valor is None:
        return None
    return titulo(valor)


def normalizar_variedad_para_match(valor: str | None) -> str | None:
    """
    Normalizacion tipografica segura para matching de variedades.
    No cambia la semantica; solo unifica formato.

    Ejemplos:
    - 'FCM15 – 005' -> 'FCM15-005'
    - 'FL 19-006' -> 'FL19-006'
    - '  mega crisp  ' -> 'MEGA CRISP'
    """
    if valor is None:
        return None

    texto = normalizar_espacio(str(valor))
    if texto is None or texto in ('', 'None', 'nan'):
        return None

    texto = quitar_tildes(texto)
    texto = (
        texto.replace('–', '-')
        .replace('—', '-')
        .replace('−', '-')
        .replace('’', "'")
        .replace('`', "'")
    )
    texto = re.sub(r'\s*-\s*', '-', texto)
    texto = re.sub(r'\s*\(\s*', '(', texto)
    texto = re.sub(r'\s*\)\s*', ')', texto)
    texto = re.sub(r'([A-Za-z])\s+(\d)', r'\1\2', texto)
    texto = re.sub(r'(\d)\s+([A-Za-z])', r'\1\2', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto.upper()


def compactar_variedad_para_match(valor: str | None) -> str | None:
    """
    Clave compacta para equivalencias tipograficas de muy bajo riesgo.
    Elimina separadores manteniendo solo letras y numeros.

    Ejemplos:
    - 'MEGA CRISP' -> 'MEGACRISP'
    - 'FCM15-005' -> 'FCM15005'
    - 'O''NEAL' -> 'ONEAL'
    """
    texto = normalizar_variedad_para_match(valor)
    if texto is None:
        return None
    texto = re.sub(r'[^A-Z0-9]+', '', texto)
    return texto or None


def normalizar_nombre_persona(valor: str | None) -> str | None:
    """
    Normalización para nombres de personal:
    - Quita espacios extra
    - Aplica Title Case
    Ejemplo: 'JUAN CARLOS LOPEZ' → 'Juan Carlos Lopez'
    """
    if valor is None:
        return None
    return titulo(valor)


def normalizar_modulo(valor: str | None) -> str | None:
    """
    Normalización para módulos y geografía.
    Detecta Test Block y retorna None para manejo especial.
    """
    if valor is None:
        return None

    valor_limpio = normalizar_espacio(valor).upper()

    if es_test_block(valor_limpio):
        return valor_limpio  # Ya no retornamos None, permitimos que MDM resuelva el alias

    return normalizar_componente_geografico(valor_limpio)


def es_test_block(valor: str | None) -> bool:
    """
    Detecta si el valor de módulo corresponde a un Test Block.
    """
    if valor is None:
        return False
    return bool(re.search(r'\bTEST\b|\bBLOCK\b', str(valor).upper()))


def limpiar_numerico_texto(valor: str | None) -> str | None:
    """
    Limpia valores numéricos que Excel convirtió a texto.
    Ejemplo: '25.0' → '25', '  12.00  ' → '12'
    """
    if valor is None:
        return None
    valor = normalizar_espacio(str(valor))
    try:
        return str(int(float(valor)))
    except (ValueError, TypeError):
        return valor


def normalizar_componente_geografico(valor: str | None) -> str | None:
    """
    Normaliza componentes operativos de geografia para que el ETL
    tolere prefijos y formatos de campo variables.

    Ejemplos:
    - 'MODULO 2' -> '2'
    - 'TURNO 04' -> '4'
    - 'NROVALVULA 15' -> '15'
    - '9.1' -> '9.1'
    - 'VI' -> 'VI'
    - 'TURNO 02 PISO 03' -> 'TURNO 02 PISO 03'
    """
    if valor is None:
        return None

    texto = normalizar_espacio(str(valor))
    if texto is None or texto in ('', 'None', 'nan'):
        return None

    texto = texto.upper()
    if es_test_block(texto):
        return texto

    coincidencias = re.findall(r'[+-]?\d+(?:\.\d+)?', texto)
    if not coincidencias:
        return texto
    if len(coincidencias) > 1:
        return texto

    numero = coincidencias[0]
    if re.fullmatch(r'[+-]?\d+\.0+', numero):
        return str(int(float(numero)))
    if re.fullmatch(r'[+-]?\d+', numero):
        return str(int(numero))
    return numero
