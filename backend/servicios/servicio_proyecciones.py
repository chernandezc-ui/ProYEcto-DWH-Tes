from __future__ import annotations
import datetime as dt
import pandas as pd
from typing import Dict, Any, List, Optional
import asyncio

import repositorios.repo_proyecciones as repo
from nucleo.cache import cache
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

ESTADOS_POR_SEMANA = {
    1: ["cosechable", "maduras", "cremas", "fase_2", "fase_1"],
    2: ["cremas", "fase_2", "fase_1", "maduras", "cosechable"],
    3: ["fase_1", "verdes", "fase_2"],
    4: ["verdes", "pequena", "fase_1", "fase_2"],
    5: ["verdes", "pequena", "fase_1"],
    6: ["verdes", "pequena", "fase_1"],
}
DECAY_FACTOR = {1: 1.0, 2: 1.0, 3: 0.8, 4: 0.8, 5: 0.8, 6: 0.8}
DELTA_PRODUCTIVAS = {1: 0.0, 2: +0.02, 3: 0.0, 4: -0.03, 5: +0.01, 6: +0.01}
MATRIZ_INPUTS_DEFAULT = {
    "cosechable":  {1: 1.0, 2: None},
    "maduras":     {1: 1.0, 2: None},
    "cremas":      {1: 1.0, 2: None},
    "fase_2":      {1: 0.14, 2: 0.40, 3: None},
    "fase_1":      {1: 0.0, 2: 0.0, 3: 0.10, 4: 0.60, 5: None, 6: None},
    "verdes":      {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.16, 6: 0.17},
    "pequena":     {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0},
}
ID_ESTADO_MAP = {9: "cosechable", 8: "maduras", 7: "cremas", 6: "fase_2", 5: "fase_1", 4: "verdes", 3: "pequena"}
PLANTAS_POR_PUNTO = 10

def _semanas_en_anio(anio: int) -> int:
    return dt.date(anio, 12, 28).isocalendar()[1]

def validar_matriz_inputs(inputs: dict[str, dict[int, float | None]]) -> dict[str, dict]:
    reporte = {}
    for estado, semanas in inputs.items():
        suma = 0.0
        tiene_nones = False
        errores = []
        advertencias = []
        for w in range(1, 7):
            val = semanas.get(w)
            if val is None:
                tiene_nones = True
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                errores.append(f"W{w}: valor no numérico ({val!r}).")
                continue
            if fval < 0 or fval > 1:
                errores.append(f"W{w}: {fval:.3f} fuera del rango [0, 1].")
                continue
            suma += fval
        if suma > 1.0 + 1e-6:
            errores.append(f"Suma de inputs = {suma:.3f} > 1.00 (excede el 100%).")
        if (not tiene_nones) and suma < 1.0 - 1e-6:
            advertencias.append(f"Suma = {suma:.3f} < 1.00 — queda fuera del corte W1-W6.")
        reporte[estado] = {"suma": round(suma, 6), "tiene_nones": tiene_nones, "errores": errores, "advertencias": advertencias}
    return reporte

def cerrar_matriz(inputs: dict[str, dict[int, float | None]]) -> dict[str, list[float]]:
    matriz_cerrada = {}
    for estado, semanas in inputs.items():
        valores = {}
        for w in range(1, 7):
            val = semanas.get(w)
            valores[w] = None if val is None else float(val)
        for w in range(1, 7):
            if valores[w] is None:
                suma_anteriores = sum(valores[s] for s in range(1, w) if valores[s] is not None)
                valores[w] = max(0.0, round(1.0 - suma_anteriores, 10))
        matriz_cerrada[estado] = [float(valores[w]) for w in range(1, 7)]
    return matriz_cerrada

