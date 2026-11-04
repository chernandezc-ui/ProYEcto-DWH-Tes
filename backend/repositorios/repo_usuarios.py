"""
repositorios/repo_usuarios.py
==============================
SQL CRUD para Seguridad.Usuarios.

Responsabilidades:
  - Buscar usuario por nombre (para login)
  - Actualizar último acceso
  - Insertar / listar / activar / desactivar (solo admin)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos, ErrorRecursoNoEncontrado
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


# ── Consultas ──────────────────────────────────────────────────────────────────

def buscar_por_nombre(nombre_usuario: str) -> dict | None:
    """
    Retorna el registro completo del usuario activo o None si no existe.
    Incluye el hash de la contraseña (solo para uso interno del servicio auth).
    """
    try:
        with obtener_engine().connect() as con:
            fila = con.execute(
                text("""
                    SELECT
                        ID_Usuario      AS id_usuario,
                        Nombre_Usuario  AS nombre_usuario,
                        Nombre_Display  AS nombre_display,
                        Email           AS email,
                        Hash_Clave      AS hash_clave,
                        Rol             AS rol,
                        Es_Activo       AS es_activo,
                        Fecha_Creacion  AS fecha_creacion,
                        Ultimo_Acceso   AS ultimo_acceso
                    FROM Seguridad.Usuarios
                    WHERE Nombre_Usuario = :nombre
                      AND Es_Activo = 1
                """),
                {"nombre": nombre_usuario},
            ).fetchone()
            return dict(fila._mapping) if fila else None
    except SQLAlchemyError:
        log.exception("Error al buscar usuario", extra={"usuario": nombre_usuario})
        raise ErrorBaseDatos()


def registrar_ultimo_acceso(nombre_usuario: str) -> None:
    """Actualiza Ultimo_Acceso al momento actual. Falla silenciosamente."""
    try:
        with obtener_engine().begin() as con:
            con.execute(
                text("""
                    UPDATE Seguridad.Usuarios
                    SET Ultimo_Acceso = :ahora
                    WHERE Nombre_Usuario = :nombre
                """),
                {"ahora": datetime.now(), "nombre": nombre_usuario},
            )
    except SQLAlchemyError:
        log.warning("No se pudo actualizar Ultimo_Acceso", extra={"usuario": nombre_usuario})


def listar_usuarios() -> list[dict]:
    """Lista todos los usuarios (activos e inactivos). Solo para admin."""
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(text("""
                SELECT
                    ID_Usuario      AS id_usuario,
                    Nombre_Usuario  AS nombre_usuario,
                    Nombre_Display  AS nombre_display,
                    Email           AS email,
                    Rol             AS rol,
                    Es_Activo       AS es_activo,
                    Fecha_Creacion  AS fecha_creacion,
                    Ultimo_Acceso   AS ultimo_acceso
                FROM Seguridad.Usuarios
                ORDER BY Nombre_Usuario
            """)).fetchall()
            return [dict(fila._mapping) for fila in filas]
    except SQLAlchemyError:
        log.exception("Error al listar usuarios")
        raise ErrorBaseDatos()


def insertar_usuario(
    nombre_usuario: str,
    nombre_display: str,
    hash_clave: str,
    rol: str,
    email: str | None = None,
) -> int:
    """Inserta un nuevo usuario. Retorna el ID generado."""
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("""
                    INSERT INTO Seguridad.Usuarios
                        (Nombre_Usuario, Nombre_Display, Email, Hash_Clave, Rol, Es_Activo)
                    OUTPUT INSERTED.ID_Usuario
                    VALUES (:nombre, :display, :email, :hash, :rol, 1)
                """),
                {
                    "nombre":  nombre_usuario,
                    "display": nombre_display,
                    "email":   email,
                    "hash":    hash_clave,
                    "rol":     rol,
                },
            )
            id_nuevo = resultado.fetchone()[0]
            log.info("Usuario creado", extra={"usuario": nombre_usuario, "rol": rol})
            return id_nuevo
    except SQLAlchemyError:
        log.exception("Error al insertar usuario", extra={"usuario": nombre_usuario})
        raise ErrorBaseDatos()


def cambiar_estado(nombre_usuario: str, activo: bool) -> None:
    """Activa o desactiva un usuario. Lanza ErrorRecursoNoEncontrado si no existe."""
    try:
        with obtener_engine().begin() as con:
            rows = con.execute(
                text("""
                    UPDATE Seguridad.Usuarios
                    SET Es_Activo = :activo
                    WHERE Nombre_Usuario = :nombre
                """),
                {"activo": 1 if activo else 0, "nombre": nombre_usuario},
            ).rowcount
        if rows == 0:
            raise ErrorRecursoNoEncontrado(f"Usuario '{nombre_usuario}'")
    except (ErrorRecursoNoEncontrado, ErrorBaseDatos):
        raise
    except SQLAlchemyError:
        log.exception("Error al cambiar estado del usuario")
        raise ErrorBaseDatos()


def cambiar_hash_clave(nombre_usuario: str, nuevo_hash: str) -> None:
    """Actualiza el hash de contraseña de un usuario."""
    try:
        with obtener_engine().begin() as con:
            rows = con.execute(
                text("""
                    UPDATE Seguridad.Usuarios
                    SET Hash_Clave = :hash
                    WHERE Nombre_Usuario = :nombre AND Es_Activo = 1
                """),
                {"hash": nuevo_hash, "nombre": nombre_usuario},
            ).rowcount
        if rows == 0:
            raise ErrorRecursoNoEncontrado(f"Usuario activo '{nombre_usuario}'")
    except (ErrorRecursoNoEncontrado, ErrorBaseDatos):
        raise
    except SQLAlchemyError:
        log.exception("Error al cambiar contraseña")
        raise ErrorBaseDatos()
