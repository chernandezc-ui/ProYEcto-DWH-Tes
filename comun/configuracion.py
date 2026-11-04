"""Conexión compartida: parámetros explícitos > entorno > .env de la raíz."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
ENV_GLOBAL = RAIZ_PROYECTO / '.env'


class ConfiguracionBD(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_GLOBAL, env_file_encoding='utf-8', case_sensitive=False,
        extra='ignore', hide_input_in_errors=True,
    )

    db_servidor: str = Field(alias='DB_SERVIDOR', min_length=1)
    db_nombre: str = Field(alias='DB_NOMBRE', min_length=1)
    db_usuario: str | None = Field(default=None, alias='DB_USUARIO')
    db_clave: str | None = Field(default=None, alias='DB_CLAVE', repr=False)
    db_driver: str = Field(default='ODBC Driver 17 for SQL Server', alias='DB_DRIVER', min_length=1)

    @field_validator('db_usuario', mode='before')
    @classmethod
    def usuario_vacio_es_windows_auth(cls, value):
        return None if value == '' else value


@lru_cache(maxsize=1)
def obtener_configuracion_bd() -> ConfiguracionBD:
    return ConfiguracionBD(_env_file=ENV_GLOBAL)
