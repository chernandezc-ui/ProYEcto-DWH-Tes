"""Ejercita el servicio con caché SQLite real y un repositorio SQL sustituido."""

from unittest.mock import Mock

import pytest

import nucleo.cache as cache_module
from servicios import servicio_cuarentena as service


@pytest.fixture
def local_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_module, "DB_PATH", str(tmp_path / "cache.db"))
    cache = cache_module.CacheAlpha()
    monkeypatch.setattr(service, "cache", cache)
    yield cache
    cache._local.conn.close()


@pytest.mark.asyncio
async def test_estado_pagina_y_tabla_tienen_entradas_independientes(local_cache, monkeypatch):
    read = Mock(side_effect=lambda **filters: {"filtros": filters})
    monkeypatch.setattr(service.repo, "listar_pendientes", read)
    queries = [
        (1, 20, None, "PENDIENTE"),
        (1, 20, None, "RESUELTO"),
        (1, 20, None, "DESCARTADO"),
        (1, 20, None, None),
        (1, 20, "todos", None),
        (2, 20, None, "PENDIENTE"),
        (1, 10, None, "PENDIENTE"),
    ]
    for page, size, table, state in queries:
        expected = {"pagina": page, "tamano": size, "tabla_filtro": table, "estado_filtro": state}
        for _ in range(2):
            response = await service.listar_cuarentena(page, size, table, state)
            assert response["filtros"] == expected
    assert read.call_count == len(queries)
    assert local_cache.limpiar_por_prefijo("cuarentena:") == len(queries)
    await service.listar_cuarentena()
    assert read.call_count == len(queries) + 1


@pytest.mark.asyncio
async def test_no_reutiliza_entradas_del_formato_anterior(local_cache, monkeypatch):
    local_cache.guardar("cuarentena:listar:p1:t20:ftodos", {"estado": "incorrecto"})
    monkeypatch.setattr(service.repo, "listar_pendientes", lambda **kw: {"estado": kw["estado_filtro"]})
    assert await service.listar_cuarentena(estado_filtro="RESUELTO") == {"estado": "RESUELTO"}
