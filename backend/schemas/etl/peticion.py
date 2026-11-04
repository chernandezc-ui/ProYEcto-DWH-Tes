"""
schemas/etl/peticion.py
========================
Schemas de ENTRADA para el módulo ETL.
Versión 2: iniciado_por se elimina del body — se extrae del token JWT.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from nucleo.etl_catalogo import listar_facts_disponibles


def _obtener_facts_validos() -> frozenset[str]:
    try:
        return frozenset(f["nombre_fact"] for f in listar_facts_disponibles())
    except Exception:
        return frozenset()  # fallback vacío si ETL no está en path (tests, CI, etc.)


_FACTS_VALIDOS: frozenset[str] = _obtener_facts_validos()

_PATRON_FACT = re.compile(r"^[A-Za-z0-9_]+$")


class PeticionIniciarCorrida(BaseModel):
    """
    Cuerpo de la petición para iniciar una corrida del pipeline ETL.

    IMPORTANTE: el campo 'iniciado_por' ya no es parte del body.
    El backend lo deriva del usuario autenticado (JWT).
    """
    comentario: str | None = Field(
        default=None,
        description="Comentario opcional para registrar en la auditoría.",
        max_length=500,
    )
    modo_ejecucion: Literal["completo", "facts"] = Field(
        default="completo",
        description="Modo de corrida. 'facts' habilita reproceso dirigido.",
    )
    facts: list[str] | None = Field(
        default=None,
        description="Facts a reprocesar cuando modo_ejecucion='facts'.",
        max_length=20,
    )
    incluir_dependencias: bool = Field(
        default=True,
        description="Ejecuta dimensiones y SPs dependientes antes del reproceso.",
    )
    refrescar_gold: bool = Field(
        default=True,
        description="Refresca los marts Gold impactados.",
    )
    forzar_relectura_bronce: bool = Field(
        default=True,
        description="Reabre filas PROCESADO/RECHAZADO en Bronce antes del reproceso.",
    )

    @field_validator("facts")
    @classmethod
    def validar_facts(cls, v: list[str] | None) -> list[str] | None:
        if not v:
            return v
        for fact in v:
            if not _PATRON_FACT.match(fact):
                raise ValueError(f"Nombre de fact con caracteres no permitidos: {fact!r}")
            if fact not in _FACTS_VALIDOS:
                raise ValueError(f"Fact desconocido: {fact!r}. Válidos: {sorted(_FACTS_VALIDOS)}")
        return v

    @model_validator(mode="after")
    def validar_modo_y_facts(self) -> "PeticionIniciarCorrida":
        if self.modo_ejecucion == "facts" and not self.facts:
            raise ValueError("facts es obligatorio cuando modo_ejecucion='facts'.")
        return self
