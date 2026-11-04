# Validación real con SQL Server aislado

Fecha local: 3 de noviembre de 2026 (America/Lima).

## Resultado

**El recorrido funcional probado pasó sobre SQL Server real, con ODBC y procesos HTTP/runner reales, sin mocks.** Se validaron cuatro dominios con datos sintéticos no vacíos: conteo, censo, pesos y poda. El pipeline completo ejecutó además los demás procesadores con entradas vacías.

La instalación desde cero **no queda certificada**. El snapshot y la secuencia histórica contienen incompatibilidades; para probar el funcionamiento se construyó un esquema de prueba con reparaciones explícitas, descritas abajo. Esas reparaciones no se aplicaron a la base actual.

Evidencia estructurada, sin credenciales: [validacion-sqlserver-aislado-resultados.json](./validacion-sqlserver-aislado-resultados.json).

## Aislamiento

- Instancia: `localhost\LOCALHOST`.
- Base nueva: `ACP_E2E_20261104_005725_b1f328`. El nombre utiliza UTC; la ejecución corresponde al 3 de noviembre en Lima.
- SQL Server Developer, conexión mediante ODBC Driver 17.
- Se creó un login SQL exclusivo para esa base, con rol `db_owner` allí y **sin rol sysadmin**. La comprobación de acceso a la base habitual no devolvió acceso disponible.
- La administración inicial se conectó únicamente a `master` para crear la base y su login. Las cargas y aplicaciones se conectaron exclusivamente a `ACP_E2E_*`.
- Los scripts comprueban el nombre de la base y rechazan otros destinos. Los `USE` históricos se redirigen en memoria al destino aislado y se validan antes de ejecutarse.
- Se copió el código a `.test-tmp-sqlserver/workspace`; los Excel, archivos procesados y logs quedaron dentro de esa copia. No se utilizaron archivos ni datos productivos.
- No se cambiaron `.env` existentes. Las credenciales de prueba se generaron al azar y se pasaron a los subprocesos mediante su entorno.

La base sintética se conserva para inspección. El backend HTTP y el runner temporales se cerraron al terminar; no quedaron corridas activas, locks adquiridos ni triggers de fallo.

## Pruebas ejecutadas

| Prueba | Resultado observado |
|---|---|
| Excel → Bronce → Silver → Gold | 2 registros de conteo, 2 de censo, 12 de pesos y 2 de poda; Gold consultable |
| Dos fundos con los mismos números de módulo/turno/válvula | Geografías separadas; cantidades de órganos 100 y 200 |
| Segunda corrida incremental | Datos de las cuatro facts idénticos antes/después, sin duplicados |
| HTTP real y autenticación | Uvicorn en localhost con puerto temporal, login contra SQL, JWT, perfil y readiness correctos; petición anónima protegida devuelve 401 |
| Proyección por HTTP | 12 filas de detalle, seis por geografía; W1 = 3 kg para A y 16 kg para B, usando los datos sintéticos definidos |
| Persistencia de proyección | Dos geografías diferentes, seis registros por cada una, con IDs y totales correctos |
| API → cola SQL → runner → subproceso ETL | Reproceso de conteo termina en OK; siete pasos persistidos |
| SSE | Eventos de log y cierre `[FIN_CORRIDA]` recibidos por HTTP |
| Fallo SQL real durante reconstrucción | Un trigger temporal rechaza INSERT después del borrado; corrida ERROR y conservación exacta de fact, Bronce y cuarentena |
| Recuperación | Retirado el trigger, un nuevo reproceso termina en OK |
| Corrida completa desde API | Finaliza en OK mediante el runner real |
| Migración correcta | SQL detrás de comentarios y separadores GO se ejecuta; registro de éxito confirmado |
| Error diferido ODBC | Se detecta el error de un resultado posterior y se revierte el INSERT del mismo batch |
| Error al auditar éxito de migración | Trigger temporal rechaza el registro OK; SQL de la migración revertido y registro ERROR guardado |
| Integridad final | DBCC CHECKCONSTRAINTS sin violaciones; cero FK deshabilitadas o no confiables |

La prueba de rollback compara filas completas, incluyendo sus IDs y estados, antes y después del fallo. No se limita a contar registros ni a comprobar el código de salida.

## Correcciones adicionales descubiertas con datos reales

### Normalización de fundos en el ETL

La separación corregida en el backend no bastaba: el ETL podía colapsar la identidad antes de llegar a Silver.

El normalizador operativo extraía el único número de un nombre. Por ejemplo, `E2E_A` y `E2E_B` acababan como `2`. Además, el mapa genérico de catálogo normalizaba de otra forma. La búsqueda podía perder los filtros de fundo/sector y seleccionar la geografía con menor ID.

Se modificaron `ETL/mdm/lookup.py` y `ETL/silver/facts/_base_processor.py` para:

- Conservar el nombre completo de fundo y sector, normalizando espacios y mayúsculas/minúsculas.
- Usar la misma normalización en los valores recibidos y en los catálogos.
- Impedir que un fundo o sector desconocido se transforme en una búsqueda sin ese filtro.
- Rechazar geografías ambiguas en lugar de elegir el menor ID.

