# Pruebas locales e integración SQL Server

Desde la raíz del repositorio, con los requirements instalados:

```bash
python -m pytest -q
```

El `pytest.ini` raíz descubre `tests/`, `ETL/tests/` y `backend/tests/`.
No es necesario excluir el procesador de censo ni pasar listas de archivos.
Los scripts operativos de `ETL/` y `ETL/tools/` no forman parte de ese
descubrimiento. Sus nombres históricos no implican que sean pruebas unitarias.
Las herramientas conservan sus rutas CLI; ejecutarlas manualmente puede leer
o escribir en la instancia configurada. Las de inspección Bronce y carga de
fisiología ya no ejecutan operaciones al importarse.

La política es común también al ejecutar `python -m pytest` desde `backend/`;
en ese caso se seleccionan sus pruebas de backend. Para ejecutar toda la suite,
usar el comando desde la raíz. Para limitarla desde la raíz, usar
`python -m pytest backend/tests`.

En la ejecución local:

- Se establece un destino `offline-test` y un JWT efímero para el proceso de
  pruebas; no se modifican `.env` ni las variables del proceso que lo invocó.
- Se bloquean las conexiones reales mediante pyodbc y el dialecto MSSQL/pyodbc
  de SQLAlchemy desde antes de importar los módulos de prueba. SQLite temporal
  sigue disponible para probar transacciones reales sin SQL Server.
- Las pruebas marcadas `sqlserver` se reportan como **omitidas**, no aprobadas.
  La antigua variable `ACP_TEST_DB=1` no habilita el acceso SQL en pytest.
- `ACP_ENTORNO=test` por sí solo no proporciona una base mock: la conexión
  común de la aplicación sigue siendo SQL Server fuera de estas protecciones
  específicas de pytest.

La regresión de importación arranca un proceso Python nuevo y comprueba que
importar el pipeline no crea un engine SQL ni inicia la carga Bronce. Otras
regresiones verifican el descubrimiento, bloqueo de conexiones, permisos de
integración, destino efectivo y propagación de fallos en herramientas manuales.

Para revisar la colección sin ejecutar las pruebas:

```bash
python -m pytest --collect-only -q
```

## Integración SQL Server, solo con una base aislada disponible

No se ejecutó esta integración durante el cambio. Cuando exista una instancia
de prueba y sus prerrequisitos de esquema/datos/ODBC, puede habilitarse con:

```bash
python -m pytest -m sqlserver --run-sqlserver \
  --sqlserver-server '<servidor-de-prueba>' \
  --sqlserver-database ACP_TEST_<identificador>
```

El servidor y la base son obligatorios y sustituyen el destino heredado solo
dentro del proceso pytest. La base debe tener un nombre completo que comience
por `ACP_TEST_` o `ACP_E2E_`, seguido de letras, números o guiones bajos.
Antes de las fixtures de integración se consulta `DB_NAME()` y se comprueba
que coincide con el destino solicitado. La verificación no crea ni borra bases,
ni ejecuta migraciones. Un nombre con ese prefijo no crea aislamiento por sí
solo: utilizar una base dedicada y credenciales con permisos limitados a ella.
Configurar las credenciales mediante el mecanismo seguro del entorno; no
incluir contraseñas en comandos ni en archivos versionados.

Las pruebas de catálogo necesitan geografías de muestra; el smoke de Bronce
requiere la tabla `Bronce.Peladas`. El harness por etapas de
`tests/integration/sqlserver_e2e.py` conserva su CLI y sus protecciones propias;
no se inicia automáticamente mediante pytest.

Al agregar una prueba que necesita SQL Server, marcarla con
`@pytest.mark.sqlserver` (o `pytestmark` a nivel de módulo) y usar la fixture
`sqlserver_engine`/`engine`. Mantener las pruebas unitarias sin ese marcador.
No agregar configuración pytest duplicada en subcarpetas ni quitar aserciones
para lograr una ejecución satisfactoria.
