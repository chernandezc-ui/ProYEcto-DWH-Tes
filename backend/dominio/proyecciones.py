"""Validación y cálculo de proyecciones sobre snapshots en memoria."""

from __future__ import annotations

from collections.abc import Mapping
import datetime as dt
import math

import pandas as pd


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
    "cosechable": {1: 1.0, 2: None},
    "maduras": {1: 1.0, 2: None},
    "cremas": {1: 1.0, 2: None},
    "fase_2": {1: 0.14, 2: 0.40, 3: None},
    "fase_1": {1: 0.0, 2: 0.0, 3: 0.10, 4: 0.60, 5: None, 6: None},
    "verdes": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.16, 6: 0.17},
    "pequena": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0},
}
ID_ESTADO_MAP = {
    9: "cosechable", 8: "maduras", 7: "cremas", 6: "fase_2",
    5: "fase_1", 4: "verdes", 3: "pequena",
}
PLANTAS_POR_PUNTO = 10
_TOLERANCIA_SUMA = 1e-6


class ErrorValidacionProyeccion(ValueError):
    """Parámetros de un escenario de proyección inválidos."""


def _numero_finito(valor: object, nombre: str) -> float:
    if isinstance(valor, bool):
        raise ErrorValidacionProyeccion(f"{nombre}: debe ser un número finito.")
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ErrorValidacionProyeccion(
            f"{nombre}: debe ser un número finito."
        ) from exc
    if not math.isfinite(numero):
        raise ErrorValidacionProyeccion(f"{nombre}: debe ser un número finito.")
    return numero


def _porcentaje(valor: object, semana: int) -> float:
    numero = _numero_finito(valor, f"W{semana}")
    if not 0.0 <= numero <= 1.0:
        raise ErrorValidacionProyeccion(
            f"W{semana}: fuera del rango [0, 1]."
        )
    return numero


def _semanas_en_anio(anio: int) -> int:
    return dt.date(anio, 12, 28).isocalendar()[1]


def cerrar_matriz(
    inputs: dict[str, dict[int, float | None]],
) -> dict[str, list[float]]:
    """Conserva el cierre residual secuencial de las semanas sin porcentaje."""
    matriz_cerrada = {}
    for estado, semanas in inputs.items():
        valores = {
            w: None if semanas.get(w) is None else float(semanas[w])
            for w in range(1, 7)
        }
        for w in range(1, 7):
            if valores[w] is None:
                suma_anteriores = sum(
                    valores[s] for s in range(1, w) if valores[s] is not None
                )
                valores[w] = max(0.0, round(1.0 - suma_anteriores, 10))
        matriz_cerrada[estado] = [float(valores[w]) for w in range(1, 7)]
    return matriz_cerrada


def validar_matriz_inputs(
    inputs: dict[str, dict[int, float | None]],
) -> dict[str, dict]:
    """Devuelve el informe por estado usado por consumidores existentes."""
    reporte = {}
    for estado, semanas in inputs.items():
        valores = []
        tiene_nones = False
        errores = []
        advertencias = []
        for w in range(1, 7):
            valor = semanas.get(w)
            if valor is None:
                tiene_nones = True
                continue
            try:
                valores.append(_porcentaje(valor, w))
            except ErrorValidacionProyeccion as exc:
                errores.append(str(exc))
        suma = math.fsum(valores)
        if suma > 1.0 + _TOLERANCIA_SUMA:
            errores.append(
                f"Suma de inputs = {suma:.3f} > 1.00 (excede el 100%)."
            )
        if not errores:
            cierre = cerrar_matriz({estado: semanas})[estado]
            # Conserva la tolerancia del validador anterior también al cierre.
            if math.fsum(cierre) > 1.0 + _TOLERANCIA_SUMA:
                errores.append("El cierre residual excede el 100%.")
        if not tiene_nones and suma < 1.0 - _TOLERANCIA_SUMA:
            advertencias.append(
                f"Suma = {suma:.3f} < 1.00 — queda fuera del corte W1-W6."
            )
        reporte[estado] = {
            "suma": round(suma, 6),
            "tiene_nones": tiene_nones,
            "errores": errores,
            "advertencias": advertencias,
        }
    return reporte


def normalizar_matriz_inputs(inputs: object) -> dict[str, dict[int, float | None]]:
    """Normaliza claves JSON y valida sin completar porcentajes residuales."""
    if not isinstance(inputs, Mapping) or not inputs:
        raise ErrorValidacionProyeccion("La matriz debe contener al menos un estado.")
    normalizada = {}
    for estado, semanas in inputs.items():
        if estado not in MATRIZ_INPUTS_DEFAULT:
            raise ErrorValidacionProyeccion("La matriz contiene un estado desconocido.")
        if not isinstance(semanas, Mapping):
            raise ErrorValidacionProyeccion("Las semanas de cada estado deben ser un objeto.")
        valores = {}
        for clave, valor in semanas.items():
            if type(clave) is int and 1 <= clave <= 6:
                semana = clave
            elif isinstance(clave, str) and clave in {"1", "2", "3", "4", "5", "6"}:
                semana = int(clave)
            else:
                raise ErrorValidacionProyeccion("Las semanas deben estar entre 1 y 6.")
            if semana in valores:
                raise ErrorValidacionProyeccion("La matriz contiene una semana repetida.")
            valores[semana] = None if valor is None else _porcentaje(valor, semana)
        normalizada[estado] = {w: valores.get(w) for w in range(1, 7)}
    for estado, resultado in validar_matriz_inputs(normalizada).items():
        if resultado["errores"]:
            raise ErrorValidacionProyeccion(
                f"{estado}: {' '.join(resultado['errores'])}"
            )
    return normalizada


