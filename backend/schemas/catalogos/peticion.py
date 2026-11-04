"""
schemas/catalogos/peticion.py
==============================
Schemas de ENTRADA para operaciones de escritura sobre catálogos.
Solo el rol 'admin' puede usar estos endpoints.

  · PeticionCrearVariedad      → MDM.Catalogo_Variedades  (reservado, aún no expuesto)
  · PeticionCrearDimVariedad   → Silver.Dim_Variedad       (crear/desactivar/reactivar)
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PeticionCrearVariedad(BaseModel):
    """Payload para crear una nueva variedad en MDM.Catalogo_Variedades."""

    nombre_canonico: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nombre canónico oficial de la variedad (único en el catálogo).",
    )
    breeder: str | None = Field(
        default=None,
        max_length=100,
        description="Casa o institución que desarrolló la variedad. Opcional.",
    )

    @field_validator("nombre_canonico", mode="before")
    @classmethod
    def normalizar_nombre(cls, v: str) -> str:
        """Elimina espacios extremos."""
        return str(v).strip()

    @field_validator("breeder", mode="before")
    @classmethod
    def normalizar_breeder(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None


class PeticionCrearDimVariedad(BaseModel):
    """Payload para crear una nueva variedad en Silver.Dim_Variedad."""

    nombre_variedad: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nombre de la variedad (debe ser único en la dimensión DWH).",
    )
    breeder: str | None = Field(
        default=None,
        max_length=100,
        description="Casa o institución que desarrolló la variedad. Opcional.",
    )

    @field_validator("nombre_variedad", mode="before")
    @classmethod
    def normalizar_nombre(cls, v: str) -> str:
        return str(v).strip()

    @field_validator("breeder", mode="before")
    @classmethod
    def normalizar_breeder(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

