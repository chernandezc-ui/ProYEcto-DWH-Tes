from pydantic import BaseModel, Field

class SolicitudActualizarParametro(BaseModel):
    valor: str = Field(..., min_length=1, max_length=500, description="Nuevo valor del parámetro")

class ItemParametroBatch(BaseModel):
    nombre_parametro: str
    valor: str

class SolicitudBatchParametros(BaseModel):
    parametros: list[ItemParametroBatch]
