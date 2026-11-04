"""Validación HTTP, concurrencia y sinks reales de logging con datos sintéticos."""

import asyncio
import io
import json
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
import httpx
import pytest

from nucleo import logging as app_logging
from nucleo.excepciones import manejar_error_validacion
from nucleo.middleware import RequestIdMiddleware
from schemas.auth.peticion import PeticionLogin


@pytest.fixture(params=["json", "texto"])
def log_sinks(tmp_path, monkeypatch, request):
    root = logging.getLogger()
    output = io.StringIO()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", root.level)
    monkeypatch.setattr(app_logging.sys, "stdout", output)
    monkeypatch.setattr(app_logging, "_DIR_LOGS", tmp_path)
    monkeypatch.setattr(app_logging.settings, "log_formato", request.param)
    app_logging.configurar_logging()
    # Repetir configuración no debe duplicar handlers ni filtros.
    app_logging.configurar_logging()
    yield output, tmp_path / "backend.log"
    for handler in root.handlers:
        handler.close()


def emitted(sinks):
    output, path = sinks
    return output.getvalue() + path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_422_registra_diagnostico_sin_inputs_ni_contexto_sensible(log_sinks):
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, manejar_error_validacion)

    @app.post("/login")
    def login(body: PeticionLogin):
        raise AssertionError("Payload inválido no debe llegar al endpoint")

    secret = "synthetic-password-never-log"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/login", json={"nombre_usuario": "synthetic", "clave": {"nested": secret}})
    assert response.status_code == 422
    text = emitted(log_sinks)
    assert secret not in text
    rows = [json.loads(line) for line in log_sinks[1].read_text().splitlines()]
    error = next(row for row in rows if "errores_pydantic" in row)
    assert error["errores_pydantic"] == [{"loc": ["body", "clave"], "type": "string_type"}]


def test_sanea_extras_anidados_mensaje_y_excepcion(log_sinks):
    logger = logging.getLogger("tests.security.child")
    secrets = ["synthetic-pass", "synthetic-token", "synthetic-input", "synthetic-exception"]
    try:
        raise ValueError(secrets[3])
    except ValueError:
        logger.exception(
            "fallo password=%s Authorization=Bearer %s DNI=12345678", secrets[0], secrets[1],
            extra={"payload": [{"clave_nueva": secrets[0], "Authorization": secrets[1], "input": secrets[2], "nota": "DNI 12345678"}]},
        )
    text = emitted(log_sinks)
    for value in secrets + ["12345678"]:
        assert value not in text
    assert "ValueError" in text
    assert "test_sanea_extras" in text


def test_handler_preexistente_tambien_sanea_y_no_muta_payload(log_sinks):
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    logging.getLogger().addHandler(handler)
    app_logging.configurar_logging()
    payload = {"clave": "synthetic-preexisting-secret", "rows": 3}
    logging.getLogger('tests.preexisting.child').warning('fila %d', 3, extra={"payload": payload})
    assert 'synthetic-preexisting-secret' not in output.getvalue()
    assert payload['clave'] == 'synthetic-preexisting-secret'
    assert 'fila 3' in output.getvalue()


def test_mensaje_mal_formado_no_vuelca_argumentos(log_sinks):
    logging.getLogger('tests.malformed.child').warning('entero %d', 'synthetic-malformed-secret')
    text = emitted(log_sinks)
    assert 'synthetic-malformed-secret' not in text
    assert 'mensaje de log inválido' in text


@pytest.mark.asyncio
async def test_error_restaurar_contexto_previo(log_sinks):
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    logger = logging.getLogger('tests.error.child')

    @app.get('/error')
    async def endpoint():
        logger.warning('inside-error')
        raise RuntimeError('synthetic-handler-error')

    token = app_logging.request_id_context.set('parent-context')
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            with pytest.raises(RuntimeError, match='synthetic-handler-error'):
                await client.get('/error', headers={'X-Request-ID': 'child-context'})
        logger.warning('after-error')
    finally:
        app_logging.request_id_context.reset(token)
    rows = [json.loads(line) for line in log_sinks[1].read_text().splitlines()]
    assert [(r['message'], r['request_id']) for r in rows if r['logger'] == logger.name] == [
        ('inside-error', 'child-context'), ('after-error', 'parent-context'),
    ]


@pytest.mark.asyncio
async def test_requests_concurrentes_y_threadpool_no_mezclan_request_id(log_sinks):
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    first_ready, second_ready = asyncio.Event(), asyncio.Event()
    logger = logging.getLogger("tests.requests.child")

    @app.get("/{name}")
    async def endpoint(name: str):
        if name == "A":
            first_ready.set()
            await second_ready.wait()
        else:
            await first_ready.wait()
            second_ready.set()
        logger.warning("request %s", name)
        await asyncio.to_thread(logger.warning, "thread %s", name)
        return {"name": name}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        responses = await asyncio.gather(*[
            client.get(f"/{name}", headers={"X-Request-ID": f"request-{name}"}) for name in ("A", "B")
        ])
    assert [response.headers["X-Request-ID"] for response in responses] == ["request-A", "request-B"]
    logger.warning("outside")
    rows = [json.loads(line) for line in log_sinks[1].read_text().splitlines()]
    own = [row for row in rows if row["logger"] == logger.name]
    assert len(own) == 5
    for row in own:
        expected = "" if row["message"] == "outside" else f"request-{row['message'][-1]}"
        assert row.get("request_id") == expected
