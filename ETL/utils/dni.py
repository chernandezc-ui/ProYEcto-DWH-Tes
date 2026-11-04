"""
dni.py
======
Utilidades para manejo de DNI.
DNI siempre es texto — nunca numérico.
"""

import re


LONGITUD_DNI = 8
PATRON_DNI   = re.compile(r'^\d{8}$')


def limpiar_dni(valor: str | None) -> str | None:
    """
    Limpia y normaliza un DNI crudo:
    - Elimina decimales (Excel convierte 7654321 → 7654321.0)
    - Quita espacios y puntos
    - Aplica zero-pad a 8 dígitos
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

    # Zero-pad a 8 dígitos
    return valor.zfill(LONGITUD_DNI)


def es_dni_valido(valor: str | None) -> bool:
    """
    Valida que el DNI tenga exactamente 8 dígitos numéricos.
    """
    if valor is None:
        return False
    return bool(PATRON_DNI.match(valor))


def procesar_dni(valor: str | None) -> tuple[str | None, bool]:
    """
    Limpia y valida el DNI en un solo paso.
    Retorna tupla (dni_limpio, es_valido).
    """
    dni_limpio = limpiar_dni(valor)
    valido     = es_dni_valido(dni_limpio)
    return dni_limpio, valido
