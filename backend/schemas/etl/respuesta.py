"""
schemas/etl/respuesta.py
=========================
Schemas de SALIDA para el módulo ETL.
Nunca se reutilizan como schemas de petición.
"""
from datetime import datetime
from pydantic import BaseModel, Field

class RespuestaCorridaIniciada(BaseModel):
    """Respuesta al cliente cuando se acepta una corrida ETL."""
    id_corrida:     str        = Field(description="UUID único de la corrida para suscribirse al SSE.")
    id_log:         int | None = Field(default=None, description="ID del registro en Auditoria.Log_Carga (None hasta que el runner arranca).")
    iniciado_por:   str        = Field(description="Quién inició la corrida.")
    fecha_inicio:   datetime   = Field(description="Timestamp de solicitud registrado.")
    url_stream:     str        = Field(description="URL para suscribirse al stream SSE de esta corrida.")
    estado: str = Field(
        default="PENDIENTE",
        description="Estado de la corrida. Valores: PENDIENTE → EJECUTANDO → OK | ERROR | CANCELADO | TIMEOUT.",
    )

    model_config = {"from_attributes": True}

class RespuestaHistorialCorrida(BaseModel):
    """Una entrada del historial de corridas de Auditoria.Log_Carga."""
    id_log:             int
    nombre_proceso:     str
    tabla_destino:      str
    nombre_archivo:     str | None      = Field(default=None)
    fecha_inicio:       datetime | None = Field(default=None)
    fecha_fin:          datetime | None = Field(default=None)
    estado:             str
    filas_insertadas:   int
    filas_rechazadas:   int
    duracion_segundos:  int | None      = Field(default=None)
    mensaje_error:      str | None      = Field(default=None)
    # UUID del Control.Corrida asociado, si existe. Permite linkear al detalle.
    id_corrida:         str | None      = Field(default=None)

    model_config = {"from_attributes": True}

class RespuestaPasoCorrida(BaseModel):
    id_paso: int
    id_corrida: str
    nombre_paso: str
    orden: int
    estado: str
    fecha_inicio: datetime | None  = Field(default=None)
    fecha_fin:    datetime | None  = Field(default=None)
    mensaje_error: str | None      = Field(default=None)

    model_config = {"from_attributes": True}

class RespuestaDetalleCorrida(BaseModel):
    id_corrida: str
    iniciado_por: str
    comentario:          str | None      = Field(default=None)
    estado: str
    intento_numero: int
    max_reintentos: int
    fecha_solicitud:     datetime | None = Field(default=None)
    fecha_inicio:        datetime | None = Field(default=None)
    fecha_fin:           datetime | None = Field(default=None)
    pid_runner:          int | None      = Field(default=None)
    heartbeat_ultimo:    datetime | None = Field(default=None)
    timeout_segundos: int
    mensaje_final:       str | None      = Field(default=None)
    id_log_auditoria:    int | None      = Field(default=None)
    modo_ejecucion: str
    facts: list[str]
    incluir_dependencias: bool
    refrescar_gold: bool
    forzar_relectura_bronce: bool
    pasos: list[RespuestaPasoCorrida] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class RespuestaFactDisponible(BaseModel):
    nombre_fact: str
    orden: int
    tabla_destino: str
    fuentes_bronce: list[str]
    dependencias: list[str]
    marts: list[str]
    releer_bronce_por_estado: bool
    estrategia_rerun: str

    model_config = {"from_attributes": True}
