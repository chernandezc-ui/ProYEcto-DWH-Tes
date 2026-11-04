"""
bridges_tasa_crecimiento.py
===========================
Helpers para resolver dimensiones y sincronizar bridges del fact
Tasa_Crecimiento_Brotes:

- resolver_id_cama: Cama_Raw -> Dim_Cama_Catalogo.ID_Cama_Catalogo
- resolver_id_condicion: Condicion_Raw (texto libre) -> Dim_Condicion_Cultivo
- garantizar_bridge_geografia_cama: upsert idempotente del par (geo, cama)
- sincronizar_bridge_modulo_campana_condicion: poblar ID_Condicion en el
  bridge si esta NULL para la fila vigente (modulo, variedad, campana).
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from mdm.lookup import _obtener_id_catalogo
from utils.texto import normalizar_componente_geografico


_CACHE_DIM_CONDICION: dict[tuple[str, str], int] = {}


def _normalizar_texto(valor) -> str:
    if valor is None:
        return ''
    texto = unicodedata.normalize('NFKD', str(valor))
    texto = ''.join(ch for ch in texto if not unicodedata.combining(ch))
    return texto.upper().strip()


def resolver_id_cama(cama_raw, engine: Engine) -> int | None:
    """
    Busca ID_Cama_Catalogo desde Cama_Raw. Reusa la normalizacion de
    componentes geograficos para que coincida con el seed del catalogo.
    Retorna None si no hay match (la cama no esta en el catalogo).
    """
    cama_token = normalizar_componente_geografico(cama_raw) if cama_raw is not None else None
    if not cama_token:
        return None
    id_cama = _obtener_id_catalogo(
        engine,
        'Silver.Dim_Cama_Catalogo',
        'ID_Cama_Catalogo',
        'Cama_Normalizada',
        cama_token,
    )
    return id_cama if id_cama and id_cama > 0 else None


_PATRON_CERTIFICACION = re.compile(r'\b(ORGANIC[OA]?|CONVENCIONAL|CONV)\b')
_PATRON_SUSTRATO = re.compile(r'\b(COCO|TIERRA|SUELO)\b')


def _parsear_condicion(texto_norm: str) -> tuple[str, str]:
    cert_match = _PATRON_CERTIFICACION.search(texto_norm)
    sust_match = _PATRON_SUSTRATO.search(texto_norm)

    if cert_match:
        cert = cert_match.group(1)
        if cert in ('ORGANICA', 'ORGANIC'):
            cert = 'ORGANICO'
        elif cert == 'CONV':
            cert = 'CONVENCIONAL'
    else:
        cert = 'DESCONOCIDA'

    if sust_match:
        sust = sust_match.group(1)
        if sust == 'SUELO':
            sust = 'TIERRA'
    else:
        sust = 'COCO' if cert != 'DESCONOCIDA' else 'DESCONOCIDO'

    return sust, cert


def _cargar_mapa_condicion(engine: Engine) -> dict[tuple[str, str], int]:
    if _CACHE_DIM_CONDICION:
        return _CACHE_DIM_CONDICION
    with engine.connect() as conexion:
        filas = conexion.execute(text("""
            SELECT ID_Condicion, Sustrato, Certificacion
            FROM Silver.Dim_Condicion_Cultivo
        """)).fetchall()
    for id_condicion, sustrato, certificacion in filas:
        _CACHE_DIM_CONDICION[(str(sustrato).upper(), str(certificacion).upper())] = int(id_condicion)
    return _CACHE_DIM_CONDICION


def resolver_id_condicion(condicion_raw, engine: Engine) -> int | None:
    """
    Parsea texto libre de Condicion_Raw (ej. 'ORGANICO COCO', 'Convencional')
    y resuelve a Dim_Condicion_Cultivo.ID_Condicion. Retorna None si no parsea.
    """
    if condicion_raw is None:
        return None
    texto_norm = _normalizar_texto(condicion_raw)
    if not texto_norm:
        return None

    sustrato, certificacion = _parsear_condicion(texto_norm)
    mapa = _cargar_mapa_condicion(engine)
    
    # 1. Intentar combinación exacta (sustrato, certificacion)
    id_condicion = mapa.get((sustrato, certificacion))
    if id_condicion is not None:
        return id_condicion

    # 2. Fallback: Buscar con sustrato genérico 'N/A'
    id_condicion = mapa.get(('N/A', certificacion))
    if id_condicion is not None:
        return id_condicion

    return mapa.get(('DESCONOCIDO', 'DESCONOCIDA'))


def garantizar_bridge_geografia_cama(
    conexion,
    id_geografia: int,
    id_cama_catalogo: int,
    fecha_inicio,
) -> None:
    """
    OBSOLETA: Bridge_Geografia_Cama fue eliminada en la fase 45.
    Las camas ahora se registran directamente en Dim_Geografia.
    """
    return


def sincronizar_bridge_modulo_campana_condicion(
    conexion,
    id_modulo_catalogo: int,
    id_variedad: int,
    id_campana: int,
    id_condicion: int,
) -> None:
    """
    Si el bridge tiene una fila vigente (modulo, variedad, campana) con
    ID_Condicion NULL, la rellena con la condicion recibida. Si ya tiene
    valor distinto no la sobrescribe (la trazabilidad historica se mantiene
    via la fila existente; cambios reales viven en filas de otras campanas).
    """
    if not all([id_modulo_catalogo, id_variedad, id_campana, id_condicion]):
        return
    conexion.execute(
        text("""
            UPDATE Silver.Bridge_Modulo_Campana
            SET ID_Condicion = :id_condicion
            WHERE ID_Modulo_Catalogo = :id_modulo
              AND ID_Variedad        = :id_variedad
              AND ID_Campana         = :id_campana
              AND ID_Condicion IS NULL
        """),
        {
            'id_modulo': int(id_modulo_catalogo),
            'id_variedad': int(id_variedad),
            'id_campana': int(id_campana),
            'id_condicion': int(id_condicion),
        },
    )
