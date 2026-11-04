"""
nucleo/api_response.py
======================
Estandarización de respuestas HTTP para todo el backend.
Garantiza un formato predecible para el consumido (Frontend).
"""

from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class StandardResponse(BaseModel, Generic[T]):
    """
    Envoltorio universal para todas las respuestas de la API.
    Asegura un contrato estricto con el consumidor.
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": 1, "nombre": "Ejemplo"},
                "error": None,
                "metadata": {"timestamp": "2026-04-16T12:00:00Z", "version": "1.1.0"}
            }
        }
    )

    @classmethod
    def ok(cls, data: T, metadata: Optional[dict[str, Any]] = None) -> "StandardResponse[T]":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error_msg: str, metadata: Optional[dict[str, Any]] = None) -> "StandardResponse[Any]":
        return cls(success=False, data=None, error=error_msg, metadata=metadata)
