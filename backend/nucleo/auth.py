"""
nucleo/auth.py
==============
Core de autenticación y autorización del backend ACP Platform.

Responsabilidades:
  - Hashing y verificación de contraseñas (bcrypt via passlib)
  - Generación y validación de JWT (python-jose HS256)
  - Dependencias FastAPI: obtener_usuario_actual, require_rol

Diseño compatible con AD/SSO:
  El sistema valida tokens JWT. Si en el futuro se usa un IdP externo
  (Azure AD, Okta) el token llega pre-firmado. Solo cambia la clave
  de verificación y el claim de roles — la capa de dependencias no cambia.

Configuración requerida en settings/.env:
  ACP_JWT_SECRETO   — clave HMAC (mínimo 32 chars en producción)
  ACP_JWT_TTL_MIN   — tiempo de vida del token en minutos (default: 480 = 8h)
  ACP_JWT_ALGORITMO — algoritmo JWT (default: HS256)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from nucleo.logging import obtener_logger
from nucleo.settings import settings
from repositorios import repo_usuarios

log = obtener_logger(__name__)

# ── Constantes ─────────────────────────────────────────────────────────────────
_SCHEME = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Jerarquía de roles: cada rol incluye los permisos del nivel inferior
_JERARQUIA: dict[str, int] = {
    "admin":        40,
    "operador_etl": 30,
    "analista_mdm": 20,
    "viewer":       10,
}

# Mapa de acceso por endpoint (rol mínimo requerido)
RBAC: dict[str, str] = {
    # ETL
    "lanzar_corrida":        "operador_etl",
    "ver_corridas":          "viewer",
    "stream_corrida":        "operador_etl",
    # Cuarentena
    "ver_cuarentena":        "viewer",
    "resolver_cuarentena":   "analista_mdm",
    "rechazar_cuarentena":   "analista_mdm",
    # Catálogos
    "ver_catalogos":         "viewer",
    # Auditoría
    "ver_auditoria":         "viewer",
    # Administración
    "admin_usuarios":        "admin",
}


# ── Hashing ────────────────────────────────────────────────────────────────────

def hash_clave(clave: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    sal = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(clave.encode("utf-8"), sal).decode("utf-8")


def verificar_clave(clave_plana: str, hash_almacenado: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt almacenado."""
    try:
        return bcrypt.checkpw(
            clave_plana.encode("utf-8"),
            hash_almacenado.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT ────────────────────────────────────────────────────────────────────────

def crear_token(
    nombre_usuario: str,
    rol: str,
    nombre_display: str,
    ttl_minutos: int | None = None,
) -> str:
    """
    Genera un JWT firmado con los claims del usuario.

    Claims:
        sub         — nombre_usuario (sujeto estándar JWT)
        rol         — rol del usuario
        display     — nombre para mostrar
        iat         — issued at
        exp         — expira en
    """
    ttl = ttl_minutos or settings.jwt_ttl_min
    ahora   = datetime.now(tz=timezone.utc)
    expira  = ahora + timedelta(minutes=ttl)

    payload = {
        "sub":     nombre_usuario,
        "rol":     rol,
        "display": nombre_display,
        "iat":     ahora,
        "exp":     expira,
    }

    return jwt.encode(payload, settings.jwt_secreto, algorithm=settings.jwt_algoritmo)


def decodificar_token(token: str) -> dict:
    """
    Decodifica y valida un JWT.
    Lanza HTTPException 401 si el token es inválido o expirado.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secreto,
            algorithms=[settings.jwt_algoritmo],
        )
    except JWTError as e:
        # No registrar el token ni el detalle del error a nivel INFO/print:
        # el token en claro en logs es material de robo de sesión (V-02).
        log.warning("Token JWT inválido", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Modelo de usuario autenticado ──────────────────────────────────────────────

class UsuarioActual:
    """Representa el usuario autenticado extraído del JWT."""

    __slots__ = ("nombre_usuario", "rol", "nombre_display")

    def __init__(self, nombre_usuario: str, rol: str, nombre_display: str) -> None:
        self.nombre_usuario = nombre_usuario
        self.rol            = rol
        self.nombre_display = nombre_display

    @classmethod
    def desde_payload(cls, payload: dict) -> "UsuarioActual":
        nombre = payload.get("sub")
        rol    = payload.get("rol", "viewer")
        disp   = payload.get("display", nombre)
        if not nombre:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token sin sujeto válido.",
            )
        return cls(nombre_usuario=nombre, rol=rol, nombre_display=disp)

    def tiene_rol(self, rol_requerido: str) -> bool:
        """Verifica si el usuario tiene al menos el nivel de rol requerido."""
        nivel_usuario   = _JERARQUIA.get(self.rol, 0)
        nivel_requerido = _JERARQUIA.get(rol_requerido, 999)
        return nivel_usuario >= nivel_requerido

    def __repr__(self) -> str:
        return f"<Usuario {self.nombre_usuario!r} rol={self.rol!r}>"


# ── Dependencias FastAPI ───────────────────────────────────────────────────────

async def obtener_usuario_actual(
    token: Annotated[str, Depends(_SCHEME)],
) -> UsuarioActual:
    """
    Dependencia FastAPI: extrae y valida el usuario desde el Bearer token.
    Inyectable en cualquier endpoint con: usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)]
    """
    payload = decodificar_token(token)
    nombre = payload.get("sub")
    usuario_db = repo_usuarios.buscar_por_nombre(nombre) if nombre else None
    if not usuario_db:
        log.warning("Token con usuario inexistente o inactivo", extra={"sub": nombre})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada o usuario inactivo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UsuarioActual.desde_payload(payload)


def require_rol(*roles: str):
    """
    Fábrica de dependencias: requiere que el usuario tenga al menos uno
    de los roles especificados.

    Uso:
        @router.post("/", dependencies=[Depends(require_rol("operador_etl"))])
        def endpoint(): ...
    """
    async def _dependency(
        usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
    ) -> UsuarioActual:
        for rol in roles:
            if usuario.tiene_rol(rol):
                return usuario
        log.warning(
            "Acceso denegado por rol insuficiente",
            extra={
                "usuario":        usuario.nombre_usuario,
                "rol_usuario":    usuario.rol,
                "roles_requeridos": list(roles),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Rol insuficiente. Se requiere: {' o '.join(roles)}.",
        )

    return _dependency
