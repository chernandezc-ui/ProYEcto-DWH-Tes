"""
schemas/auth/respuesta.py
==========================
Schemas de SALIDA para el módulo de autenticación.

IMPORTANTE: ningún schema de respuesta incluye hash_clave ni clave en texto plano.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class PerfilUsuario(BaseModel):
    """Perfil público del usuario autenticado."""
    nombre_usuario: str
    nombre_display: str
    rol:            str
    email:          str | None

class TokenRespuesta(BaseModel):
    """Respuesta al login exitoso."""
    access_token: str  = Field(description="JWT Bearer token.")
    token_type:   str  = Field(default="bearer")
    usuario:      PerfilUsuario

class RespuestaUsuarioAdmin(BaseModel):
    """Representación de un usuario para el panel admin (sin hash_clave)."""
    id_usuario:     int
    nombre_usuario: str
    nombre_display: str
    email:          str | None
    rol:            str
    es_activo:      bool
    fecha_creacion: datetime | None
    ultimo_acceso:  datetime | None
    model_config = {"from_attributes": True}

class RespuestaMensaje(BaseModel):
    """Respuesta simple de confirmación."""
    mensaje: str
    ok:      bool = True