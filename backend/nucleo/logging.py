"""
nucleo/logging.py
=================
Configuración centralizada de logging para el backend ACP Platform.

- Formato JSON en prod (parseable por Loki, Datadog, etc.)
- Formato texto con colores en dev (legible en consola)
- Campos estándar: timestamp, level, service, request_id, message

Uso:
    from nucleo.logging import obtener_logger
    log = obtener_logger(__name__)
    log.info("Mensaje", extra={"request_id": req_id, "corrida_id": corrida})
"""

from __future__ import annotations
import json
import logging
import logging.handlers
import re
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from nucleo.settings import settings

_DIR_LOGS = Path(__file__).resolve().parents[1] / "logs"
request_id_context: ContextVar[str] = ContextVar("request_id", default="")

# ── Constantes ─────────────────────────────────────────────────────────────────
_NOMBRE_SERVICIO = "acp-backend"
_LEVEL_COLORES = {
    "DEBUG":    "\033[36m",   # cian
    "INFO":     "\033[32m",   # verde
    "WARNING":  "\033[33m",   # amarillo
    "ERROR":    "\033[31m",   # rojo
    "CRITICAL": "\033[35m",   # magenta
    "RESET":    "\033[0m",
}


class _JsonFormatter(logging.Formatter):
    """
    Emite cada línea de log como un objeto JSON serializado.
    Los campos extra del LogRecord se incluyen automáticamente.
    """

    _CAMPOS_ESTANDAR = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        extra: dict[str, Any] = {
            k: v
            for k, v in record.__dict__.items()
            if k not in self._CAMPOS_ESTANDAR
        }

        entrada = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level":     record.levelname,
            "service":   _NOMBRE_SERVICIO,
            "logger":    record.name,
            "message":   record.message,
        }
        entrada.update(extra)

        if record.exc_info or record.exc_text:
            entrada["exception"] = record.exc_text or _excepcion_segura(record.exc_info)

        return json.dumps(entrada, ensure_ascii=False, default=str)


class _TextoFormatter(logging.Formatter):
    """
    Formato legible para consola en desarrollo.
    Incluye colores ANSI y muestra request_id si está disponible.
    """

    FMT = "{color}[{level:<8}]{reset} {ts} | {logger} | {msg}{extra}"

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        color  = _LEVEL_COLORES.get(record.levelname, "")
        reset  = _LEVEL_COLORES["RESET"]
        ts     = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")

        campos_extra = ["request_id", "corrida_id", "usuario"]
        extra_parts  = [
            f"{k}={record.__dict__[k]}"
            for k in campos_extra
            if k in record.__dict__ and record.__dict__[k]
        ]
        extra_str = "  [" + " ".join(extra_parts) + "]" if extra_parts else ""

        linea = self.FMT.format(
            color=color,
            reset=reset,
            level=record.levelname,
            ts=ts,
            logger=record.name,
            msg=record.message,
            extra=extra_str,
        )

        if record.exc_info or record.exc_text:
            linea += "\n" + (record.exc_text or _excepcion_segura(record.exc_info))
        return linea


