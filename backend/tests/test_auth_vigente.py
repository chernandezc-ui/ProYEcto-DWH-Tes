"""Autorización HTTP real con JWT firmado y usuario de BD sintético."""

from unittest.mock import Mock

from fastapi import Depends, FastAPI
import httpx
from jose import jwt
import pytest

from nucleo import auth


@pytest.fixture
def protected_app():
    app = FastAPI()

    @app.get("/admin")
    def admin(user=Depends(auth.require_rol("admin"))):
        return {"rol": user.rol, "nombre_display": user.nombre_display}

    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("token_role,current_role,code", [
    ("admin", "viewer", 403),
    ("viewer", "admin", 200),
    ("admin", "admin", 200),
    ("admin", "desconocido", 403),
])
async def test_permisos_y_display_provienen_del_usuario_vigente(protected_app, monkeypatch, token_role, current_role, code):
    lookup = Mock(return_value={"nombre_usuario": "synthetic", "nombre_display": "Vigente", "rol": current_role})
    monkeypatch.setattr(auth.repo_usuarios, "buscar_por_nombre", lookup)
    token = auth.crear_token("synthetic", token_role, "Anterior")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=protected_app), base_url="http://test") as client:
        response = await client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == code
    lookup.assert_called_once_with("synthetic")
    if code == 200:
        assert response.json() == {"rol": current_role, "nombre_display": "Vigente"}


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["inactivo", "expirado", "firma_invalida", "sin_sujeto"])
async def test_sesiones_no_validas_siguen_rechazadas(protected_app, monkeypatch, mode):
    lookup = Mock(return_value=None)
    monkeypatch.setattr(auth.repo_usuarios, "buscar_por_nombre", lookup)
    token = auth.crear_token("synthetic", "admin", "Synthetic", ttl_minutos=-1 if mode == "expirado" else 5)
    if mode == "firma_invalida":
        token = jwt.encode({"sub": "synthetic", "rol": "admin"}, "synthetic-unrelated-signing-key", algorithm="HS256")
    elif mode == "sin_sujeto":
        token = jwt.encode({"rol": "admin"}, auth.settings.jwt_secreto, algorithm=auth.settings.jwt_algoritmo)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=protected_app), base_url="http://test") as client:
        response = await client.get("/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    if mode != "inactivo":
        lookup.assert_not_called()
