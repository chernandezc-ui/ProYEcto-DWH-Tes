# Correcciones críticas antes del frontend — etapa 1

## Cambios implementados

### Migraciones

`ETL/tools/migration_runner.py` usa `ETL/sql_migrations/manifest.json` como lista explícita. Agregar un `.sql` al directorio ya no lo incorpora al plan. La limpieza total, consultas operativas y el cambio de RCSI están bloqueados en el runner. Baseline y reparaciones históricas se identifican como manuales, fuera de las migraciones incrementales.

El manifiesto mantiene un orden explícito por fases; la definición vegetativa v2 queda después de la original. Este orden no constituye una instalación certificada desde una base vacía. No se alteraron los archivos SQL existentes ni sus hashes.

El runner detecta modificaciones de migraciones ya aplicadas por SHA-256, conserva bloques que empiezan por comentarios y reconoce GO con CRLF, minúsculas y comentarios finales. Respeta literales multilínea y comentarios de bloque. Detiene las siguientes migraciones al primer error. El SQL y su registro de éxito comparten una transacción: si falla la auditoría de éxito, tampoco se confirma la migración. El diagnóstico de error se intenta guardar en otra transacción y su fallo se informa.

Operación: revisar primero `python ETL/tools/migration_runner.py --dry-run`. Un script manual debe evaluarse según su procedimiento propio; no agregarlo al manifiesto para eludir ese procedimiento. Las migraciones previamente registradas que ahora quedan fuera del plan no se revierten ni se vuelven a ejecutar.

### Separación de fundos en proyecciones

La extracción conserva `id_geografia`, `id_variedad` e `id_fundo`. El cálculo agrupa por IDs dimensionales; el censo se cruza por geografía exacta y el lookup de pesos se limita al mismo fundo. El guardado usa los IDs originales y rechaza detalles antiguos que carezcan de ellos. Se eliminó la resolución geográfica mediante TOP 1 por módulo/turno/válvula.

La respuesta mantiene sus campos y añade IDs al detalle. El cruce por geografía exacta es deliberado: no se adjudica automáticamente el censo de otra geografía con etiquetas coincidentes. Si censo y conteo tienen diferente granularidad, puede activarse el fallback de plantas ya existente; definir esa correspondencia y eliminar supuestos silenciosos corresponde a la siguiente revisión del modelo agronómico.

Los problemas previamente detectados de vigencia temporal, validación de matriz y publicación/versionado de simulaciones siguen pendientes. Esta etapa corrige la mezcla de identidad, no certifica el modelo predictivo completo.

### Reproceso por fact

`ETL/utils/reproceso_atomico.py` presta una única conexión a los procesadores y mantiene una transacción exterior para reapertura de Bronce, borrado del destino, carga, cambios de estado y cuarentena. Los contextos internos no confirman ni cierran esa conexión. El homologador también consulta con el recurso recibido, evitando escapar de la transacción.

Ante excepción, breaker ERROR/CRITICO, señal de pérdida silenciosa o reemplazo vacío de una fact no vacía, se revierte la reconstrucción. Se invalida el lookup para no reutilizar IDs creados dentro de una transacción revertida. Las corridas completas conservan su política anterior; la nueva protección aplica a `--modo-ejecucion facts`.

Los reruns ahora son secuenciales: algunas facts comparten tablas Bronce y no deben competir por sus estados. La atomicidad es por fact; una fact exitosa no se revierte porque una posterior falle. Las dependencias previas siguen siendo operaciones separadas. Una reconstrucción vacía intencional requiere otro procedimiento explícito; ya no vacía automáticamente una fact existente.

Esta protección conserva el estado confirmado tras un fallo. No es una versión publicada de todo el DWH: lectores con NOLOCK aún pueden observar cambios no confirmados durante una reconstrucción. El aislamiento de lectura y la publicación coherente de Gold siguen pendientes. Las transacciones más largas también deben medirse sobre SQL Server con volumen real.

### Dependencia de arranque

Se agregó Blinker a ambos requirements porque el backend lo importa en su event bus. En este entorno se descargó una copia aislada en `.test-deps` para verificarlo. Los entornos desplegados necesitan instalar los requirements actualizados con su procedimiento habitual.

## Validación realizada

Resultado: **134 pruebas aprobadas, una omitida**. También pasó `python -m compileall -q ETL backend comun tests`.

Cobertura nueva en `tests/test_critical_safety.py`:

- Manifiesto: limpieza prohibida, archivos no declarados, rutas inválidas y hash modificado.
- Separación GO sin perder SQL detrás de comentarios.
- Parada ante error y transacción conjunta de SQL/auditoría, incluido fallo de auditoría.
- Rollback de destino, Bronce y cuarentena con transacciones SQLite reales.
- Reproceso desde el orquestador real, tanto exitoso como fallido.
- Dos fundos con iguales códigos locales, distintos censos/pesos y persistencia de sus IDs.
- Contrato de extracción y rechazo de persistencia sin identidad dimensional.
- OpenAPI, liveness y ejecución HTTP de proyecciones en memoria, sin conexión a SQL Server.

Comando usado en este entorno Windows:

```powershell
$env:PYTHONPATH = 'D:/DataWareHouse-main/.test-deps'
python -m pytest tests/test_critical_safety.py ETL/tests --ignore=ETL/tests/test_integridad_tablas.py --ignore=ETL/tests/test_flujo_datos.py -q -p no:cacheprovider --basetemp=D:/DataWareHouse-main/.test-tmp-regression-final
```

Se excluyeron dos scripts de integración contra la BD existente; el smoke de ID de origen quedó omitido por su propia condición `ACP_TEST_DB`. Las pruebas se ejecutaron fuera del sandbox por el socket interno que requiere asyncio en Windows. No se ejecutaron migraciones ni escrituras sobre SQL Server.

## Validación pendiente sobre SQL Server aislado

1. Revisar el plan y el registro de hashes frente al DWH desplegado.
2. Ejecutar una carga y un rerun de una fact representativa con el driver real.
3. Inducir un fallo de carga y comprobar que fact/estados/cuarentena vuelven al estado anterior.
4. Consultar dos fundos con códigos locales iguales y verificar IDs y totales guardados.
5. Medir bloqueos, tiempo y uso del log de transacciones durante reconstrucciones grandes.

Hasta completar ese ensayo, la validación lograda es local y automatizada; no equivale a una certificación end-to-end del despliegue real.