def lookup_peso_baya(modulo: int, variedad: str, df_pesos: pd.DataFrame, sem_base: int, anio_base: int, id_fundo: int) -> dict[int, float]:
    PESO_FALLBACK_KG = 0.00289
    df_pesos = df_pesos[df_pesos["id_fundo"] == id_fundo]
    max_sem = _semanas_en_anio(anio_base)
    subset_mv = df_pesos[(df_pesos["modulo"] == modulo) & (df_pesos["variedad"] == variedad)]
    subset_v  = df_pesos[df_pesos["variedad"] == variedad]
    pesos = {}
    for w in range(1, 7):
        target_sem = sem_base + w
        if target_sem > max_sem: target_sem -= max_sem
        val = subset_mv[subset_mv["semana_iso"] == target_sem]["peso_baya_kg"].mean()
        if pd.isna(val) or val == 0:
            val = subset_v[subset_v["semana_iso"] == target_sem]["peso_baya_kg"].mean()
        if pd.isna(val) or val == 0:
            recientes = subset_mv[subset_mv["semana_iso"] <= sem_base]
            if not recientes.empty:
                val = recientes.sort_values("semana_iso", ascending=False).iloc[0]["peso_baya_kg"]
        if pd.isna(val) or val == 0:
            val = subset_v["peso_baya_kg"].mean()
        pesos[w] = PESO_FALLBACK_KG if (pd.isna(val) or val == 0) else float(val)
    return pesos

def calcular_pct_productivas(s1: float) -> list[float]:
    res = [0.0] * 6
    curr = s1 if pd.notna(s1) else 0.0
    for w in range(1, 7):
        delta = DELTA_PRODUCTIVAS.get(w, 0.0)
        curr = min(1.0, max(0.0, curr + delta))
        res[w - 1] = curr
    return res

def kg_unidad_semana(conteo_estados: dict[int, float], matriz_cerrada: dict[str, list[float]], plantas: float, pesos_w: dict[int, float], pct_prod_w: list[float]) -> list[float]:
    kg_semanas = [0.0] * 6
    for w_idx in range(6):
        w_num = w_idx + 1
        sum_estados = 0.0
        for id_est, cant in conteo_estados.items():
            estado_nom = ID_ESTADO_MAP.get(id_est)
            if estado_nom and estado_nom in matriz_cerrada:
                pct_mad = matriz_cerrada[estado_nom][w_idx]
                sum_estados += cant * pct_mad * plantas * pesos_w[w_num] * pct_prod_w[w_idx]
        kg_semanas[w_idx] = sum_estados * DECAY_FACTOR[w_num]
    return kg_semanas

