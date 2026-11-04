from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

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
