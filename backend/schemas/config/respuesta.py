from __future__ import annotations
from pydantic import BaseModel


class RespuestaRegla(BaseModel):
    tabla_destino:   str | None
    columna:         str | None
    tipo_validacion: str | None
    valor_min:       float | None
    valor_max:       float | None
    accion:          str | None
    activo:          bool

    model_config = {"from_attributes": True}


class KpisReglas(BaseModel):
    total:    int
    activas:  int
    inactivas: int


class RespuestaPaginadaReglas(BaseModel):
    total:  int
    pagina: int
    tamano: int
    kpis:   KpisReglas
    datos:  list[RespuestaRegla]


class RespuestaParametro(BaseModel):
    nombre_parametro:    str
    valor:               str | None
    descripcion:         str | None
    fecha_modificacion:  str | None

    model_config = {"from_attributes": True}


class RespuestaPaginadaParametros(BaseModel):
    total:  int
    pagina: int
    tamano: int
    datos:  list[RespuestaParametro]