def preparar_parametros(
    id_tiempo: int,
    matriz_inputs: dict[str, dict[int, float | None]] | None = None,
    margen_pesimista: float = 0.9906,
    margen_optimista: float = 1.0107,
) -> tuple[dt.datetime, dict[str, dict[int, float | None]]]:
    """Valida los parámetros antes de leer fuentes o efectuar el cálculo."""
    if isinstance(id_tiempo, bool) or not isinstance(id_tiempo, (int, str)):
        raise ErrorValidacionProyeccion("id_tiempo debe ser una fecha YYYYMMDD válida.")
    texto_fecha = str(id_tiempo)
    if len(texto_fecha) != 8 or not texto_fecha.isascii() or not texto_fecha.isdigit():
        raise ErrorValidacionProyeccion("id_tiempo debe ser una fecha YYYYMMDD válida.")
    try:
        fecha_base = dt.datetime.strptime(texto_fecha, "%Y%m%d")
    except ValueError as exc:
        raise ErrorValidacionProyeccion(
            "id_tiempo debe ser una fecha YYYYMMDD válida."
        ) from exc
    pesimista = _numero_finito(margen_pesimista, "margen_pesimista")
    optimista = _numero_finito(margen_optimista, "margen_optimista")
    if pesimista < 0 or optimista < 0:
        raise ErrorValidacionProyeccion("Los márgenes deben ser no negativos.")
    if pesimista > optimista:
        raise ErrorValidacionProyeccion(
            "El margen pesimista no puede superar al optimista."
        )
    matriz = MATRIZ_INPUTS_DEFAULT if matriz_inputs is None else matriz_inputs
    return fecha_base, normalizar_matriz_inputs(matriz)


def lookup_peso_baya(
    modulo: int, variedad: str, df_pesos: pd.DataFrame,
    sem_base: int, anio_base: int, id_fundo: int,
) -> dict[int, float]:
    PESO_FALLBACK_KG = 0.00289
    df_pesos = df_pesos[df_pesos["id_fundo"] == id_fundo]
    max_sem = _semanas_en_anio(anio_base)
    subset_mv = df_pesos[
        (df_pesos["modulo"] == modulo) & (df_pesos["variedad"] == variedad)
    ]
    subset_v = df_pesos[df_pesos["variedad"] == variedad]
    pesos = {}
    for w in range(1, 7):
        target_sem = sem_base + w
        if target_sem > max_sem:
            target_sem -= max_sem
        val = subset_mv[subset_mv["semana_iso"] == target_sem]["peso_baya_kg"].mean()
        if pd.isna(val) or val == 0:
            val = subset_v[subset_v["semana_iso"] == target_sem]["peso_baya_kg"].mean()
        if pd.isna(val) or val == 0:
            recientes = subset_mv[subset_mv["semana_iso"] <= sem_base]
            if not recientes.empty:
                val = recientes.sort_values("semana_iso", ascending=False).iloc[0]["peso_baya_kg"]
        if pd.isna(val) or val == 0:
            val = subset_v["peso_baya_kg"].mean()
        pesos[w] = PESO_FALLBACK_KG if pd.isna(val) or val == 0 else float(val)
    return pesos


def calcular_pct_productivas(s1: float) -> list[float]:
    res = [0.0] * 6
    curr = s1 if pd.notna(s1) else 0.0
    for w in range(1, 7):
        delta = DELTA_PRODUCTIVAS.get(w, 0.0)
        curr = min(1.0, max(0.0, curr + delta))
        res[w - 1] = curr
    return res


def kg_unidad_semana(
    conteo_estados: dict[int, float], matriz_cerrada: dict[str, list[float]],
    plantas: float, pesos_w: dict[int, float], pct_prod_w: list[float],
) -> list[float]:
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


