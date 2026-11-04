from __future__ import annotations
import datetime as dt
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger
import json

log = obtener_logger(__name__)

def _ejecutar_query_df(sql: str, params: Dict[str, Any] = None) -> pd.DataFrame:
    try:
        with obtener_engine().connect() as con:
            df = pd.read_sql(text(sql), con, params=params)
        return df
    except SQLAlchemyError as e:
        log.exception(f"Error ejecutando query: {str(e)}")
        raise ErrorBaseDatos()

def obtener_fechas_disponibles() -> List[int]:
    sql = """
        SELECT MAX(f.ID_Tiempo) as ID_Tiempo
        FROM (
            SELECT ID_Tiempo FROM Silver.Fact_Conteo_Fenologico WITH (NOLOCK)
            UNION
            SELECT ID_Tiempo FROM Silver.Fact_Peladas WITH (NOLOCK)
            UNION
            SELECT ID_Tiempo FROM Silver.Fact_Evaluacion_Pesos WITH (NOLOCK)
        ) f
        JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
        GROUP BY dt.Anio, dt.Semana_ISO
        ORDER BY ID_Tiempo DESC
    """
    df = _ejecutar_query_df(sql)
    return df["ID_Tiempo"].tolist() if not df.empty else []

def obtener_combinaciones_disponibles(id_tiempo: int) -> pd.DataFrame:
    sql = """
        SELECT DISTINCT
            f_cat.Fundo                                    AS Fundo,
            CAST(m_cat.Modulo AS NVARCHAR(50))             AS Modulo,
            v.Nombre_Variedad                              AS Variedad,
            ISNULL(cc.Sustrato + ' - ' + cc.Certificacion,
                   'Sin condición')                        AS Condicion
        FROM Silver.Fact_Conteo_Fenologico f WITH (NOLOCK)
        JOIN Silver.Dim_Variedad v WITH (NOLOCK)
            ON f.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK)
            ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m_cat WITH (NOLOCK)
            ON g.ID_Modulo_Catalogo = m_cat.ID_Modulo_Catalogo
        JOIN Silver.Dim_Fundo_Catalogo f_cat WITH (NOLOCK)
            ON g.ID_Fundo_Catalogo = f_cat.ID_Fundo_Catalogo
        LEFT JOIN Silver.Fact_Cosecha_SAP cs WITH (NOLOCK)
            ON cs.ID_Geografia = g.ID_Geografia
           AND cs.ID_Variedad  = f.ID_Variedad
        LEFT JOIN Silver.Dim_Condicion_Cultivo cc WITH (NOLOCK)
            ON cs.ID_Condicion_Cultivo = cc.ID_Condicion
        WHERE f.ID_Tiempo = :t
    """
    df = _ejecutar_query_df(sql, {"t": id_tiempo})
    if not df.empty:
        for col in ["Fundo", "Modulo", "Variedad", "Condicion"]:
            df[col] = df[col].astype(str).fillna("Sin condición")
    return df.drop_duplicates().reset_index(drop=True) if not df.empty else pd.DataFrame(columns=["Fundo", "Modulo", "Variedad", "Condicion"])

def verificar_integridad_datos(id_tiempo: int, modulo: Optional[int] = None, variedad: Optional[str] = None, condicion: Optional[str] = None) -> Dict[str, bool]:
    res = {"conteo": False, "peladas": False, "pesos": False}
    
    filtro_c = ""
    params_c = {"t": id_tiempo}
    if modulo:
        filtro_c += " AND m.Modulo = :m"
        params_c["m"] = modulo
    if variedad:
        filtro_c += " AND v.Nombre_Variedad = :v"
        params_c["v"] = variedad

    df_c = _ejecutar_query_df(
        f"""SELECT TOP 1 1
        FROM Silver.Fact_Conteo_Fenologico f WITH (NOLOCK)
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON f.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
        WHERE dt.Anio = (SELECT Anio FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          AND dt.Semana_ISO = (SELECT Semana_ISO FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          {filtro_c}""",
        params_c,
    )
    res["conteo"] = not df_c.empty
    
    df_p = _ejecutar_query_df("SELECT TOP 1 1 FROM Silver.Fact_Censo_Plantas WITH (NOLOCK)")
    res["peladas"] = not df_p.empty
    
    filtro_w = ""
    params_w = {"t": id_tiempo}
    if variedad:
        filtro_w = " AND v.Nombre_Variedad = :v"
        params_w["v"] = variedad

    df_w = _ejecutar_query_df(
        f"""SELECT TOP 1 1
        FROM Silver.Fact_Evaluacion_Pesos p WITH (NOLOCK)
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON p.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Tiempo dt ON p.ID_Tiempo = dt.ID_Tiempo
        WHERE dt.Anio = (SELECT Anio FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          AND dt.Semana_ISO = (SELECT Semana_ISO FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          {filtro_w}""",
        params_w,
    )
    res["pesos"] = not df_w.empty
    return res

