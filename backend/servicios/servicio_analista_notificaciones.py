from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from nucleo.conexion import obtener_engine
from nucleo.logging import obtener_logger
from schemas.analista.modelos import ItemNotificacion, RespuestaNotificaciones

log = obtener_logger(__name__)


def _query_sync(page: int, page_size: int, severidad: str | None) -> RespuestaNotificaciones:
    engine = obtener_engine()
    try:
        offset = (page - 1) * page_size
        limit_hasta = offset + page_size

        where = "WHERE 1=1"
        params: dict[str, Any] = {"offset_n": offset, "limit_hasta": limit_hasta}
        if severidad:
            where += " AND severidad = :severidad"
            params["severidad"] = severidad

        sql_items = text(f"""
            SELECT *
            FROM (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY timestamp DESC) AS rn,
                    CAST(id AS VARCHAR(36)) AS id,
                    tipo, severidad, titulo, descripcion,
                    CONVERT(VARCHAR(30), timestamp, 126) AS timestamp,
                    leida, link
                FROM MDM.Alertas
                {where}
            ) AS paged
            WHERE rn > :offset_n AND rn <= :limit_hasta
        """)

        count_params: dict[str, Any] = {}
        if severidad:
            count_params["severidad"] = severidad
        sql_total = text(f"SELECT COUNT(*) FROM MDM.Alertas {where}")
        sql_unread = text(f"SELECT COUNT(*) FROM MDM.Alertas {where} AND leida = 0")

        with engine.connect() as conn:
            rows = conn.execute(sql_items, params).fetchall()
            total = conn.execute(sql_total, count_params).scalar() or 0
            no_leidas = conn.execute(sql_unread, count_params).scalar() or 0

        items = [
            ItemNotificacion(
                id=str(r.id),
                tipo=r.tipo,
                severidad=r.severidad,
                titulo=r.titulo,
                descripcion=r.descripcion,
                timestamp=r.timestamp,
                leida=bool(r.leida),
                link=r.link,
            )
            for r in rows
        ]
        return RespuestaNotificaciones(items=items, total=total, no_leidas=no_leidas)
    except (OperationalError, ProgrammingError) as exc:
        log.warning("Tabla MDM.Alertas no disponible o BD caída", exc_info=True)
        return RespuestaNotificaciones(items=[], total=0, no_leidas=0)


async def obtener_notificaciones(
    page: int = 1,
    page_size: int = 25,
    severidad: str | None = None,
) -> RespuestaNotificaciones:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _query_sync, page, page_size, severidad)
