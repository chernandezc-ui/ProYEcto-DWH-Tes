"""
schemas/auth/peticion.py
=========================
Schemas de ENTRADA para el módulo de autenticación.
"""

from pydantic import BaseModel, Field


class PeticionLogin(BaseModel):
    """Credenciales para iniciar sesión."""
    nombre_usuario: str = Field(
        description="Nombre de usuario (login).",
        min_length=1,
        max_length=100,
    )
    clave: str = Field(
        description="Contraseña en texto plano (nunca se almacena ni se retorna).",
        min_length=1,
        max_length=200,
    )


class PeticionCrearUsuario(BaseModel):
    """Cuerpo para crear un nuevo usuario (solo admin)."""
    nombre_usuario: str = Field(min_length=3, max_length=100)
    nombre_display: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    clave: str = Field(
        description="Contraseña inicial en texto plano.",
        min_length=8,
        max_length=200,
    )
    rol: str = Field(
        description="Rol del usuario: admin | operador_etl | analista_mdm | viewer",
    )


class PeticionCambiarClave(BaseModel):
    """Solicitud de cambio de contraseña."""
    clave_actual: str = Field(min_length=1, max_length=200)
    clave_nueva: str = Field(min_length=8, max_length=200)
