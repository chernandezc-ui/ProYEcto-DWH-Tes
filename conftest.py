"""Política común: pruebas locales por defecto, SQL Server solo bajo opt-in."""

import re
import secrets

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("sqlserver")
    group.addoption("--run-sqlserver", action="store_true", help="Ejecutar integración SQL Server")
    group.addoption("--sqlserver-server", help="Servidor de la instancia de prueba")
    group.addoption("--sqlserver-database", help="Base aislada ACP_TEST_* o ACP_E2E_*")


def pytest_configure(config):
    enabled = config.getoption("--run-sqlserver")
    server = config.getoption("--sqlserver-server")
    database = config.getoption("--sqlserver-database")
    if enabled:
        if not server or not server.strip() or any(c in server for c in ";\r\n"):
            raise pytest.UsageError("--run-sqlserver requiere --sqlserver-server explícito")
        if not database or not re.fullmatch(r"ACP_(?:TEST|E2E)_[A-Za-z0-9_]+", database):
            raise pytest.UsageError("--sqlserver-database debe ser una base aislada ACP_TEST_* o ACP_E2E_*")
    elif server or database:
        raise pytest.UsageError("Los destinos SQL requieren --run-sqlserver")

    patches = pytest.MonkeyPatch()
    config.add_cleanup(patches.undo)
    # No heredar el destino de desarrollo/producción ni usar el JWT de la aplicación.
    patches.setenv("DB_SERVIDOR", server if enabled else "offline-test")
    patches.setenv("DB_NOMBRE", database if enabled else "offline-test")
    patches.setenv("ACP_ENTORNO", "test")
    patches.setenv("ACP_JWT_SECRETO", secrets.token_urlsafe(48))
    if not enabled:
        def deny_sqlserver(*args, **kwargs):
            raise RuntimeError("SQL Server bloqueado en pruebas locales; use --run-sqlserver con destino aislado")

        # Proteger también llamadas accidentales durante la colección/importación.
        patches.setattr("sqlalchemy.dialects.mssql.pyodbc.MSDialect_pyodbc.connect", deny_sqlserver)
        patches.setattr("pyodbc.connect", deny_sqlserver)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-sqlserver"):
        skip = pytest.mark.skip(reason="Integración SQL Server no habilitada (--run-sqlserver)")
        for item in items:
            if item.get_closest_marker("sqlserver"):
                item.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def sqlserver_engine(request):
    """Comprobar el destino efectivo antes de cualquier fixture/prueba SQL."""
    if not request.config.getoption("--run-sqlserver"):
        return None
    if not any(item.get_closest_marker("sqlserver") for item in request.session.items):
        return None

    from comun.conexion import obtener_engine

    engine = obtener_engine()
    with engine.connect() as connection:
        actual = connection.exec_driver_sql("SELECT DB_NAME()").scalar_one()
    if actual != request.config.getoption("--sqlserver-database"):
        pytest.fail("SQL Server devolvió una base distinta del destino de prueba solicitado")
    return engine
