"""
api/rutas_alertas.py
=====================
Router /api/v1/alertas — Ack persistente de alertas del Control Center.

Las alertas se derivan dinámicamente en el portal (proxy /api/cc/alerts).
Aquí solo persistimos el estado "atendida" por ID_Alerta en MDM.Alerta_Ack.

Endpoints:
    GET    /v1/alertas/acks                    Lista de acks (con metadatos)
    POST   /v1/alertas/{id_alerta}/ack         Marca como atendida
    DELETE /v1/alertas/{id_alerta}/ack         Reabre

Seguridad:
    - GET    → viewer+
    - POST   → analista_mdm+
    - DELETE → analista_mdm+
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from nucleo.auth import UsuarioActual, obtener_usuario_actual, require_rol
from nucleo.excepciones import ErrorRecursoNoEncontrado
from schemas.alertas.peticion import PeticionAckAlerta
from schemas.alertas.respuesta import RespuestaAccionAck, RespuestaAckAlerta
from servicios.servicio_alertas import (
    desmarcar_ack,
    marcar_ack,
    obtener_acks,
)

enrutador_alertas = APIRouter(prefix="/v1/alertas", tags=["Alertas"])


_ID_ALERTA = Annotated[
    str,
    Path(
        min_length=1,
        max_length=120,
        description="Identificador estable de la alerta (ej. 'etl-12345', 'cuarentena-pendientes').",
        pattern=r"^[A-Za-z0-9._:\-]+$",
    ),
]


@enrutador_alertas.get(
    "/acks",
    response_model=list[RespuestaAckAlerta],
    summary="Lista alertas atendidas",
    description="Retorna las alertas marcadas como atendidas con quién/cuándo.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def listar_acks() -> list[RespuestaAckAlerta]:
    registros = await obtener_acks()
    return [RespuestaAckAlerta(**r) for r in registros]


@enrutador_alertas.post(
    "/{id_alerta}/ack",
    response_model=RespuestaAccionAck,
    summary="Marca una alerta como atendida",
    description="Upsert idempotente: si ya estaba acked, actualiza el usuario/comentario.",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def ack_alerta(
    id_alerta: _ID_ALERTA,
    body: PeticionAckAlerta,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> RespuestaAccionAck:
    await marcar_ack(
        id_alerta=id_alerta,
        usuario_dni=usuario.nombre_usuario,
        comentario=body.comentario,
    )
    return RespuestaAccionAck(
        id_alerta=id_alerta,
        accion="ack",
        mensaje=f"Alerta '{id_alerta}' marcada como atendida.",
    )


@enrutador_alertas.delete(
    "/{id_alerta}/ack",
    response_model=RespuestaAccionAck,
    summary="Reabre una alerta atendida",
    description="Borra el registro de ack. Devuelve 404 si no estaba marcada.",
    dependencies=[Depends(require_rol("analista_mdm"))],
)
async def unack_alerta(
    id_alerta: _ID_ALERTA,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> RespuestaAccionAck:
    existia = await desmarcar_ack(
        id_alerta=id_alerta,
        usuario_dni=usuario.nombre_usuario,
    )
    if not existia:
        raise ErrorRecursoNoEncontrado(f"Ack para alerta '{id_alerta}'")
    return RespuestaAccionAck(
        id_alerta=id_alerta,
        accion="unack",
        mensaje=f"Alerta '{id_alerta}' reabierta.",
    )
