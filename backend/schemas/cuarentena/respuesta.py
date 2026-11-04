"""
schemas/cuarentena/respuesta.py
================================
Schemas de SALIDA para el módulo Cuarentena.
"""
from datetime import datetime
from pydantic import BaseModel, Field

class RespuestaCuarentena(BaseModel):
    """
    Un registro de cuarentena leído desde MDM.Cuarentena.
    """
    tabla_origen:   str
    id_registro:    str
    columna_origen: str
    valor_raw:      str
    nombre_archivo: str | None
    fecha_ingreso:  str | None  # Ya formateado como string YYYY-MM-DD
    estado:         str
    motivo:         str | None
    valor_corregido:str | None = None
    id_registro_origen: int | None = None

    model_config = {"from_attributes": True}

class RespuestaPaginada(BaseModel):
    """Wrapper de paginación para listados de cuarentena."""
    total:   int
    pagina:  int
    tamano:  int
    datos:   list[RespuestaCuarentena]

class RespuestaAccionCuarentena(BaseModel):
    """Confirmación de una acción sobre un registro de cuarentena."""
    id_registro:   str
    estado_nuevo:  str
    mensaje:       str

class RespuestaResumenCuarentena(BaseModel):
    """Conteo agregado de registros en MDM.Cuarentena, por estado."""
    total:       int
    pendientes:  int
    resueltos:   int
    descartados: int