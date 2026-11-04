"""
nucleo/settings.py
==================
Configuración formal del backend ACP Platform.

Configuración del backend; hereda el contrato de conexión de comun/configuracion.py.
Ambos leen únicamente el .env raíz y las variables del proceso.

Perfiles:
    dev   — recarga automática, logging verboso, CORS amplio
    test  — perfil de pruebas; por sí solo no sustituye SQL Server
    prod  — sin reload, logging JSON compacto, CORS estricto

Orden de carga (del menos al más prioritario):
    1. .env en la raíz del proyecto
    2. Variables de sistema del SO
    3. Parámetros explícitos al construir Settings
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator

# Compatibilidad con el arranque directo desde backend/ sin instalar paquetes.
_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.configuracion import ConfiguracionBD, RAIZ_PROYECTO

_DIR_PROYECTO = RAIZ_PROYECTO


class Settings(ConfiguracionBD):
    """
    Configuración centralizada del backend.
    Todas las variables tienen valores por defecto seguros para desarrollo.
    """

    # ── Entorno ────────────────────────────────────────────────────────────────
    entorno: Literal["dev", "test", "prod"] = Field(
        default="dev",
        alias="ACP_ENTORNO",
        description="Perfil de ejecución: dev | test | prod",
    )

    # ── Servidor ───────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="ACP_HOST")
    puerto: int = Field(default=8810, alias="ACP_PUERTO")
    workers: int = Field(default=1, alias="ACP_WORKERS")
    reload: bool = Field(default=False, alias="ACP_RELOAD")
    runner_activo: bool = Field(default=False, alias="ACP_RUNNER_ACTIVO")

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origenes: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:8510",
            "http://127.0.0.1:8510",
        ],
        alias="ACP_CORS_ORIGENES",
        description="Lista JSON de orígenes permitidos, ej: '[\"http://mi-host:3000\"]'",
    )

    # ── Logging ────────────────────────────────────────────────────────────────
    log_nivel: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="ACP_LOG_NIVEL",
    )
    log_formato: Literal["json", "texto"] = Field(
        default="json",
        alias="ACP_LOG_FORMATO",
        description="'json' para prod; 'texto' para dev con colores",
    )

    # ── ETL ────────────────────────────────────────────────────────────────────
    etl_dir: Path = Field(
        default=_DIR_PROYECTO / "ETL",
        alias="ACP_ETL_DIR",
        description="Ruta absoluta al directorio ETL/",
    )

    # ── API metadata ───────────────────────────────────────────────────────────
    api_titulo: str = Field(
        default="ACP Platform API",
        alias="ACP_API_TITULO",
    )
    api_version: str = Field(
        default="1.1.0",
        alias="ACP_API_VERSION",
    )

    # ── JWT / Autenticación ────────────────────────────────────────────────
    jwt_secreto: str = Field(
        alias="ACP_JWT_SECRETO",
        description="Clave HMAC para firmar JWT. OBLIGATORIO.",
        min_length=32,
        repr=False,
    )
    jwt_ttl_min: int = Field(
        default=480,   # 8 horas
        alias="ACP_JWT_TTL_MIN",
        description="Tiempo de vida del token en minutos.",
    )
    jwt_algoritmo: str = Field(
        default="HS256",
        alias="ACP_JWT_ALGORITMO",
    )

    @field_validator("cors_origenes", mode="before")
    @classmethod
    def parsear_cors(cls, v: str | list[str]) -> list[str]:
        """Acepta la variable como JSON string o como lista Python."""
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # Si es un string simple (un solo origen), lo envuelve en lista
            return [v]
        return v

    @property
    def es_desarrollo(self) -> bool:
        return self.entorno == "dev"

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "prod"

    @property
    def es_test(self) -> bool:
        return self.entorno == "test"

    @property
    def script_pipeline(self) -> Path:
        return self.etl_dir / "pipeline.py"


@lru_cache(maxsize=1)
def obtener_settings() -> Settings:
    """
    Retorna la instancia singleton de Settings.
    Usa lru_cache para garantizar que el .env se carga una sola vez.
    """
    try:
        return Settings()
    except ValidationError as e:
        print("\n\033[31m" + "!" * 80)
        print("  ERROR DE CONFIGURACIÓN (ZERO-TRUST COMPLIANCE)")
        print("!" * 80 + "\033[0m")
        print("\nEl backend no puede iniciar porque faltan variables críticas en el archivo .env\n")
        
        for error in e.errors():
            campo = " -> ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            print(f"  \033[33m[ FALTA ]\033[0m {campo}: {msg}")
            
        print("\n\033[36mSOLUCIÓN:\033[0m")
        print("  1. Abre (o crea) el archivo '.env' en la raíz del proyecto")
        print("  2. Usa '.env.example' como guía o ejecuta python instalar.py.")
        print("  3. Asegúrate de definir DB_SERVIDOR, DB_NOMBRE y ACP_JWT_SECRETO.")
        print("\n" + "!" * 80 + "\n")
        sys.exit(1)


# Alias de importación directa: from nucleo.settings import settings
try:
    settings = obtener_settings()
except Exception:
    # Este bloque es por si algo falla fuera de la validación de Pydantic
    sys.exit(1)
