from collections.abc import Mapping
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, model_validator

from dominio.proyecciones import preparar_parametros

class PeticionEjecutarProyeccion(BaseModel):
    id_tiempo: int = Field(..., description="ID del tiempo base (YYYYMMDD)")
    matriz_inputs: Optional[Dict[str, Dict[int, Optional[float]]]] = Field(
        None, description="Matriz de inputs por estado fenológico"
    )
    margen_pesimista: float = Field(0.9906, description="Margen pesimista")
    margen_optimista: float = Field(1.0107, description="Margen optimista")
    modulo: Optional[int] = Field(None, description="Filtro opcional por módulo")
    variedad: Optional[str] = Field(None, description="Filtro opcional por variedad")
    condicion: Optional[str] = Field(None, description="Filtro opcional por condición")
    fundo: Optional[str] = Field(None, description="Filtro opcional por fundo")

    @model_validator(mode="before")
    @classmethod
    def validar_parametros(cls, datos: Any) -> Any:
        if not isinstance(datos, Mapping) or "id_tiempo" not in datos:
            return datos

        # Validar los valores originales evita que la coerción numérica de
        # Pydantic convierta booleanos en porcentajes, márgenes o fechas.
        _, matriz_normalizada = preparar_parametros(
            id_tiempo=datos["id_tiempo"],
            matriz_inputs=datos.get("matriz_inputs"),
            margen_pesimista=datos.get("margen_pesimista", 0.9906),
            margen_optimista=datos.get("margen_optimista", 1.0107),
        )
        normalizados = dict(datos)
        if datos.get("matriz_inputs") is not None:
            normalizados["matriz_inputs"] = matriz_normalizada
        return normalizados
