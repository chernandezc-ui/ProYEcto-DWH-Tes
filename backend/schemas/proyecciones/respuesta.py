from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class FilaSemanas(BaseModel):
    semana: int
    semana_label: str
    fecha_semana: str
    kg_proyectados: float
    kg_pesimista: float = 0.0
    kg_optimista: float = 0.0
    kg_anterior: float
    pct_variacion: float
    tendencia: str

class RespuestaProyeccion(BaseModel):
    df_semanal: List[FilaSemanas]
    kpis: Dict[str, Any]
    # Optionally we can return the detail rows if the frontend needs it,
    # but returning a large list of dicts.
    df_detalle: Optional[List[Dict[str, Any]]] = None
