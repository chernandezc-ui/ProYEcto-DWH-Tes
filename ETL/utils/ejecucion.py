"""
ejecucion.py
============
Contrato de ejecución del pipeline ETL.

Define:
- facts disponibles para reproceso dirigido
- dependencias operativas por fact
- marts Gold impactados por cada fact
"""

from __future__ import annotations

from collections import OrderedDict


MODO_EJECUCION_COMPLETO = "completo"
MODO_EJECUCION_FACTS = "facts"

DEPENDENCIA_DIM_PERSONAL = "Dim_Personal"
DEPENDENCIA_DIM_GEOGRAFIA = "Dim_Geografia"
DEPENDENCIA_SP_CAMA_SYNC = "SP_CAMA_SYNC"
DEPENDENCIA_SP_CAMA_VALIDACION = "SP_CAMA_VALIDACION"

ORDEN_DEPENDENCIAS = (
    DEPENDENCIA_DIM_PERSONAL,
    DEPENDENCIA_DIM_GEOGRAFIA,
    DEPENDENCIA_SP_CAMA_SYNC,
    DEPENDENCIA_SP_CAMA_VALIDACION,
)


CONFIG_FACTS = OrderedDict({
    "Fact_Ciclo_Poda": {
        "orden": 9,
        "tabla_destino": "Silver.Fact_Ciclo_Poda",
        "fuentes_bronce": ("Bronce.Evaluacion_Calidad_Poda", "Bronce.Ciclos_Fenologicos"),
        "dependencias": (DEPENDENCIA_DIM_GEOGRAFIA,),
        "marts": ("Gold.Mart_Ciclo_Poda",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Cosecha_SAP": {
        "orden": 10,
        "tabla_destino": "Silver.Fact_Cosecha_SAP",
        "fuentes_bronce": ("Bronce.Reporte_Cosecha", "Bronce.Data_SAP"),
        "dependencias": (DEPENDENCIA_DIM_GEOGRAFIA,),
        "marts": ("Gold.Mart_Cosecha",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Conteo_Fenologico": {
        "orden": 11,
        "tabla_destino": "Silver.Fact_Conteo_Fenologico",
        "fuentes_bronce": ("Bronce.Conteo_Fruta",),
        "dependencias": (DEPENDENCIA_DIM_PERSONAL, DEPENDENCIA_DIM_GEOGRAFIA),
        "marts": ("Gold.Mart_Fenologia",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Ciclos_Fenologicos": {
        "orden": 12,
        "tabla_destino": "Silver.Fact_Ciclos_Fenologicos",
        "fuentes_bronce": ("Bronce.Ciclos_Fenologicos",),
        "dependencias": (DEPENDENCIA_DIM_PERSONAL, DEPENDENCIA_DIM_GEOGRAFIA),
        "marts": (),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_total_fact",
    },
    "Fact_Peladas": {
        "orden": 13,
        "tabla_destino": "Silver.Fact_Peladas",
        "fuentes_bronce": ("Bronce.Peladas",),
        "dependencias": (DEPENDENCIA_DIM_PERSONAL, DEPENDENCIA_DIM_GEOGRAFIA),
        "marts": (),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Telemetria_Clima": {
        "orden": 14,
        "tabla_destino": "Silver.Fact_Telemetria_Clima",
        "fuentes_bronce": ("Bronce.Telemetria_Clima",),
        "dependencias": (),
        "marts": ("Gold.Mart_Clima",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Evaluacion_Pesos": {
        "orden": 15,
        "tabla_destino": "Silver.Fact_Evaluacion_Pesos",
        "fuentes_bronce": ("Bronce.Evaluacion_Pesos",),
        "dependencias": (
            DEPENDENCIA_DIM_PERSONAL,
            DEPENDENCIA_DIM_GEOGRAFIA,
            DEPENDENCIA_SP_CAMA_SYNC,
            DEPENDENCIA_SP_CAMA_VALIDACION,
        ),
        "marts": ("Gold.Mart_Pesos_Calibres",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Tareo": {
        "orden": 16,
        "tabla_destino": "Silver.Fact_Tareo",
        "fuentes_bronce": ("Bronce.Consolidado_Tareos",),
        "dependencias": (DEPENDENCIA_DIM_PERSONAL, DEPENDENCIA_DIM_GEOGRAFIA),
        "marts": ("Gold.Mart_Administrativo",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Fisiologia": {
        "orden": 17,
        "tabla_destino": "Silver.Fact_Fisiologia",
        "fuentes_bronce": ("Bronce.Fisiologia",),
        "dependencias": (DEPENDENCIA_DIM_GEOGRAFIA,),
        "marts": ("Gold.Mart_Fisiologia",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Floracion": {
        "orden": 18,
        "tabla_destino": "Silver.Fact_Floracion",
        "fuentes_bronce": ("Bronce.Floracion",),
        "dependencias": (
            DEPENDENCIA_DIM_PERSONAL,
            DEPENDENCIA_DIM_GEOGRAFIA,
            DEPENDENCIA_SP_CAMA_SYNC,
            DEPENDENCIA_SP_CAMA_VALIDACION,
        ),
        "marts": ("Gold.Mart_Evaluacion_Vegetativa",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Induccion_Floral": {
        "orden": 19,
        "tabla_destino": "Silver.Fact_Induccion_Floral",
        "fuentes_bronce": ("Bronce.Induccion_Floral",),
        "dependencias": (DEPENDENCIA_DIM_PERSONAL, DEPENDENCIA_DIM_GEOGRAFIA),
        "marts": ("Gold.Mart_Induccion_Floral",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Tasa_Crecimiento_Brotes": {
        "orden": 20,
        "tabla_destino": "Silver.Fact_Tasa_Crecimiento_Brotes",
        "fuentes_bronce": ("Bronce.Tasa_Crecimiento_Brotes",),
        "dependencias": (DEPENDENCIA_DIM_PERSONAL, DEPENDENCIA_DIM_GEOGRAFIA),
        "marts": ("Gold.Mart_Tasa_Crecimiento",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Censo_Plantas": {
        "orden": 21,
        "tabla_destino": "Silver.Fact_Censo_Plantas",
        "fuentes_bronce": ("Bronce.Censo_Plantas",),
        "dependencias": (DEPENDENCIA_DIM_GEOGRAFIA,),
        "marts": ("Gold.Mart_Censo_Plantas",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Evaluacion_Vegetativa": {
        "orden": 22,
        "tabla_destino": "Silver.Fact_Evaluacion_Vegetativa",
        "fuentes_bronce": ("Bronce.Evaluacion_Vegetativa",),
        "dependencias": (DEPENDENCIA_DIM_GEOGRAFIA,),
        "marts": ("Gold.Mart_Evaluacion_Vegetativa",),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
    "Fact_Areas_Plantas": {
        "orden": 23,
        "tabla_destino": "Silver.Fact_Areas_Plantas",
        "fuentes_bronce": ("Bronce.Base_Plantas_Area",),
        "dependencias": (DEPENDENCIA_DIM_GEOGRAFIA,),
        "marts": (),
        "releer_bronce_por_estado": True,
        "estrategia_rerun": "rebuild_fact",
    },
})


def obtener_facts_disponibles() -> list[str]:
    return list(CONFIG_FACTS.keys())


def obtener_tablas_bronce_por_dependencias(
    dependencias: list[str] | tuple[str, ...] | set[str],
) -> list[str]:
    dependencias_set = set(dependencias or [])
    tablas: list[str] = []

    for meta in CONFIG_FACTS.values():
        if not dependencias_set.intersection(meta.get("dependencias", ())):
            continue
        for tabla in meta.get("fuentes_bronce", ()):
            if tabla not in tablas:
                tablas.append(tabla)

    return tablas


def obtener_facts_con_marts() -> list[str]:
    return [
        nombre
        for nombre, meta in CONFIG_FACTS.items()
        if meta.get("marts")
    ]


def construir_catalogo_facts(funciones_por_fact: dict[str, object]) -> OrderedDict[str, dict]:
    nombres_config = list(CONFIG_FACTS.keys())
    nombres_funciones = list(funciones_por_fact.keys())

    faltantes = [nombre for nombre in nombres_config if nombre not in funciones_por_fact]
    sobrantes = [nombre for nombre in nombres_funciones if nombre not in CONFIG_FACTS]
    if faltantes or sobrantes:
        raise ValueError(
            'Catalogo de funciones inconsistente. '
            f'Faltantes: {faltantes} | Sobrantes: {sobrantes}'
        )

    catalogo: OrderedDict[str, dict] = OrderedDict()
    for nombre, meta in CONFIG_FACTS.items():
        catalogo[nombre] = {
            **meta,
            'nombre_fact': nombre,
            'funcion': funciones_por_fact[nombre],
        }
    return catalogo


def obtener_catalogo_facts() -> list[dict]:
    catalogo = []
    for nombre, meta in CONFIG_FACTS.items():
        catalogo.append({
            "nombre_fact": nombre,
            "orden": int(meta["orden"]),
            "tabla_destino": str(meta["tabla_destino"]),
            "fuentes_bronce": list(meta.get("fuentes_bronce", ())),
            "dependencias": list(meta.get("dependencias", ())),
            "marts": list(meta.get("marts", ())),
            "releer_bronce_por_estado": bool(meta.get("releer_bronce_por_estado", True)),
            "estrategia_rerun": str(meta.get("estrategia_rerun", "NO_DECLARADA")),
        })
    return catalogo


def normalizar_facts_solicitadas(facts_solicitadas: list[str] | tuple[str, ...] | None) -> list[str]:
    if not facts_solicitadas:
        return []

    mapa = {nombre.lower(): nombre for nombre in CONFIG_FACTS}
    normalizadas: list[str] = []
    desconocidas: list[str] = []

    for item in facts_solicitadas:
        if item is None:
            continue
        for fragmento in str(item).split(","):
            nombre = fragmento.strip()
            if not nombre:
                continue
            canonico = mapa.get(nombre.lower())
            if canonico is None:
                desconocidas.append(nombre)
                continue
            if canonico not in normalizadas:
                normalizadas.append(canonico)

    if desconocidas:
        disponibles = ", ".join(CONFIG_FACTS.keys())
        raise ValueError(
            f"Facts no reconocidas: {desconocidas}. Disponibles: {disponibles}"
        )

    return normalizadas


def resolver_plan_reproceso(
    facts_solicitadas: list[str] | tuple[str, ...] | None,
    incluir_dependencias: bool = True,
    refrescar_gold: bool = True,
) -> dict:
    facts = normalizar_facts_solicitadas(facts_solicitadas)
    if not facts:
        raise ValueError("Debe indicar al menos una fact para el reproceso dirigido.")

    facts_ordenadas = sorted(facts, key=lambda nombre: CONFIG_FACTS[nombre]["orden"])
    estrategias_invalidas = [
        nombre
        for nombre in facts_ordenadas
        if CONFIG_FACTS[nombre].get("estrategia_rerun") not in {"rebuild_fact", "rebuild_total_fact"}
    ]
    if estrategias_invalidas:
        raise ValueError(
            "Las siguientes facts no tienen estrategia_rerun declarada: "
            f"{estrategias_invalidas}"
        )

    dependencias = []
    if incluir_dependencias:
        dependencias_set = {
            dependencia
            for nombre in facts_ordenadas
            for dependencia in CONFIG_FACTS[nombre]["dependencias"]
        }
        dependencias = [
            dependencia
            for dependencia in ORDEN_DEPENDENCIAS
            if dependencia in dependencias_set
        ]

    marts = []
    if refrescar_gold:
        for nombre in facts_ordenadas:
            for mart in CONFIG_FACTS[nombre]["marts"]:
                if mart not in marts:
                    marts.append(mart)

    return {
        "facts": facts_ordenadas,
        "dependencias": dependencias,
        "marts": marts,
        "config_facts": {
            nombre: CONFIG_FACTS[nombre]
            for nombre in facts_ordenadas
        },
    }