async def ejecutar_proyeccion(
    id_tiempo: int,
    matriz_inputs: dict[str, dict[int, float | None]] = None,
    margen_pesimista: float = 0.9906,
    margen_optimista: float = 1.0107,
    modulo: Optional[int] = None,
    variedad: Optional[str] = None,
    condicion: Optional[str] = None,
    fundo: Optional[str] = None,
) -> dict:
    if matriz_inputs is None:
        matriz_inputs = MATRIZ_INPUTS_DEFAULT
        
    df_conteo, df_plantas, df_pesos = await asyncio.to_thread(
        repo.extraer_datos_granulares, id_tiempo, modulo, variedad, condicion, fundo
    )
    
    if df_conteo.empty:
        return {"df_semanal": pd.DataFrame(), "df_detalle": pd.DataFrame(), "kpis": {}}
        
    matriz_cerrada = cerrar_matriz(matriz_inputs)
    fecha_base = dt.datetime.strptime(str(id_tiempo), "%Y%m%d")
    sem_base = fecha_base.isocalendar()[1]
    anio_base = fecha_base.year
    
    unidades = df_conteo.groupby(["id_geografia", "id_variedad"], dropna=False)
    filas_detalle = []
    total_plantas_proy = 0
    unidades_con_datos = 0
    
    for (id_geo, id_var), group in unidades:
        if pd.isna(id_geo) or pd.isna(id_var):
            raise ValueError("Conteo sin identidad dimensional de origen.")
        mod, tur, valv, var = (group[c].iloc[0] for c in ("modulo", "turno", "valvula", "variedad"))
        id_fundo = int(group["id_fundo"].iloc[0])
        fundo_unidad = str(group["fundo"].iloc[0]) if "fundo" in group.columns else "—"
        condicion_unidad = str(group["condicion"].iloc[0]) if "condicion" in group.columns else "Sin condición"
        certificacion_unidad = str(group["certificacion"].iloc[0]) if "certificacion" in group.columns else "Sin certificación"
        puntos_val = group["puntos"].max()
        if puntos_val == 0: puntos_val = 1
        
        conteo_estados = {}
        for _, row in group.iterrows():
            conteo_estados[row["id_estado"]] = conteo_estados.get(row["id_estado"], 0.0) + row["total_organos"] / (puntos_val * PLANTAS_POR_PUNTO)
            
        p_row = df_plantas[df_plantas["id_geografia"] == id_geo]
        if p_row.empty:
            num_plantas_total = 1500.0
            pct_prod_s1 = 0.80
        else:
            val_p = p_row.iloc[0].get("plantas_sampleadas", p_row.iloc[0].get("Plantas_Productivas", 1500.0))
            num_plantas_total = float(val_p) if pd.notna(val_p) and val_p > 0 else 1500.0
            val_pct = p_row.iloc[0].get("pct_productivas_s1", 0.0)
            pct_prod_s1 = float(val_pct) if pd.notna(val_pct) else 0.0
            unidades_con_datos += 1
            
        total_plantas_proy += num_plantas_total
        pesos_w = lookup_peso_baya(mod, var, df_pesos, sem_base, anio_base, id_fundo)
        prod_w = calcular_pct_productivas(pct_prod_s1)
        kg_semanas = kg_unidad_semana(conteo_estados, matriz_cerrada, num_plantas_total, pesos_w, prod_w)
        
        for i, kg in enumerate(kg_semanas):
            w_num = i + 1
            fecha_sem = fecha_base + dt.timedelta(days=w_num * 7)
            id_t_sem = int(fecha_sem.strftime("%Y%m%d"))
            filas_detalle.append({
                "id_geografia": int(id_geo), "id_variedad": int(id_var), "id_fundo": id_fundo,
                "fundo": fundo_unidad, "condicion": condicion_unidad, "certificacion": certificacion_unidad,
                "modulo": mod, "turno": tur, "valvula": valv, "variedad": var, "semana": w_num,
                "id_tiempo_proy": id_t_sem, "semana_label": f"W{w_num} ({fecha_sem.strftime('%d/%m')})",
                "fecha_semana": fecha_sem.date(), "kg_base": round(kg, 2), "kg_pesimista": round(kg * margen_pesimista, 2), "kg_optimista": round(kg * margen_optimista, 2),
            })
            
    df_detalle = pd.DataFrame(filas_detalle)
    if df_detalle.empty: return {"df_semanal": pd.DataFrame(), "df_detalle": pd.DataFrame(), "kpis": {}}
    
    df_semanal = df_detalle.groupby(["semana", "semana_label", "fecha_semana"]).agg(kg_base=("kg_base", "sum"), kg_pesimista=("kg_pesimista", "sum"), kg_optimista=("kg_optimista", "sum")).reset_index().sort_values("semana")
    total_base = df_semanal["kg_base"].sum()
    total_opt = df_semanal["kg_optimista"].sum()
    total_pes = df_semanal["kg_pesimista"].sum()
    try: variedad_top = df_detalle.groupby("variedad")["kg_base"].sum().idxmax() if total_base > 0 else "—"
    except (ValueError, KeyError): variedad_top = "—"
    
    # Save the projection async if wanted, or we do it immediately. We'll do it immediately via repo.
    await asyncio.to_thread(repo.guardar_proyeccion, df_detalle, id_tiempo, margen_pesimista, margen_optimista)
    
    return {
        "df_semanal": df_semanal,
        "df_detalle": df_detalle,
        "kpis": {
            "total_base": total_base, "total_opt": total_opt, "total_pes": total_pes,
            "variedad_top": variedad_top, "total_plantas": total_plantas_proy,
            "kg_por_planta": total_base / total_plantas_proy if total_plantas_proy > 0 else 0,
            "unidades_cubiertas": unidades_con_datos, "unidades_totales": len(unidades)
        },
    }

async def obtener_fechas_disponibles() -> list[int]:
    return await asyncio.to_thread(repo.obtener_fechas_disponibles)
