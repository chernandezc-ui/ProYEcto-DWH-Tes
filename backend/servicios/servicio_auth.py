"""
servicios/servicio_auth.py
==========================
Lógica de negocio de autenticación.

Coordina: repositorio de usuarios + core de auth + auditoría de acceso.
El router de auth solo llama funciones de este servicio.
"""

from __future__ import annotations

import asyncio

from fastapi import HTTPException, status

from nucleo.auth import crear_token, verificar_clave
from nucleo.logging import obtener_logger
import repositorios.repo_log_acceso as repo_log
import repositorios.repo_usuarios as repo

log = obtener_logger(__name__)


def autenticar_usuario(
    nombre_usuario: str,
    clave: str,
    request_id: str | None = None,
    ip_origen: str | None = None,
) -> dict:
    """
    Valida credenciales y retorna el dict del token JWT.

    Flujo:
        1. Busca el usuario activo en BD.
        2. Verifica la contraseña con bcrypt.
        3. Actualiza Ultimo_Acceso.
        4. Genera y retorna el token JWT.
        5. Registra el acceso en la auditoría.

    Lanza HTTPException 401 si las credenciales son inválidas.
    """
    usuario = repo.buscar_por_nombre(nombre_usuario)

    # Verificación constante-time (evita timing attacks)
    clave_ok = (
        usuario is not None
        and verificar_clave(clave, usuario["hash_clave"])
    )

    if not clave_ok:
        log.warning(
            "Intento de login fallido",
            extra={"usuario": nombre_usuario, "request_id": request_id},
        )
        repo_log.registrar_acceso(
            nombre_usuario=nombre_usuario,
            accion="LOGIN",
            resultado="DENEGADO",
            request_id=request_id,
            ip_origen=ip_origen,
            detalle="Credenciales incorrectas",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Login exitoso
    repo.registrar_ultimo_acceso(nombre_usuario)

    token = crear_token(
        nombre_usuario=usuario["nombre_usuario"],
        rol=usuario["rol"],
        nombre_display=usuario["nombre_display"],
    )

    repo_log.registrar_acceso(
        nombre_usuario=nombre_usuario,
        accion="LOGIN",
        resultado="OK",
        request_id=request_id,
        ip_origen=ip_origen,
    )

    log.info(
        "Login exitoso",
        extra={"usuario": nombre_usuario, "rol": usuario["rol"]},
    )

    return {
        "access_token": token,
        "token_type":   "bearer",
        "usuario": {
            "nombre_usuario": usuario["nombre_usuario"],
            "nombre_display":  usuario["nombre_display"],
            "rol":             usuario["rol"],
            "email":           usuario.get("email"),
        },
    }


async def registrar_accion(
    nombre_usuario: str,
    accion: str,
    resultado: str = "OK",
    endpoint: str | None = None,
    request_id: str | None = None,
    ip_origen: str | None = None,
    detalle: str | None = None,
) -> None:
    """
    Registra una acción mutable en Auditoria.Log_Acceso.
    Llamar desde endpoints que modifican estado.
    """
    await asyncio.to_thread(
        repo_log.registrar_acceso,
        nombre_usuario=nombre_usuario,
        accion=accion,
        resultado=resultado,
        endpoint=endpoint,
        request_id=request_id,
        ip_origen=ip_origen,
        detalle=detalle,
    )
