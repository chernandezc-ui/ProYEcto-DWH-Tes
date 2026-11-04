"""Conversores de tipos robustos — fuente única de verdad para el ETL."""
from __future__ import annotations
import math


def a_entero(valor) -> int | None:
    try:
        if valor is None:
            return None
        t = str(valor).strip()
        t_lower = t.lower()
        if t_lower in ("", "none", "nan", "null", "undefined", "nat", "n/a", "n.a.", "n.a"):
            return None
        if "inf" in t_lower or "infinity" in t_lower:
            return None
            
        if "," in t and "." in t:
            idx_coma = t.find(",")
            idx_punto = t.find(".")
            if idx_punto > idx_coma:
                t = t.replace(",", "")
            else:
                t = t.replace(".", "").replace(",", ".")
        elif "," in t:
            partes = t.split(",")
            if len(partes) == 2 and len(partes[1]) == 3:
                t = t.replace(",", "")
            else:
                t = t.replace(",", ".")
                
        val_float = float(t)
        if math.isinf(val_float) or math.isnan(val_float):
            return None
        return int(val_float)
    except (ValueError, TypeError, OverflowError):
        return None


def a_entero_no_negativo(valor) -> int | None:
    n = a_entero(valor)
    return n if (n is not None and n >= 0) else None


def a_decimal(valor) -> float | None:
    try:
        if valor is None:
            return None
        t = str(valor).strip()
        t_lower = t.lower()
        if t_lower in ("", "none", "nan", "null", "undefined", "nat", "n/a", "n.a.", "n.a"):
            return None
        if "inf" in t_lower or "infinity" in t_lower:
            return None
            
        if "," in t and "." in t:
            idx_coma = t.find(",")
            idx_punto = t.find(".")
            if idx_punto > idx_coma:
                t = t.replace(",", "")
            else:
                t = t.replace(".", "").replace(",", ".")
        elif "," in t:
            partes = t.split(",")
            if len(partes) == 2 and len(partes[1]) == 3:
                t = t.replace(",", "")
            else:
                t = t.replace(",", ".")
                
        val_float = float(t)
        if math.isinf(val_float) or math.isnan(val_float):
            return None
        return val_float
    except (ValueError, TypeError, OverflowError):
        return None


def texto_nulo(valor) -> str | None:
    if valor is None:
        return None
    t = str(valor).strip()
    t_lower = t.lower()
    if t_lower in ("", "none", "nan", "null", "undefined", "nat", "n/a", "n.a.", "n.a"):
        return None
    return t


def obtener_valor_raw(
    fila,
    nombre_columna: str,
    valores_raw: dict | None = None,
):
    """Busca valor en columna directa o, si falta, en el dict valores_raw."""
    valor = fila.get(nombre_columna)
    if valor is not None and str(valor).strip() not in ("", "None", "nan"):
        return valor
    if valores_raw is None:
        return None
    v = valores_raw.get(nombre_columna)
    return v if v is not None and str(v).strip() not in ("", "None", "nan") else None

