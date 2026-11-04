"""
servicios/servicio_ingesta.py
================================
Servicio para validar archivos CSV en memoria usando Polars.
"""

from __future__ import annotations
import io
import polars as pl
from nucleo.logging import obtener_logger
from fastapi import UploadFile

log = obtener_logger(__name__)

async def validar_csv_polars(archivo: UploadFile, tabla_destino: str) -> dict:
    """
    Lee un CSV en memoria y retorna un diccionario con filas válidas y con errores.
    Este es un validador genérico que luego se puede extender con validaciones contra BD.
    """
    contenido = await archivo.read()
    
    try:
        # Leemos el CSV directamente en memoria con Polars
        df = pl.read_csv(contenido)
    except Exception as e:
        log.error("Error al leer CSV con Polars", exc_info=True)
        return {
            "valido": False,
            "error_general": f"No se pudo parsear el CSV. Verifica que sea un archivo separado por comas. Detalles: {str(e)}"
        }

    filas = df.to_dicts()
    
    validos = []
    con_errores = []

    # Ejemplo de validación básica: revisar si hay nulos en columnas numéricas o formatos extraños.
    # En un caso real, aquí cruzaríamos con las reglas de 'tabla_destino'.
    for i, fila in enumerate(filas):
        errores_fila = []
        
        # Validación genérica dummy: detectar nulos
        for col, val in fila.items():
            if val is None or (isinstance(val, str) and val.strip() == ""):
                # Omitimos marcar nulos genéricamente como error fatal para esta prueba,
                # pero aquí iría la lógica de negocio.
                pass
                
        # Si la tabla es Fact_Proyecciones, revisar que no haya montos negativos
        if "proyecciones" in tabla_destino.lower():
            for col in ["Monto", "Valor", "monto", "valor"]:
                if col in fila:
                    try:
                        monto_float = float(fila[col])
                        if monto_float < 0:
                            errores_fila.append(f"El campo {col} no puede ser negativo.")
                    except (ValueError, TypeError):
                        errores_fila.append(f"El campo {col} debe ser numérico.")
                        
        # Si la tabla es Fact_Ciclo_Poda, revisar que Costo y Horas_Hombre no sean negativos
        elif "ciclo_poda" in tabla_destino.lower():
            for col in ["Costo", "Horas_Hombre"]:
                if col in fila:
                    try:
                        val_float = float(fila[col])
                        if val_float < 0:
                            errores_fila.append(f"El campo {col} no puede ser negativo.")
                    except (ValueError, TypeError):
                        errores_fila.append(f"El campo {col} debe ser numérico.")

        if errores_fila:
            con_errores.append({
                "fila_id": i + 1,
                "datos": fila,
                "errores": errores_fila
            })
        else:
            validos.append({
                "fila_id": i + 1,
                "datos": fila
            })

    # Resumen estructurado
    return {
        "valido": True,
        "total_filas": len(filas),
        "columnas": df.columns,
        "filas_validas": validos,
        "filas_con_errores": con_errores,
    }
