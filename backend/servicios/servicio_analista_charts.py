from __future__ import annotations

import asyncio
import json
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from sqlalchemy import text

from nucleo.conexion import obtener_engine
from schemas.analista.modelos import ConfigWidget, RespuestaWidget, InfoVista

_TEMPLATE = "plotly_dark"

CATALOGO_VISTAS: list[InfoVista] = [
    InfoVista(
        nombre="vw_cosecha_mensual",
        label="Cosecha mensual",
        descripcion="Producción mensual por variedad y módulo (Silver.Fact_Cosecha_SAP)",
        columnas=["fecha", "variedad", "zona", "toneladas", "kg_neto"],
        tipos={"fecha": "fecha", "variedad": "texto", "zona": "texto",
               "toneladas": "numero", "kg_neto": "numero"},
    ),
    InfoVista(
        nombre="vw_rendimiento_zona",
        label="Cosecha por módulo",
        descripcion="Toneladas cosechadas por módulo y mes",
        columnas=["fecha", "zona", "toneladas"],
        tipos={"fecha": "fecha", "zona": "texto", "toneladas": "numero"},
    ),
    InfoVista(
        nombre="vw_cosecha_variedad",
        label="Cosecha por variedad",
        descripcion="Distribución de cosecha por variedad",
        columnas=["variedad", "toneladas", "porcentaje"],
        tipos={"variedad": "texto", "toneladas": "numero", "porcentaje": "numero"},
    ),
    InfoVista(
        nombre="vw_rendimiento_historico",
        label="Histórico cosecha diaria",
        descripcion="Serie histórica diaria de kg cosechados",
        columnas=["fecha", "rendimiento_tha"],
        tipos={"fecha": "fecha", "rendimiento_tha": "numero"},
    ),
    InfoVista(
        nombre="vw_correlacion",
        label="Cosecha por módulo (mensual)",
        descripcion="Toneladas por módulo y mes — base para correlación",
        columnas=["fecha", "mm_lluvia", "temperatura_media", "rendimiento_tha", "zona"],
        tipos={"fecha": "fecha", "mm_lluvia": "numero", "temperatura_media": "numero",
               "rendimiento_tha": "numero", "zona": "texto"},
    ),
    InfoVista(
        nombre="vw_resumen_periodo",
        label="Resumen de período",
        descripcion="KPIs agregados de cosecha",
        columnas=["metrica", "valor", "valor_periodo_anterior", "delta_pct"],
        tipos={"metrica": "texto", "valor": "numero",
               "valor_periodo_anterior": "numero", "delta_pct": "numero"},
    ),
]


def listar_vistas() -> list[InfoVista]:
    return CATALOGO_VISTAS


def _info_vista(nombre: str) -> InfoVista:
    for v in CATALOGO_VISTAS:
        if v.nombre == nombre:
            return v
    raise ValueError(f"Vista '{nombre}' no existe en el catálogo.")


