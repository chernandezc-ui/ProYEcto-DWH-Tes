from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class FiltrosWidget(BaseModel):
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    dimension_valor: Optional[str] = None


VistaNombre = Literal[
    "vw_cosecha_mensual",
    "vw_rendimiento_zona",
    "vw_cosecha_variedad",
    "vw_rendimiento_historico",
    "vw_correlacion",
    "vw_resumen_periodo",
]


class ConfigWidget(BaseModel):
    tipo: Literal["linea", "barra", "area", "scatter", "pie", "kpi", "tabla", "forecast"]
    vista: VistaNombre  # Pydantic rechaza cualquier valor fuera del conjunto
    eje_x: Optional[str] = None
    eje_y: Optional[str] = None
    grupo_by: Optional[str] = None
    metrica: Optional[str] = None
    columnas: Optional[list[str]] = None
    top_n: int = Field(default=50, ge=1, le=500)
    filtros: FiltrosWidget = Field(default_factory=FiltrosWidget)
    forecast_periodos: int = Field(default=0, ge=0, le=24)


class RespuestaWidget(BaseModel):
    data: list[dict[str, Any]]
    layout: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)


class InfoVista(BaseModel):
    nombre: str
    label: str
    descripcion: str
    columnas: list[str]
    tipos: dict[str, str]


class ItemNotificacion(BaseModel):
    id: str
    tipo: Literal["etl_failure", "cuarentena", "umbral_calidad", "etl_ok", "info"]
    severidad: Literal["error", "warning", "info"]
    titulo: str
    descripcion: str
    timestamp: str
    leida: bool = False
    link: Optional[str] = None


class RespuestaNotificaciones(BaseModel):
    items: list[ItemNotificacion]
    total: int
    no_leidas: int
