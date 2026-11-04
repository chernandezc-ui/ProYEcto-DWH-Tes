"""
schemas/reinyeccion/respuesta.py
==================================
Schemas de SALIDA para la Herramienta de Reinyección MDM.
"""
from pydantic import BaseModel, Field, model_validator


class RespuestaConteoReinyeccion(BaseModel):
    """Cuántos registros están disponibles para reinyección."""
    candidatos: int = Field(description="Total de registros RESUELTOS listos para reinyectar.")


class RespuestaReinyeccion(BaseModel):
    """Resultado de una ejecución masiva de reinyección."""
    reinyectados: int       = Field(description="Filas restauradas a Estado_Carga=CARGADO en Bronce.")
    omitidos:     int       = Field(description="Filas no reinyectadas (tabla no mapeada o sin ID origen).")
    detalle:      list[str] = Field(description="Detalle por tabla con el resultado de cada operación.")
    mensaje:      str       = Field(default="", description="Mensaje de resumen para el usuario.")

    @model_validator(mode="after")
    def _generar_mensaje(self) -> "RespuestaReinyeccion":
        if not self.mensaje:
            if self.reinyectados > 0:
                self.mensaje = (
                    f"{self.reinyectados} registros reactivados en Bronce. "
                    "Ya pueden ser procesados por el pipeline."
                )
            else:
                self.mensaje = (
                    f"No se encontraron candidatos para reinyectar "
                    f"(omitidos: {self.omitidos})."
                )
        return self