def extraer_datos_granulares(
    id_tiempo: int,
    modulo: Optional[int] = None,
    variedad: Optional[str] = None,
    condicion: Optional[str] = None,
    fundo: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    filtro_conteo = ""
    filtro_plantas = ""
    params_conteo = {"t": id_tiempo}
    params_plantas = {"t": id_tiempo}

    if modulo:
        filtro_conteo += " AND m.Modulo = :m"
        filtro_plantas += " AND m.Modulo = :m"
        params_conteo["m"] = modulo
        params_plantas["m"] = modulo
    if variedad:
        filtro_conteo += " AND v.Nombre_Variedad = :v"
        params_conteo["v"] = variedad
    if fundo:
        filtro_conteo += " AND f_cat.Fundo = :fnd"
        filtro_plantas += " AND f_cat.Fundo = :fnd"
        params_conteo["fnd"] = fundo
        params_plantas["fnd"] = fundo
    if condicion:
        partes = condicion.split(" - ")
        if len(partes) == 2:
            sus, cert = partes[0], partes[1]
            filtro_cond = (
                " AND g.ID_Geografia IN ("
                "SELECT cs.ID_Geografia FROM Silver.Fact_Cosecha_SAP cs "
                "JOIN Silver.Dim_Condicion_Cultivo c ON cs.ID_Condicion_Cultivo = c.ID_Condicion "
                "WHERE c.Sustrato = :sus AND c.Certificacion = :cert)"
            )
            filtro_conteo += filtro_cond
            filtro_plantas += filtro_cond
            params_conteo["sus"] = sus
            params_conteo["cert"] = cert
            params_plantas["sus"] = sus
            params_plantas["cert"] = cert

    df_conteo = _ejecutar_query_df(
        f"""SELECT
            g.ID_Geografia AS id_geografia,
            g.ID_Fundo_Catalogo AS id_fundo,
            f.ID_Variedad AS id_variedad,
            f_cat.Fundo AS fundo,
            m.Modulo AS modulo,
            t.Turno AS turno,
            v_val.Valvula AS valvula,
            v.Nombre_Variedad AS variedad,
            ISNULL(cond_oa.Condicion, 'Sin condición') AS condicion,
            ISNULL(cond_oa.Certificacion, 'Sin certificación') AS certificacion,
            f.ID_Estado_Fenologico AS id_estado,
            SUM(f.Cantidad_Organos * 1.0) AS total_organos,
            COUNT(DISTINCT f.Punto) AS puntos
        FROM Silver.Fact_Conteo_Fenologico f WITH (NOLOCK)
        JOIN Silver.Dim_Tiempo dt_f ON f.ID_Tiempo = dt_f.ID_Tiempo
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON f.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Turno_Catalogo t WITH (NOLOCK) ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo v_val WITH (NOLOCK) ON g.ID_Valvula_Catalogo = v_val.ID_Valvula_Catalogo
        JOIN Silver.Dim_Fundo_Catalogo f_cat WITH (NOLOCK) ON g.ID_Fundo_Catalogo = f_cat.ID_Fundo_Catalogo
        OUTER APPLY (
            SELECT TOP 1
                cc.Sustrato + ' - ' + cc.Certificacion AS Condicion,
                cc.Certificacion                       AS Certificacion
            FROM Silver.Fact_Cosecha_SAP cs WITH (NOLOCK)
            JOIN Silver.Dim_Condicion_Cultivo cc WITH (NOLOCK)
                ON cs.ID_Condicion_Cultivo = cc.ID_Condicion
            WHERE cs.ID_Geografia = g.ID_Geografia
              AND cs.ID_Variedad = v.ID_Variedad
            ORDER BY cs.ID_Tiempo DESC
        ) cond_oa
        WHERE dt_f.Anio = (SELECT Anio FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          AND dt_f.Semana_ISO = (SELECT Semana_ISO FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          {filtro_conteo}
        GROUP BY g.ID_Geografia, g.ID_Fundo_Catalogo, f.ID_Variedad, f_cat.Fundo, m.Modulo, t.Turno, v_val.Valvula, v.Nombre_Variedad,
                 cond_oa.Condicion, cond_oa.Certificacion, f.ID_Estado_Fenologico""",
        params=params_conteo,
    )

    df_plantas = _ejecutar_query_df(
        f"""SELECT
            g.ID_Geografia AS id_geografia,
            m.Modulo AS modulo,
            t.Turno AS turno,
            v_val.Valvula AS valvula,
            CAST(SUM(f.Cantidad) AS FLOAT) AS plantas_sampleadas,
            1.0 AS pct_productivas_s1
        FROM Silver.Fact_Censo_Plantas f WITH (NOLOCK)
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo v_val ON g.ID_Valvula_Catalogo = v_val.ID_Valvula_Catalogo
        JOIN Silver.Dim_Fundo_Catalogo f_cat ON g.ID_Fundo_Catalogo = f_cat.ID_Fundo_Catalogo
        WHERE 1=1 {filtro_plantas}
        GROUP BY g.ID_Geografia, m.Modulo, t.Turno, v_val.Valvula""",
        params=params_plantas,
    )

    df_sem_base = _ejecutar_query_df(
        "SELECT DATEPART(ISO_WEEK, Fecha) AS sem_base, YEAR(Fecha) AS anio_base "
        "FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t",
        params={"t": id_tiempo},
    )
    sem_base = int(df_sem_base.iloc[0]["sem_base"]) if not df_sem_base.empty else 1
    anio_base = int(df_sem_base.iloc[0]["anio_base"]) if not df_sem_base.empty else 2026

    max_sem_anio = 53 if dt.date(anio_base, 12, 28).isocalendar()[1] == 53 else 52
    sem_ini = sem_base + 1
    sem_fin = sem_base + 6

    if sem_fin <= max_sem_anio:
        filtro_sem = "DATEPART(ISO_WEEK, t.Fecha) BETWEEN :s1 AND :s2 AND YEAR(t.Fecha) = :y"
        params_p = {"s1": sem_ini, "s2": sem_fin, "y": anio_base}
    else:
        filtro_sem = (
            "(YEAR(t.Fecha) = :y AND DATEPART(ISO_WEEK, t.Fecha) >= :s1) "
            "OR (YEAR(t.Fecha) = :y2 AND DATEPART(ISO_WEEK, t.Fecha) <= :s2)"
        )
        params_p = {"s1": sem_ini, "s2": sem_fin % max_sem_anio, "y": anio_base, "y2": anio_base + 1}

    df_pesos = _ejecutar_query_df(
        f"""SELECT
            g.ID_Fundo_Catalogo AS id_fundo,
            m.Modulo AS modulo,
            v.Nombre_Variedad AS variedad,
            DATEPART(ISO_WEEK, t.Fecha) AS semana_iso,
            AVG(p.Peso_Promedio_Baya_g) / 1000.0 AS peso_baya_kg
        FROM Silver.Fact_Evaluacion_Pesos p WITH (NOLOCK)
        JOIN Silver.Dim_Tiempo t WITH (NOLOCK) ON p.ID_Tiempo = t.ID_Tiempo
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON p.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON p.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        WHERE {filtro_sem}
        GROUP BY g.ID_Fundo_Catalogo, m.Modulo, v.Nombre_Variedad, DATEPART(ISO_WEEK, t.Fecha)""",
        params=params_p,
    )

    if df_pesos.empty:
        if sem_fin <= 53:
            filtro_hist = "DATEPART(ISO_WEEK, t.Fecha) BETWEEN :s1 AND :s2"
            params_h = {"s1": sem_ini, "s2": sem_fin}
        else:
            filtro_hist = (
                "DATEPART(ISO_WEEK, t.Fecha) >= :s1 "
                "OR DATEPART(ISO_WEEK, t.Fecha) <= :s2"
            )
            params_h = {"s1": sem_ini, "s2": sem_fin % 53}

        df_pesos = _ejecutar_query_df(
            f"""SELECT
                g.ID_Fundo_Catalogo AS id_fundo,
                m.Modulo AS modulo,
                v.Nombre_Variedad AS variedad,
                DATEPART(ISO_WEEK, t.Fecha) AS semana_iso,
                AVG(p.Peso_Promedio_Baya_g) / 1000.0 AS peso_baya_kg
            FROM Silver.Fact_Evaluacion_Pesos p WITH (NOLOCK)
            JOIN Silver.Dim_Tiempo t WITH (NOLOCK) ON p.ID_Tiempo = t.ID_Tiempo
            JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON p.ID_Variedad = v.ID_Variedad
            JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON p.ID_Geografia = g.ID_Geografia
            JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
            WHERE {filtro_hist}
            GROUP BY g.ID_Fundo_Catalogo, m.Modulo, v.Nombre_Variedad, DATEPART(ISO_WEEK, t.Fecha)""",
            params=params_h,
        )

    return df_conteo, df_plantas, df_pesos

def extraer_proyeccion_anterior(
    id_tiempo_base: int,
    modulo: Optional[int] = None,
    variedad: Optional[str] = None,
    condicion: Optional[str] = None,
    fundo: Optional[str] = None,
) -> pd.DataFrame:
    fecha_base = dt.datetime.strptime(str(id_tiempo_base), "%Y%m%d")
    ids_semanas = [
        int((fecha_base + dt.timedelta(days=(i + 1) * 7)).strftime("%Y%m%d"))
        for i in range(6)
    ]
    placeholders = ",".join(str(x) for x in ids_semanas)

    try:
        where_extra = ""
        params = {}
        if modulo:
            where_extra += " AND ID_Geografia IN (SELECT ID_Geografia FROM Silver.Dim_Geografia g JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo WHERE m.Modulo = :mod)"
            params["mod"] = str(modulo)
        if variedad:
            where_extra += " AND ID_Variedad = (SELECT ID_Variedad FROM Silver.Dim_Variedad WHERE Nombre_Variedad = :var)"
            params["var"] = variedad
        if fundo:
            where_extra += (
                " AND ID_Geografia IN ("
                "SELECT g2.ID_Geografia FROM Silver.Dim_Geografia g2 "
                "JOIN Silver.Dim_Fundo_Catalogo fc2 ON g2.ID_Fundo_Catalogo = fc2.ID_Fundo_Catalogo "
                "WHERE fc2.Fundo = :fnd)"
            )
            params["fnd"] = fundo
        if condicion:
            partes = condicion.split(" - ")
            if len(partes) == 2:
                sus, cert = partes[0], partes[1]
                where_extra += (
                    " AND ID_Geografia IN ("
                    "SELECT cs.ID_Geografia FROM Silver.Fact_Cosecha_SAP cs "
                    "JOIN Silver.Dim_Condicion_Cultivo c ON cs.ID_Condicion_Cultivo = c.ID_Condicion "
                    "WHERE c.Sustrato = :sus AND c.Certificacion = :cert)"
                )
                params["sus"] = sus
                params["cert"] = cert

        sql = f"SELECT ID_Tiempo, SUM(Kg_Proyectados) AS kg_anterior FROM Silver.Fact_Proyecciones WITH (NOLOCK) WHERE ID_Tiempo IN ({placeholders}) AND ID_Escenario = 4 {where_extra} GROUP BY ID_Tiempo"
        df = _ejecutar_query_df(sql, params)
        if df.empty:
            return pd.DataFrame(columns=["semana", "semana_label", "fecha_semana", "kg_anterior"])

        rows = []
        for i, id_t in enumerate(ids_semanas):
            fecha_sem = fecha_base + dt.timedelta(weeks=i + 1)
            kg = df.loc[df["ID_Tiempo"] == id_t, "kg_anterior"].sum() if id_t in df["ID_Tiempo"].values else 0.0
            rows.append({
                "semana": i + 1,
                "semana_label": f"W{i+1} ({fecha_sem.strftime('%d/%m')})",
                "fecha_semana": fecha_sem.date(),
                "kg_anterior": float(kg),
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["semana", "semana_label", "fecha_semana", "kg_anterior"])

def _ejecutar_comando(sql: str, params: Dict[str, Any] = None) -> None:
    try:
        with obtener_engine().begin() as con:
            con.execute(text(sql), params)
    except SQLAlchemyError as e:
        log.exception(f"Error ejecutando comando: {str(e)}")
        raise ErrorBaseDatos()

def guardar_proyeccion(
    df_detalle: pd.DataFrame,
    id_tiempo_base: int,
    margen_pesimista: float,
    margen_optimista: float,
) -> Dict[str, Any]:
    if df_detalle.empty:
        return {"insertados": 0, "saltados": 0, "errores": ["DataFrame vacío"]}

    # Los IDs de origen se conservan; nunca resolver con TOP 1 por etiquetas.
    requeridas = {"id_geografia", "id_variedad"}
    if not requeridas.issubset(df_detalle.columns) or df_detalle[list(requeridas)].isna().any().any():
        raise ValueError("El detalle de proyeccion requiere IDs de geografia y variedad de origen.")
    cache_tiempo = {}

    def id_tiempo_para_fecha(f):
        df = _ejecutar_query_df("SELECT TOP 1 ID_Tiempo FROM Silver.Dim_Tiempo WHERE Fecha = :f", {"f": f})
        return int(df.iloc[0]["ID_Tiempo"]) if not df.empty else None

    insertados = 0
    saltados = 0
    errores = []
    fecha_sistema = dt.datetime.now()
    fecha_cutoff = dt.datetime.strptime(str(id_tiempo_base), "%Y%m%d").date()

    for _, row in df_detalle.iterrows():
        id_geo = int(row["id_geografia"])
        id_var = int(row["id_variedad"])
        clave_geo = id_geo
        var_nombre = str(row["variedad"])

        fecha_sem = row["fecha_semana"]
        if hasattr(fecha_sem, "date"):
            fecha_sem = fecha_sem.date()
        if fecha_sem not in cache_tiempo:
            cache_tiempo[fecha_sem] = id_tiempo_para_fecha(fecha_sem)
        id_tiempo_sem = cache_tiempo[fecha_sem]

        if id_geo is None or id_var is None or id_tiempo_sem is None:
            saltados += 1
            continue

        try:
            _ejecutar_comando(
                """
                MERGE Silver.Fact_Proyecciones AS dest
                USING (SELECT :id_t AS ID_Tiempo, :id_g AS ID_Geografia, :id_v AS ID_Variedad, :id_e AS ID_Escenario) AS src
                  ON dest.ID_Tiempo = src.ID_Tiempo AND dest.ID_Geografia = src.ID_Geografia
                 AND dest.ID_Variedad = src.ID_Variedad AND dest.ID_Escenario = src.ID_Escenario
                WHEN MATCHED THEN UPDATE SET
                    Kg_Proyectados = :kgb, Kg_Pesimista = :kgp, Kg_Optimista = :kgo,
                    Fecha_Cutoff = :fc, Fecha_Evento = :fe, Fecha_Sistema = :fs,
                    Version_Modelo = :ver, Estado_DQ = 'OK'
                WHEN NOT MATCHED THEN INSERT (
                    ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario, ID_Estado_Workflow,
                    Kg_Proyectados, Kg_Pesimista, Kg_Optimista, Fecha_Cutoff, Fecha_Evento, Fecha_Sistema,
                    Version_Modelo, Flag_Override, Estado_DQ
                ) VALUES (
                    :id_t, :id_g, :id_v, :id_e, :id_wf, :kgb, :kgp, :kgo, :fc, :fe, :fs, :ver, 0, 'OK'
                );
                """,
                {
                    "id_t": id_tiempo_sem, "id_g": id_geo, "id_v": id_var, "id_e": 4, "id_wf": 1,
                    "kgb": float(row["kg_base"]), "kgp": float(row["kg_pesimista"]), "kgo": float(row["kg_optimista"]),
                    "fc": fecha_cutoff, "fe": fecha_sem, "fs": fecha_sistema, "ver": "sixweek-manual-ui-v1",
                }
            )
            insertados += 1
        except Exception as exc:
            errores.append(f"Mod={clave_geo} Var={var_nombre} Sem={fecha_sem}: {exc}")
            saltados += 1

    return {"insertados": insertados, "saltados": saltados, "errores": errores}

def guardar_param_json(clave: str, payload_dict: dict, descripcion: str, modulo: str = "sixweek") -> bool:
    try:
        _ejecutar_comando(
            """
            MERGE Config.Parametros_Pipeline AS dest
            USING (SELECT :clave AS Nombre_Parametro) AS src
              ON dest.Nombre_Parametro = src.Nombre_Parametro
            WHEN MATCHED THEN UPDATE
                SET Valor = :valor, Descripcion = :desc, Modulo = :mod, Tipo_Dato = :tipo
            WHEN NOT MATCHED THEN
                INSERT (Nombre_Parametro, Valor, Descripcion, Modulo, Tipo_Dato)
                VALUES (:clave, :valor, :desc, :mod, :tipo);
            """,
            {
                "clave": clave,
                "valor": json.dumps(payload_dict, ensure_ascii=False),
                "desc": descripcion,
                "mod": modulo,
                "tipo": "JSON",
            },
        )
        return True
    except Exception:
        return False

def leer_param_json(clave: str) -> Optional[dict]:
    df = _ejecutar_query_df("SELECT Valor FROM Config.Parametros_Pipeline WHERE Nombre_Parametro = :c", {"c": clave})
    if df.empty or not df.iloc[0]["Valor"]:
        return None
    return json.loads(df.iloc[0]["Valor"])