def _build_query(config: ConfigWidget) -> tuple[str, dict[str, Any]]:
    """Construye la SQL y params para la vista pedida usando tablas Silver reales."""
    fil = config.filtros
    params: dict[str, Any] = {}
    date_cond = ""
    if fil.fecha_desde:
        date_cond += " AND f.Fecha_Evento >= :fecha_desde"
        params["fecha_desde"] = fil.fecha_desde
    if fil.fecha_hasta:
        date_cond += " AND f.Fecha_Evento <= :fecha_hasta"
        params["fecha_hasta"] = fil.fecha_hasta
    n = config.top_n
    v = config.vista

    if v == "vw_cosecha_mensual":
        sql = f"""
            SELECT TOP {n}
                DATEFROMPARTS(YEAR(f.Fecha_Evento), MONTH(f.Fecha_Evento), 1) AS fecha,
                vr.Nombre_Variedad AS variedad,
                m.Modulo                            AS zona,
                CAST(SUM(f.Kg_Neto_MP)/1000.0 AS FLOAT) AS toneladas,
                CAST(SUM(f.Kg_Neto_MP)         AS FLOAT) AS kg_neto
            FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK)
            JOIN Silver.Dim_Variedad          vr ON f.ID_Variedad = vr.ID_Variedad
            JOIN Silver.Dim_Geografia          g ON f.ID_Geografia = g.ID_Geografia
            JOIN Silver.Dim_Modulo_Catalogo    m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
            WHERE 1=1 {date_cond}
            GROUP BY DATEFROMPARTS(YEAR(f.Fecha_Evento), MONTH(f.Fecha_Evento), 1),
                     vr.Nombre_Variedad, m.Modulo
            ORDER BY fecha DESC
        """

    elif v == "vw_rendimiento_zona":
        sql = f"""
            SELECT TOP {n}
                DATEFROMPARTS(YEAR(f.Fecha_Evento), MONTH(f.Fecha_Evento), 1) AS fecha,
                m.Modulo                            AS zona,
                CAST(SUM(f.Kg_Neto_MP)/1000.0 AS FLOAT) AS toneladas
            FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK)
            JOIN Silver.Dim_Geografia          g ON f.ID_Geografia = g.ID_Geografia
            JOIN Silver.Dim_Modulo_Catalogo    m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
            WHERE 1=1 {date_cond}
            GROUP BY DATEFROMPARTS(YEAR(f.Fecha_Evento), MONTH(f.Fecha_Evento), 1), m.Modulo
            ORDER BY fecha DESC
        """

    elif v == "vw_cosecha_variedad":
        sql = f"""
            WITH cte AS (
                SELECT vr.Nombre_Variedad AS variedad,
                       SUM(f.Kg_Neto_MP)/1000.0 AS ton
                FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK)
                JOIN Silver.Dim_Variedad vr ON f.ID_Variedad = vr.ID_Variedad
                WHERE 1=1 {date_cond}
                GROUP BY vr.Nombre_Variedad
            )
            SELECT TOP {n}
                variedad,
                CAST(ton AS FLOAT) AS toneladas,
                CAST(ROUND(100.0 * ton / NULLIF(SUM(ton) OVER(), 0), 2) AS FLOAT) AS porcentaje
            FROM cte
            ORDER BY ton DESC
        """

    elif v == "vw_rendimiento_historico":
        sql = f"""
            SELECT TOP {n}
                CONVERT(DATE, f.Fecha_Evento)          AS fecha,
                CAST(SUM(f.Kg_Neto_MP)/1000.0 AS FLOAT) AS rendimiento_tha
            FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK)
            WHERE 1=1 {date_cond}
            GROUP BY CONVERT(DATE, f.Fecha_Evento)
            ORDER BY fecha
        """

    elif v == "vw_correlacion":
        sql = f"""
            SELECT TOP {n}
                DATEFROMPARTS(YEAR(f.Fecha_Evento), MONTH(f.Fecha_Evento), 1) AS fecha,
                CAST(0.0 AS FLOAT)                      AS mm_lluvia,
                CAST(0.0 AS FLOAT)                      AS temperatura_media,
                CAST(SUM(f.Kg_Neto_MP)/1000.0 AS FLOAT) AS rendimiento_tha,
                m.Modulo                                 AS zona
            FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK)
            JOIN Silver.Dim_Geografia          g ON f.ID_Geografia = g.ID_Geografia
            JOIN Silver.Dim_Modulo_Catalogo    m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
            WHERE 1=1 {date_cond}
            GROUP BY DATEFROMPARTS(YEAR(f.Fecha_Evento), MONTH(f.Fecha_Evento), 1), m.Modulo
            ORDER BY fecha DESC
        """

    elif v == "vw_resumen_periodo":
        # date_cond aplica a las subconsultas; f siempre referencia Fact_Cosecha_SAP
        sub = f"WHERE 1=1 {date_cond}"
        sql = f"""
            SELECT TOP 10
                kpi AS metrica,
                CAST(valor AS FLOAT)            AS valor,
                CAST(0       AS FLOAT)           AS valor_periodo_anterior,
                CAST(0.0     AS FLOAT)           AS delta_pct
            FROM (
                SELECT 'Cosecha total (t)' AS kpi,
                       ISNULL(SUM(f.Kg_Neto_MP)/1000.0, 0) AS valor
                FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK) {sub}
                UNION ALL
                SELECT 'Variedades activas',
                       ISNULL(COUNT(DISTINCT f.ID_Variedad) * 1.0, 0)
                FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK) {sub}
                UNION ALL
                SELECT 'Módulos cosechados',
                       ISNULL(COUNT(DISTINCT g.ID_Modulo_Catalogo) * 1.0, 0)
                FROM Silver.Fact_Cosecha_SAP f WITH (NOLOCK)
                JOIN Silver.Dim_Geografia g ON f.ID_Geografia = g.ID_Geografia {sub}
            ) AS stats
        """

    else:
        raise ValueError(f"Vista '{v}' no reconocida en el catálogo.")

    return sql.strip(), params


def _cargar_datos(config: ConfigWidget) -> pd.DataFrame:
    info = _info_vista(config.vista)
    if config.grupo_by and config.grupo_by not in info.columnas:
        raise ValueError(
            f"Columna '{config.grupo_by}' no existe en la vista '{config.vista}'."
        )
    sql_str, params = _build_query(config)
    engine = obtener_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql_str), conn, params=params)


def _fig_response(fig: go.Figure, df: pd.DataFrame) -> RespuestaWidget:
    # plotly.io.to_json usa el PlotlyJSONEncoder, que convierte numpy.ndarray,
    # fechas y otros tipos no nativos a JSON. Volvemos a parsear a dict puro
    # para que Pydantic pueda serializar la respuesta sin errores.
    d = json.loads(pio.to_json(fig))
    return RespuestaWidget(data=d["data"], layout=d.get("layout", {}), meta={"filas": len(df)})


