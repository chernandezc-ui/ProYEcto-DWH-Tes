"""
schemas/alertas/respuesta.py
=============================
Schemas de SALIDA para el módulo Alertas.
"""
from datetime import datetime
from pydantic import BaseModel


class RespuestaAckAlerta(BaseModel):
    """Una alerta atendida (registro de MDM.Alerta_Ack)."""
    id_alerta:   str
    usuario_dni: str
    fecha_ack:   datetime
    comentario:  str | None

    model_config = {"from_attributes": True}


class RespuestaAccionAck(BaseModel):
    """Resultado de marcar/desmarcar."""
    id_alerta: str
    accion:    str   # "ack" | "unack"
    mensaje:   str