La carga real posterior produjo las dos geografías esperadas y los resultados distintos de proyección.

### Errores diferidos del driver ODBC

Se reforzó `ETL/tools/migration_runner.py`: tanto los batches SQL como la escritura de auditoría consumen todos los resultados del cursor en la misma transacción. ODBC puede entregar un error en `nextset()` / SQLMoreResults; ignorarlo permite confirmar SQL que debió fallar.

La nueva protección se verificó con `RAISERROR` y con un trigger de fallo de auditoría sobre SQL Server real. Ambas pruebas conservaron únicamente los valores previamente confirmados.

### Dependencia de lectura Excel

El cargador usa explícitamente `engine='calamine'`, pero `python-calamine` no estaba declarado ni instalado en el entorno. Se agregó a ambos requirements y se instaló una copia aislada en `.test-deps`. Los entornos desplegados necesitan instalar los requirements actualizados.

## Problemas de instalación detectados

Estos hallazgos siguen pendientes de consolidación en un baseline de despliegue. No se ocultaron bajo un resultado global de instalación satisfactoria:

1. El DDL exportado contiene procedimientos antiguos que referencian columnas inexistentes en las tablas del propio snapshot. Se instalaron sus tablas, índices y FK, los módulos vigentes de Control y sincronización, y las definiciones actuales de MDM/camas/Gold desde scripts seleccionados.
2. El snapshot omite columnas de campaña requeridas por fase46 y contratos actuales de censo, pesos, poda y otros dominios. El complemento aislado está declarado en `tests/integration/schema_prerequisites.sql`.
3. La fase50 histórica presupone columnas y datos de una etapa anterior; no es una inicialización de condiciones sobre el snapshot vacío. Se dejó fuera del plan de prueba y se sembraron condiciones sintéticas.
4. La fase66 intenta eliminar `Categoria` antes de retirar el índice que depende de ella. El bootstrap aislado retira ese índice explícitamente; fase69 crea el índice vigente.
5. Los scripts de conversión Gold usan `DROP VIEW IF EXISTS` sobre tablas y `DROP TABLE IF EXISTS` sobre vistas. SQL Server rechaza la operación por tipo de objeto. El bootstrap de prueba verifica `OBJECT_ID` y tipo antes del DROP en el texto de ejecución, sin modificar los archivos históricos.
6. La fase68 está desfasada respecto de la eliminación de columnas previa; se utilizó la definición Gold consolidada de fase70.
7. El refactor horario de clima está en `ETL/sql`, fuera del recorrido de migraciones. Se incorporó explícitamente al bootstrap aislado.
8. El usuario restringido no tiene permisos para inspeccionar sesiones de servidor; el intento opcional de limpiar sesiones huérfanas se omite con aviso. El ETL y el runner completaron sus operaciones sin ampliar permisos de servidor.

El código del ETL puede terminar con código cero aunque una muestra pequeña tenga rechazos, por el mínimo de muestra del breaker. Por eso la validación exige cantidades y valores concretos, no solo `exit 0`.

## Regresión y reproducibilidad

Después de las correcciones adicionales: **138 pruebas locales aprobadas, una omitida**, y compilación sintáctica correcta. La omitida requiere habilitación explícita de una prueba de BD. Las suites que usan la base de desarrollo permanecieron excluidas.

Herramientas añadidas:

- `tests/integration/sqlserver_e2e.py`: creación y preparación aislada, generación de Excel, ejecución y validación HTTP/runner/rollback, integridad final e informe.
- `tests/integration/sqlserver_worker.py`: migraciones reales y sus fallos transaccionales con ODBC.
- `tests/integration/schema_prerequisites.sql`: diferencias explícitas entre el snapshot y el contrato actual usadas únicamente en el fixture aislado.
- Pruebas de regresión nuevas en `tests/test_critical_safety.py` para nombres de fundos, geografía desconocida/ambigua y errores ODBC diferidos.

Secuencia prevista para un entorno de prueba nuevo, desde la raíz del proyecto, con permisos para crear bases en la instancia local y las dependencias instaladas:

```powershell
python tests/integration/sqlserver_e2e.py setup
python tests/integration/sqlserver_e2e.py prepare
python tests/integration/sqlserver_e2e.py seed
python tests/integration/sqlserver_e2e.py pipeline
python tests/integration/sqlserver_e2e.py validate
python tests/integration/sqlserver_e2e.py final-check
```

El archivo de estado local contiene credenciales de prueba y queda excluido por `.gitignore`; no debe compartirse. El informe JSON entregado contiene resultados, IDs de corridas y hashes del código, sin contraseñas ni tokens.

## Límites y siguiente trabajo

La validación demuestra el recorrido funcional representativo y las protecciones críticas sobre el driver real. No demuestra rendimiento a volumen productivo, todos los layouts agrícolas, todos los roles ni datos no vacíos en las otras once facts. Tampoco resuelve la publicación coherente de todo Gold o las lecturas con NOLOCK.

Antes del frontend definitivo, el siguiente trabajo es consolidar un baseline instalable que incluya los contratos actuales y reemplace la secuencia histórica incompatible, conservando los hashes de migraciones ya aplicadas.
