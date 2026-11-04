"""
schemas/auditoria/respuesta.py
===============================
Schemas de SALIDA para el módulo Auditoría.
"""

from datetime import datetime
from pydantic import BaseModel


class RespuestaLogCarga(BaseModel):
    """Una entrada del log de auditoría de Auditoria.Log_Carga."""
    id_log:            int
    nombre_proceso:    str
    tabla_destino:     str
    nombre_archivo:    str | None
    fecha_inicio:      datetime | None
    fecha_fin:         datetime | None
    estado:            str
    filas_insertadas:  int
    filas_rechazadas:  int
    duracion_segundos: int | None
    mensaje_error:     str | None
    id_corrida:        str | None = None

    model_config = {"from_attributes": True}


class RespuestaUltimoEstado(BaseModel):
    """Último estado conocido de una tabla en la auditoría."""
    tabla_destino:    str
    estado:           str | None
    fecha_inicio:     datetime | None
    fecha_fin:        datetime | None
    filas_insertadas: int | None
    duracion_segundos: int | None
    mensaje_error:    str | None


class RespuestaBitacoraPagina(BaseModel):
    """Página paginada de entradas de bitácora."""
    items:  list[RespuestaLogCarga]
    total:  int
    pagina: int
    tamano: int


class RespuestaResumenBitacora(BaseModel):
    """KPIs agregados de la bitácora para una ventana temporal."""
    ventana_dias:     int
    total:            int
    ok:               int
    errores:          int
    en_proceso:       int
    filas_ok:         int
    filas_rechazadas: int
    tasa_exito_pct:   float
