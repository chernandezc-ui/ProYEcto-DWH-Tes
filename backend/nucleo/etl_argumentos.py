"""
nucleo/etl_argumentos.py
========================
Serializa la configuración opcional de una corrida ETL
sin requerir cambios de esquema en Control.*.
"""

from __future__ import annotations

import json
from json import JSONDecodeError


MARCADOR_COMENTARIO_ETL = "__ETL_OPTS__"
LONGITUD_MAX_COMENTARIO = 500


def serializar_comentario_etl(
    comentario_usuario: str | None = None,
    modo_ejecucion: str = "completo",
    facts: list[str] | None = None,
    incluir_dependencias: bool = True,
    refrescar_gold: bool = True,
    forzar_relectura_bronce: bool = True,
) -> str | None:
    comentario_limpio = (comentario_usuario or "").strip() or None
    facts_limpias = [str(fact).strip() for fact in (facts or []) if str(fact).strip()]

    if (
        modo_ejecucion == "completo"
        and not facts_limpias
        and incluir_dependencias
        and refrescar_gold
        and forzar_relectura_bronce
    ):
        return comentario_limpio

    payload = {
        "m": modo_ejecucion,
        "f": facts_limpias,
        "d": 1 if incluir_dependencias else 0,
        "g": 1 if refrescar_gold else 0,
        "b": 1 if forzar_relectura_bronce else 0,
    }
    if comentario_limpio:
        payload["c"] = comentario_limpio

    texto = MARCADOR_COMENTARIO_ETL + json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),  # compacto: sin espacios, mínimo payload
    )
    if len(texto) > LONGITUD_MAX_COMENTARIO:
        raise ValueError(
            "La configuración de la corrida excede el límite de 500 caracteres en Control.Corrida.Comentario."
        )
    return texto


def deserializar_comentario_etl(comentario: str | None) -> dict:
    if not comentario:
        return {
            "comentario": None,
            "modo_ejecucion": "completo",
            "facts": [],
            "incluir_dependencias": True,
            "refrescar_gold": True,
            "forzar_relectura_bronce": True,
        }

    if not comentario.startswith(MARCADOR_COMENTARIO_ETL):
        return {
            "comentario": comentario,
            "modo_ejecucion": "completo",
            "facts": [],
            "incluir_dependencias": True,
            "refrescar_gold": True,
            "forzar_relectura_bronce": True,
        }

    try:
        payload = json.loads(comentario[len(MARCADOR_COMENTARIO_ETL):])
    except JSONDecodeError:
        return {
            "comentario": comentario,
            "modo_ejecucion": "completo",
            "facts": [],
            "incluir_dependencias": True,
            "refrescar_gold": True,
            "forzar_relectura_bronce": True,
        }
    return {
        "comentario": payload.get("c"),
        "modo_ejecucion": payload.get("m", "completo"),
        "facts": payload.get("f") or [],
        "incluir_dependencias": bool(payload.get("d", 1)),
        "refrescar_gold": bool(payload.get("g", 1)),
        "forzar_relectura_bronce": bool(payload.get("b", 1)),
    }


def construir_argumentos_pipeline(comentario: str | None) -> list[str]:
    metadatos = deserializar_comentario_etl(comentario)
    if metadatos["modo_ejecucion"] != "facts":
        return []

    argumentos = [
        "--modo-ejecucion",
        "facts",
        "--facts",
        *metadatos["facts"],
    ]
    if not metadatos["incluir_dependencias"]:
        argumentos.append("--sin-dependencias")
    if not metadatos["refrescar_gold"]:
        argumentos.append("--sin-gold")
    if not metadatos["forzar_relectura_bronce"]:
        argumentos.append("--sin-relectura-bronce")
    return argumentos


def enriquecer_corrida_con_parametros(datos: dict | None) -> dict | None:
    if datos is None:
        return None

    comentario_raw = datos.get("comentario") or datos.get("Comentario")
    metadatos = deserializar_comentario_etl(comentario_raw)
    return {
        **datos,
        "comentario": metadatos["comentario"],
        "modo_ejecucion": metadatos["modo_ejecucion"],
        "facts": metadatos["facts"],
        "incluir_dependencias": metadatos["incluir_dependencias"],
        "refrescar_gold": metadatos["refrescar_gold"],
        "forzar_relectura_bronce": metadatos["forzar_relectura_bronce"],
    }
