"""
dni.py
======
Utilidades para manejo de DNI.
DNI siempre es texto — nunca numérico.
"""

import re

from config import reglas


def longitud_dni() -> int:
    """Digitos de un DNI valido: Config.Parametros_Pipeline (DNI_LONGITUD)."""
    return reglas.parametro_int('DNI_LONGITUD')


def limpiar_dni(valor: str | None) -> str | None:
    """
    Limpia y normaliza un DNI crudo:
    - Elimina decimales (Excel convierte 7654321 → 7654321.0)
    - Quita espacios y puntos
    - Aplica zero-pad a la longitud configurada (DNI_LONGITUD)
    Retorna None si el valor es nulo o vacío.
    """
    if valor is None:
        return None

    valor = str(valor).strip()

    # Quitar parte decimal si Excel convirtió a float
    if valor.endswith('.0'):
        valor = valor[:-2]

    valor = valor.replace('.', '').replace(' ', '')

    if not valor:
        return None

    return valor.zfill(longitud_dni())


def es_dni_valido(valor: str | None) -> bool:
    """
    Valida que el DNI tenga exactamente DNI_LONGITUD dígitos numéricos.
    """
    if valor is None:
        return False
    return bool(re.fullmatch(r'\d{%d}' % longitud_dni(), valor))


def procesar_dni(valor: str | None) -> tuple[str | None, bool]:
    """
    Limpia y valida el DNI en un solo paso.
    Retorna tupla (dni_limpio, es_valido).
    """
    dni_limpio = limpiar_dni(valor)
    valido     = es_dni_valido(dni_limpio)
    return dni_limpio, valido
