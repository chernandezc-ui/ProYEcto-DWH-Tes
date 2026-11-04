"""
api/rutas_auth.py
==================
Router de autenticación del backend ACP Platform.

Endpoints:
    POST /auth/login    — intercambia credenciales por JWT
    GET  /auth/me       — retorna el perfil del usuario autenticado
    POST /auth/usuarios — crea un nuevo usuario (solo admin)
    GET  /auth/usuarios — lista todos los usuarios (solo admin)
    POST /auth/usuarios/{nombre}/desactivar — desactiva usuario (solo admin)
    POST /auth/usuarios/{nombre}/activar    — activa usuario (solo admin)
    POST /auth/cambiar-clave — cambia contraseña del usuario actual

Nota: NO hay endpoint /auth/logout en tokens stateless.
      Para invalidar sesiones en el futuro usar una blacklist Redis.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from nucleo.rate_limit import verificar_rate_limit
from nucleo.auth import (
    UsuarioActual,
    hash_clave,
    obtener_usuario_actual,
    require_rol,
    verificar_clave,
)
from nucleo.excepciones import ErrorRecursoNoEncontrado, ErrorValidacion
from nucleo.http_utils import obtener_ip_cliente, obtener_request_id
from schemas.auth.peticion import PeticionCambiarClave, PeticionCrearUsuario
from schemas.auth.respuesta import (
    PerfilUsuario,
    RespuestaMensaje,
    RespuestaUsuarioAdmin,
    TokenRespuesta,
)
from servicios.servicio_auth import autenticar_usuario
import repositorios.repo_usuarios as repo_usuarios

enrutador_auth = APIRouter(prefix="/auth", tags=["Autenticación"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rate_limit_login(request: Request) -> None:
    verificar_rate_limit(request, max_intentos=5, ventana_segundos=60)


# ── Login ──────────────────────────────────────────────────────────────────────

@enrutador_auth.post(
    "/login",
    response_model=TokenRespuesta,
    summary="Iniciar sesión",
    description=(
        "Intercambia credenciales (usuario/contraseña) por un token JWT Bearer. "
        "Compatible con el formulario estándar OAuth2 Password Flow."
    ),
)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    _: None = Depends(_rate_limit_login),
) -> TokenRespuesta:
    """
    Acepta tanto form-data (OAuth2 estándar) como JSON.
    El campo 'username' del form es el nombre_usuario.
    """
    datos = autenticar_usuario(
        nombre_usuario=form.username,
        clave=form.password,
        request_id=obtener_request_id(request),
        ip_origen=obtener_ip_cliente(request),
    )
    return TokenRespuesta(
        access_token=datos["access_token"],
        token_type="bearer",
        usuario=PerfilUsuario(**datos["usuario"]),
    )


# ── Perfil del usuario actual ──────────────────────────────────────────────────

@enrutador_auth.get(
    "/me",
    response_model=PerfilUsuario,
    summary="Perfil del usuario autenticado",
)
async def perfil_actual(
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> PerfilUsuario:
    """Retorna el perfil del usuario extraído del JWT."""
    return PerfilUsuario(
        nombre_usuario=usuario.nombre_usuario,
        nombre_display=usuario.nombre_display,
        rol=usuario.rol,
        email=None,  # El email no viaja en el token — requiere consulta a BD si se necesita
    )


# ── Cambiar contraseña ─────────────────────────────────────────────────────────

@enrutador_auth.post(
    "/cambiar-clave",
    response_model=RespuestaMensaje,
    summary="Cambiar contraseña del usuario actual",
)
async def cambiar_clave(
    cuerpo: PeticionCambiarClave,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> RespuestaMensaje:
    datos_bd = repo_usuarios.buscar_por_nombre(usuario.nombre_usuario)
    if not datos_bd or not verificar_clave(cuerpo.clave_actual, datos_bd["hash_clave"]):
        raise ErrorValidacion("La contraseña actual es incorrecta.")

    nuevo_hash = hash_clave(cuerpo.clave_nueva)
    repo_usuarios.cambiar_hash_clave(usuario.nombre_usuario, nuevo_hash)
    return RespuestaMensaje(mensaje="Contraseña actualizada correctamente.")


# ── Administración de usuarios (solo admin) ────────────────────────────────────

@enrutador_auth.get(
    "/usuarios",
    response_model=list[RespuestaUsuarioAdmin],
    summary="Listar todos los usuarios",
    dependencies=[Depends(require_rol("admin"))],
)
async def listar_usuarios() -> list[RespuestaUsuarioAdmin]:
    registros = repo_usuarios.listar_usuarios()
    return [RespuestaUsuarioAdmin(**r) for r in registros]


@enrutador_auth.post(
    "/usuarios",
    response_model=RespuestaUsuarioAdmin,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
    dependencies=[Depends(require_rol("admin"))],
)
async def crear_usuario(
    cuerpo: PeticionCrearUsuario,
) -> RespuestaUsuarioAdmin:
    roles_validos = {"admin", "operador_etl", "analista_mdm", "viewer"}
    if cuerpo.rol not in roles_validos:
        raise ErrorValidacion(f"Rol inválido. Opciones: {', '.join(sorted(roles_validos))}")

    nuevo_hash = hash_clave(cuerpo.clave)
    id_nuevo = repo_usuarios.insertar_usuario(
        nombre_usuario=cuerpo.nombre_usuario,
        nombre_display=cuerpo.nombre_display,
        hash_clave=nuevo_hash,
        rol=cuerpo.rol,
        email=cuerpo.email,
    )
    datos = repo_usuarios.buscar_por_nombre(cuerpo.nombre_usuario)
    return RespuestaUsuarioAdmin(
        id_usuario=id_nuevo,
        nombre_usuario=cuerpo.nombre_usuario,
        nombre_display=cuerpo.nombre_display,
        email=cuerpo.email,
        rol=cuerpo.rol,
        es_activo=True,
        fecha_creacion=datos["fecha_creacion"] if datos else None,
        ultimo_acceso=None,
    )


@enrutador_auth.post(
    "/usuarios/{nombre_usuario}/desactivar",
    response_model=RespuestaMensaje,
    summary="Desactivar un usuario",
    dependencies=[Depends(require_rol("admin"))],
)
async def desactivar_usuario(nombre_usuario: str) -> RespuestaMensaje:
    repo_usuarios.cambiar_estado(nombre_usuario, activo=False)
    return RespuestaMensaje(mensaje=f"Usuario '{nombre_usuario}' desactivado.")


@enrutador_auth.post(
    "/usuarios/{nombre_usuario}/activar",
    response_model=RespuestaMensaje,
    summary="Activar un usuario",
    dependencies=[Depends(require_rol("admin"))],
)
async def activar_usuario(nombre_usuario: str) -> RespuestaMensaje:
    repo_usuarios.cambiar_estado(nombre_usuario, activo=True)
    return RespuestaMensaje(mensaje=f"Usuario '{nombre_usuario}' activado.")