def _excepcion_segura(exc_info) -> str:
    """Conservar tipo y ubicaciones sin mensajes/locals/parámetros sensibles."""
    exception_type, _, tb = exc_info
    frames = traceback.extract_tb(tb)
    stack = "".join(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n' for frame in frames)
    return stack + (exception_type.__name__ if exception_type else "Exception")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get() or getattr(record, "request_id", "") or ""
        return True


class _SanitizadorPII(logging.Filter):
    """
    Sanea mensaje, extras anidados y excepciones antes de escribir cualquier sink.
    Los campos sensibles se redactan; DNI/RUC en texto se enmascaran.
    """

    # RUC peruano: 10xxxxxxxxx o 20xxxxxxxxx (11 dígitos)
    _RUC = re.compile(r"\b(1|2)(0\d{9})\b")
    # DNI peruano: exactamente 8 dígitos (no precedidos ni seguidos de dígito)
    _DNI = re.compile(r"(?<!\d)(\d{8})(?!\d)")
    _BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.I)
    _ASIGNACION = re.compile(
        r'''(\b(?:password|passwd|clave(?:_actual|_nueva)?|token|secret|secreto|authorization|api[_-]?key|db_clave|acp_jwt_secreto)\b["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)''',
        re.I,
    )
    _CAMPOS_SENSIBLES = frozenset({
        "password", "passwd", "clave", "token", "secret", "secreto",
        "authorization", "cookie", "credentials", "credenciales", "input", "ctx", "dni", "ruc",
    })

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        # Resolver args antes de sanear conserva los formatos %d/%f.
        try:
            mensaje = record.getMessage()
        except Exception:
            mensaje = "[mensaje de log inválido]"
        record.msg = self._enmascarar(mensaje)
        record.args = None
        for key, value in tuple(record.__dict__.items()):
            if key not in _JsonFormatter._CAMPOS_ESTANDAR:
                record.__dict__[key] = self._sanear(value, key)
        if record.exc_info:
            record.exc_text = _excepcion_segura(record.exc_info)
            record.exc_info = None
        if record.exc_text:
            record.exc_text = self._enmascarar(record.exc_text)
        return True

    def _sanear(self, value: Any, key: str = "") -> Any:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(key).casefold())
        if self._CAMPOS_SENSIBLES.intersection(normalized.split("_")) or "api_key" in normalized:
            return "[REDACTADO]"
        if isinstance(value, dict):
            return {k: self._sanear(v, k) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanear(v) for v in value]
        if isinstance(value, str):
            return self._enmascarar(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        # Evitar repr() arbitrarios que puedan volcar modelos o excepciones.
        return f"<{type(value).__name__}>"

    def _enmascarar(self, texto: str) -> str:
        texto = self._BEARER.sub("Bearer [REDACTADO]", texto)
        texto = self._ASIGNACION.sub(r"\1[REDACTADO]", texto)
        texto = self._RUC.sub(lambda m: m.group(1) + "0" + "*" * 8 + m.group(2)[-1], texto)
        texto = self._DNI.sub(lambda m: m.group(1)[:2] + "****" + m.group(1)[-2:], texto)
        return texto


_sanitizador_pii = _SanitizadorPII()
_request_id_filter = _RequestIdFilter()


def configurar_logging() -> None:
    """
    Configura el logging global del proceso.
    Debe llamarse UNA SOLA VEZ al iniciar el servidor (en lifespan).
    Registra dos handlers: consola (stdout) + archivo rotativo (50 MB, 10 backups).
    """
    nivel = getattr(logging, settings.log_nivel.upper(), logging.INFO)

    if settings.log_formato == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = _TextoFormatter()

    root = logging.getLogger()
    root.setLevel(nivel)

    # Handler consola (sin duplicar)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
               for h in root.handlers):
        consola = logging.StreamHandler(sys.stdout)
        consola.setFormatter(formatter)
        root.addHandler(consola)

    # Handler archivo con rotación (sin duplicar)
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        _DIR_LOGS.mkdir(parents=True, exist_ok=True)
        archivo = logging.handlers.RotatingFileHandler(
            filename=_DIR_LOGS / "backend.log",
            maxBytes=50 * 1024 * 1024,   # 50 MB
            backupCount=10,
            encoding="utf-8",
        )
        archivo.setFormatter(_JsonFormatter())   # archivo siempre JSON para parseo
        root.addHandler(archivo)

    # Los filtros del logger raíz no se aplican a registros de loggers hijos.
    # Incluir handlers preexistentes (p.ej. del servidor) y evitar duplicados.
    for handler in root.handlers:
        handler.addFilter(_request_id_filter)
        handler.addFilter(_sanitizador_pii)

    # Silencia loggers ruidosos de terceros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def obtener_logger(nombre: str) -> logging.Logger:
    """Alias conveniente: from nucleo.logging import obtener_logger."""
    return logging.getLogger(nombre)