def calcular_proyeccion(
    df_conteo: pd.DataFrame,
    df_plantas: pd.DataFrame,
    df_pesos: pd.DataFrame,
    id_tiempo: int,
    matriz_inputs: dict[str, dict[int, float | None]] | None = None,
    margen_pesimista: float = 0.9906,
    margen_optimista: float = 1.0107,
) -> dict:
    """Calcula las seis semanas sin leer ni persistir datos externos."""
    fecha_base, matriz_inputs = preparar_parametros(
        id_tiempo, matriz_inputs, margen_pesimista, margen_optimista
    )
    margen_pesimista = float(margen_pesimista)
    margen_optimista = float(margen_optimista)
    if df_conteo.empty:
        return {"df_semanal": pd.DataFrame(), "df_detalle": pd.DataFrame(), "kpis": {}}

    matriz_cerrada = cerrar_matriz(matriz_inputs)
    sem_base = fecha_base.isocalendar()[1]
    anio_base = fecha_base.year
    unidades = df_conteo.groupby(["id_geografia", "id_variedad"], dropna=False)
    filas_detalle = []
    total_plantas_proy = 0
    unidades_con_datos = 0

    for (id_geo, id_var), group in unidades:
        if pd.isna(id_geo) or pd.isna(id_var):
            raise ValueError("Conteo sin identidad dimensional de origen.")
        mod, tur, valv, var = (
            group[c].iloc[0] for c in ("modulo", "turno", "valvula", "variedad")
        )
        id_fundo = int(group["id_fundo"].iloc[0])
        fundo_unidad = str(group["fundo"].iloc[0]) if "fundo" in group.columns else "—"
        condicion_unidad = str(group["condicion"].iloc[0]) if "condicion" in group.columns else "Sin condición"
        certificacion_unidad = str(group["certificacion"].iloc[0]) if "certificacion" in group.columns else "Sin certificación"
        puntos_val = group["puntos"].max()
        if puntos_val == 0:
            puntos_val = 1

        conteo_estados = {}
        for _, row in group.iterrows():
            conteo_estados[row["id_estado"]] = (
                conteo_estados.get(row["id_estado"], 0.0)
                + row["total_organos"] / (puntos_val * PLANTAS_POR_PUNTO)
            )

        p_row = df_plantas[df_plantas["id_geografia"] == id_geo]
        if p_row.empty:
            num_plantas_total = 1500.0
            pct_prod_s1 = 0.80
        else:
            val_p = p_row.iloc[0].get(
                "plantas_sampleadas", p_row.iloc[0].get("Plantas_Productivas", 1500.0)
            )
            num_plantas_total = float(val_p) if pd.notna(val_p) and val_p > 0 else 1500.0
            val_pct = p_row.iloc[0].get("pct_productivas_s1", 0.0)
            pct_prod_s1 = float(val_pct) if pd.notna(val_pct) else 0.0
            unidades_con_datos += 1

        total_plantas_proy += num_plantas_total
        pesos_w = lookup_peso_baya(mod, var, df_pesos, sem_base, anio_base, id_fundo)
        prod_w = calcular_pct_productivas(pct_prod_s1)
        kg_semanas = kg_unidad_semana(
            conteo_estados, matriz_cerrada, num_plantas_total, pesos_w, prod_w
        )
        for i, kg in enumerate(kg_semanas):
            w_num = i + 1
            fecha_sem = fecha_base + dt.timedelta(days=w_num * 7)
            filas_detalle.append({
                "id_geografia": int(id_geo), "id_variedad": int(id_var), "id_fundo": id_fundo,
                "fundo": fundo_unidad, "condicion": condicion_unidad,
                "certificacion": certificacion_unidad, "modulo": mod, "turno": tur,
                "valvula": valv, "variedad": var, "semana": w_num,
                "id_tiempo_proy": int(fecha_sem.strftime("%Y%m%d")),
                "semana_label": f"W{w_num} ({fecha_sem.strftime('%d/%m')})",
                "fecha_semana": fecha_sem.date(), "kg_base": round(kg, 2),
                "kg_pesimista": round(kg * margen_pesimista, 2),
                "kg_optimista": round(kg * margen_optimista, 2),
            })

    df_detalle = pd.DataFrame(filas_detalle)
    if df_detalle.empty:
        return {"df_semanal": pd.DataFrame(), "df_detalle": pd.DataFrame(), "kpis": {}}
    df_semanal = (
        df_detalle.groupby(["semana", "semana_label", "fecha_semana"])
        .agg(
            kg_base=("kg_base", "sum"), kg_pesimista=("kg_pesimista", "sum"),
            kg_optimista=("kg_optimista", "sum"),
        )
        .reset_index()
        .sort_values("semana")
    )
    total_base = df_semanal["kg_base"].sum()
    total_opt = df_semanal["kg_optimista"].sum()
    total_pes = df_semanal["kg_pesimista"].sum()
    try:
        variedad_top = (
            df_detalle.groupby("variedad")["kg_base"].sum().idxmax()
            if total_base > 0 else "—"
        )
    except (ValueError, KeyError):
        variedad_top = "—"
    return {
        "df_semanal": df_semanal,
        "df_detalle": df_detalle,
        "kpis": {
            "total_base": total_base, "total_opt": total_opt, "total_pes": total_pes,
            "variedad_top": variedad_top, "total_plantas": total_plantas_proy,
            "kg_por_planta": total_base / total_plantas_proy if total_plantas_proy > 0 else 0,
            "unidades_cubiertas": unidades_con_datos, "unidades_totales": len(unidades),
        },
    }