def _linea(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    if not c.eje_x or not c.eje_y:
        raise ValueError("tipo 'linea' requiere eje_x y eje_y.")
    return px.line(df, x=c.eje_x, y=c.eje_y, color=c.grupo_by, template=_TEMPLATE)


def _barra(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    if not c.eje_x or not c.eje_y:
        raise ValueError("tipo 'barra' requiere eje_x y eje_y.")
    return px.bar(df, x=c.eje_x, y=c.eje_y, color=c.grupo_by, barmode="group", template=_TEMPLATE)


def _area(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    if not c.eje_x or not c.eje_y:
        raise ValueError("tipo 'area' requiere eje_x y eje_y.")
    return px.area(df, x=c.eje_x, y=c.eje_y, color=c.grupo_by, template=_TEMPLATE)


def _scatter(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    if not c.eje_x or not c.eje_y:
        raise ValueError("tipo 'scatter' requiere eje_x y eje_y.")
    return px.scatter(df, x=c.eje_x, y=c.eje_y, color=c.grupo_by, template=_TEMPLATE)


def _pie(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    if not c.eje_x or not c.eje_y:
        raise ValueError("tipo 'pie' requiere eje_x (dimensión) y eje_y (valor).")
    return px.pie(df, names=c.eje_x, values=c.eje_y, hole=0.4, template=_TEMPLATE)


def _kpi(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    col = c.metrica or c.eje_y
    if not col:
        raise ValueError("tipo 'kpi' requiere 'metrica' o 'eje_y'.")
    val = float(df[col].sum()) if col in df.columns else 0.0
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=val,
        delta={"reference": val * 0.9, "relative": True},
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(template=_TEMPLATE, margin=dict(t=20, b=20))
    return fig


def _tabla(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    cols = c.columnas or list(df.columns[:6])
    cols_validos = [col for col in cols if col in df.columns]
    if not cols_validos:
        raise ValueError("Ninguna columna configurada existe en los datos de la vista.")
    df_v = df[cols_validos].head(c.top_n)
    fig = go.Figure(go.Table(
        header=dict(values=cols_validos, fill_color="#1e293b",
                    font=dict(color="#e2e8f0", size=12), align="left"),
        cells=dict(values=[df_v[col].tolist() for col in cols_validos],
                   fill_color="#0a0f1e", font=dict(color="#94a3b8", size=11), align="left"),
    ))
    fig.update_layout(template=_TEMPLATE, margin=dict(t=10, b=10))
    return fig


def _forecast(c: ConfigWidget, df: pd.DataFrame) -> go.Figure:
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
    except ImportError as exc:
        raise ValueError("statsmodels no está instalado. Ejecuta: pip install statsmodels") from exc
    if not c.eje_x or not c.eje_y:
        raise ValueError("tipo 'forecast' requiere eje_x (fecha) y eje_y.")
    df = df.sort_values(c.eje_x)
    serie = df[c.eje_y].dropna()
    if len(serie) < 4:
        raise ValueError("Se necesitan al menos 4 puntos históricos para forecast.")
    n = c.forecast_periodos or 3
    fit = ExponentialSmoothing(serie, trend="add", seasonal=None).fit(optimized=True)
    forecast = fit.forecast(n)
    x_hist = df[c.eje_x].tolist()
    y_hist = df[c.eje_y].tolist()
    try:
        last = pd.to_datetime(x_hist[-1])
        x_fut = [(last + pd.DateOffset(months=i + 1)).strftime("%Y-%m") for i in range(n)]
    except Exception:
        x_fut = [f"T+{i+1}" for i in range(n)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_hist, y=y_hist, mode="lines+markers", name="Histórico",
                             line=dict(color="#60a5fa")))
    fig.add_trace(go.Scatter(x=x_fut, y=forecast.tolist(), mode="lines+markers",
                             name="Proyección", line=dict(color="#a78bfa", dash="dot")))
    fig.update_layout(template=_TEMPLATE)
    return fig


_BUILDERS = {
    "linea": _linea, "barra": _barra, "area": _area, "scatter": _scatter,
    "pie": _pie, "kpi": _kpi, "tabla": _tabla, "forecast": _forecast,
}


async def generar_figura(config: ConfigWidget) -> RespuestaWidget:
    builder = _BUILDERS.get(config.tipo)
    if not builder:
        raise ValueError(f"Tipo de widget desconocido: {config.tipo}")
    loop = asyncio.get_running_loop()
    df = await loop.run_in_executor(None, _cargar_datos, config)
    if df.empty:
        raise ValueError(
            f"La vista '{config.vista}' no devolvió datos para los filtros aplicados."
        )

    def _build() -> RespuestaWidget:
        fig = builder(config, df)
        return _fig_response(fig, df)

    return await loop.run_in_executor(None, _build)
