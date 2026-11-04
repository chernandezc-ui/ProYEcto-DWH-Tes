"""
schemas/catalogos/respuesta.py
===============================
Schemas de SALIDA para catálogos MDM y Silver.
Separados por modelo de dominio.
"""
from datetime import datetime

from pydantic import BaseModel

class RespuestaVariedad(BaseModel):
    """Fila de MDM.Catalogo_Variedades."""
    nombre_canonico: str
    breeder:         str | None
    es_activa:       bool

    model_config = {"from_attributes": True}


class RespuestaDimVariedad(BaseModel):
    """Fila de Silver.Dim_Variedad (dimensión DWH homologada)."""
    id_variedad:         int
    nombre_variedad:     str
    breeder:             str | None
    es_activa:           bool
    fecha_creacion:      datetime | None = None
    fecha_modificacion:  datetime | None = None

    model_config = {"from_attributes": True}


class RespuestaOperacionVariedad(BaseModel):
    """Respuesta de operaciones de escritura sobre Silver.Dim_Variedad."""
    ok:      bool
    mensaje: str
    dato:    dict | None = None

class RespuestaGeografia(BaseModel):
    """Fila de Silver.Dim_Geografia."""
    fundo:        str | None
    sector:       str | None
    modulo:       int | None
    turno:        int | None
    valvula:      str | None
    cama:         str | None
    es_test_block: bool
    codigo_sap_campo: str | None
    es_vigente:    bool

    model_config = {"from_attributes": True}

class RespuestaPersonal(BaseModel):
    """Fila de Silver.Dim_Personal."""
    dni:               str | None
    nombre_completo:   str | None
    rol:               str | None
    sexo:              str | None
    id_planilla:       str | None
    pct_asertividad:   float | None
    dias_ausentismo:   int | None

    model_config = {"from_attributes": True}

class RespuestaPaginadaCatalogo(BaseModel):
    """Wrapper genérico de paginación para catálogos."""
    total:  int
    pagina: int
    tamano: int
    datos:  list  # El router tipará correctamente en la firma