"""
schemas/alertas/peticion.py
============================
Schemas de ENTRADA para el módulo Alertas.
El usuario se extrae del token JWT, no del body.
"""
from pydantic import BaseModel, Field


class PeticionAckAlerta(BaseModel):
    """Cuerpo para marcar una alerta como atendida."""
    comentario: str | None = Field(
        default=None,
        description="Comentario opcional sobre la atención.",
        max_length=500,
    )
