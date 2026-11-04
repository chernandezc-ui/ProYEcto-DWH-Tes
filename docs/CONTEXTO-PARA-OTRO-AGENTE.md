# Traspaso de contexto: ACP / DataWareHouse

Fecha de corte: 3 de noviembre de 2026, America/Lima. Documento preparado para continuar el trabajo sin acceso a la memoria del chat. Es un registro de lo realizado y de las propuestas; no certifica que el entorno siga en el mismo estado después de esta fecha.

## 1. Objetivo del usuario y alcance vigente

El usuario quiere comprender, depurar y refactorizar profundamente el ETL y el backend antes de construir el frontend. Pidió proteger migraciones, corregir la mezcla de fundos y el reproceso, y verificar el recorrido real en una base SQL Server aislada. Esas correcciones y las pruebas descritas abajo ya se realizaron.

Después pidió una propuesta completa de refactor y depuración, con mapas de nodos usando https://github.com/tt-a1i/archify. La auditoría y los mapas están entregados. **Las 36 acciones del refactor siguen siendo propuestas; no asumir que se implementaron.**

La última conversación trató sobre SQL Server frente a Parquet para Bronce. El usuario aceptó la recomendación y pidió guardar todo el contexto en este Markdown. No pidió migrar almacenamiento, borrar temporales ni empezar a implementar el backlog en este último intercambio.

## 2. Entorno y precauciones operativas

- Copia local: `D:\DataWareHouse-main`, PowerShell en Windows.
- Núcleo: Python, SQL Server, SQLAlchemy/ODBC, FastAPI y procesamiento Excel.
- No se encontró metadata Git en esta copia durante la auditoría; no inventar commits, diffs o ramas del proyecto.
- No modificar la base habitual para validar cambios. Usar destinos aislados, comprobar servidor/base efectivos y conservar rollback.
- No publicar credenciales ni copiar `.env` o archivos de estado sensibles a informes.
- La configuración efectiva de conexiones tiene deuda: Settings y `os.getenv` no siempre comparten la misma ruta. Verificar el destino de cada proceso antes de ejecutar herramientas.
- El usuario prefiere avanzar de forma autónoma en el alcance autorizado, sin confirmaciones repetidas. Eso no equivale a autorización para borrar datos o ejecutar mantenimiento destructivo en la base habitual.

## 3. Arquitectura y flujo actual

El repositorio contiene ETL, backend, módulos comunes y documentación. No se encontró un frontend funcional; algunas menciones previas a un portal Next en documentos no describen una implementación presente.

1. Se reciben Excel en 23 carpetas de entrada asociadas a un catálogo de 15 procesadores de facts.
2. Bronce interpreta layouts especializados con soporte de `python-calamine`. Guarda valores de origen como texto, `Valores_Raw`, metadatos de fuente y estados de carga. Se archivan originales.
3. La selección de pendientes depende de tamaño/mtime y toma el último archivo por carpeta. No hay todavía un contrato general de cola durable por contenido para múltiples entregas.
4. MDM normaliza geografía, catálogos, variedades, personal y otras identidades. Silver aplica transformaciones, dimensiones/SCD2, campaña/poda, deduplicación y cuarentena.
5. Gold se apoya actualmente en vistas SQL. Las operaciones llamadas refresh consultan/cuentan; algunas llamadas truncate son no-op. No existe todavía una publicación versionada que congele todas las métricas oficiales.
6. FastAPI expone autenticación, catálogos, consultas analíticas, proyecciones, cuarentena y control del ETL.
7. La API registra comandos/corridas en SQL. Un runner separado toma la cola, usa locks/heartbeat, ejecuta el ETL como subproceso y persiste eventos. SSE consulta esos eventos.
8. Las proyecciones calculan seis semanas leyendo Silver y guardan en `Silver.Fact_Proyecciones`. No asumir que todo el backend consume exclusivamente Gold.

Conservar la arquitectura general durante el refactor. No se propuso reescribir todo, introducir microservicios ni sustituir simultáneamente SQL Server, FastAPI y el runner.

## 4. Cambios críticos ya implementados

### Migraciones

En `ETL/tools/migration_runner.py` y `ETL/sql_migrations/manifest.json`:

- Ejecución gobernada por manifiesto explícito; scripts históricos/manuales, consultas y mantenimiento peligroso no se ejecutan indiscriminadamente.
- Protección frente a `clear_all_data.sql` y exclusión del cambio RCSI de fase 71 del flujo automático.
- SHA para detectar cambios en migraciones ya aplicadas; detención ante el primer fallo.
- Separación GO consciente de comentarios, cadenas y finales de línea.
- SQL y registro de éxito en una misma transacción; registro de error en una transacción separada.
- Consumo de resultados posteriores con cursor DBAPI/`nextset()` para detectar errores diferidos de ODBC, tanto en SQL como en la auditoría de éxito.

**Límite:** un ejecutor protegido no resuelve la incompatibilidad histórica del esquema. Falta un baseline instalable y reproducible.

### Identidad de fundos y proyecciones

- Se preservan `id_geografia`, `id_variedad` e `id_fundo` en extracción, agrupación y persistencia.
- Censo se vincula con geografía exacta; pesos respetan el fundo.
- Se retira la elección de identidad mediante TOP 1 usando solo números locales de módulo/turno/válvula. Los detalles antiguos sin IDs no se aceptan como si fueran inequívocos.
- La prueba real descubrió además colisión en el ETL: el normalizador operativo extraía el número 2 de `E2E_A` y `E2E_B`.
- En `ETL/mdm/lookup.py` y `ETL/silver/facts/_base_processor.py`, fundo/sector conservan el nombre completo normalizado; valores desconocidos no eliminan filtros y las coincidencias ambiguas se rechazan en vez de tomar el menor ID.

### Reproceso atómico

- `ETL/utils/reproceso_atomico.py` y el contexto transaccional prestan una conexión compartida mediante un adaptador `EngineTransaccional`.
- Por fact, la reapertura de Bronce, eliminación del destino Silver y transformaciones de estados/cuarentena se coordinan dentro de la misma transacción.
- Se revierte ante excepción, breaker ERROR/CRITICO, pérdida silenciosa o reemplazo vacío de un destino que tenía datos, según las comprobaciones implementadas.
- Los reprocesos parciales se serializan porque existen fuentes Bronce compartidas.
- `ETL/pipeline.py` usa el envoltorio; el homologador respeta el recurso suministrado.
- La adaptación probada cubre el recorrido actual; a futuro se propone inyectar `Connection`/unidad de trabajo explícita para evitar que métodos heredados abran otra conexión.

Se añadieron `blinker` y `python-calamine` a las dependencias necesarias. Leer los informes y el código antes de modificar estos mecanismos.

## 5. Validación real ejecutada y límites

La regresión registrada fue de **138 pruebas aprobadas y una omitida**. Después se ejecutó un ensayo con SQL Server, ODBC, servidor HTTP y runner reales.

Destino del ensayo:

- Instancia `localhost\LOCALHOST`, SQL Server Developer, ODBC Driver 17.
- Base sintética `ACP_E2E_20261104_005725_b1f328` (sufijo UTC; fecha local del ensayo: 3 de noviembre).
- Login exclusivo con `db_owner` solo en esa base, sin sysadmin. El ensayo no operó contra la base habitual.
- Copia de trabajo aislada en `.test-tmp-sqlserver/workspace`; Excel y credenciales sintéticos, entorno de subprocesos dedicado y sin cambiar los `.env` originales.
- El host habitual configurado `LCP-PAG-PRACTIC` no estaba disponible en ese ensayo.

Resultados observados:

| Recorrido | Evidencia |
|---|---|
| Excel → Bronce → Silver → Gold | Conteo: 2 filas; censo: 2; pesos: 12; poda: 2; vistas Gold consultables |
| Separación entre fundos | Dos geografías con números locales iguales conservaron órganos 100 y 200 |
| Incremental repetido | Mismas facts, sin duplicación en los cuatro dominios |
| Autenticación HTTP | Login/JWT/perfil/readiness correctos; acceso anónimo protegido devuelve 401 |
| Proyección HTTP y persistencia | 12 detalles, seis por geografía; primera semana: 3 kg para A y 16 kg para B |
| API → SQL → runner → ETL | Reproceso de conteo OK; siete pasos persistidos; SSE recibió cierre |
| Fallo SQL inducido | Trigger rechazó INSERT después de DELETE; rollback conservó filas completas, IDs y estados de fact, Bronce y cuarentena |
| Recuperación y ejecución completa | Corridas posteriores OK tras retirar el trigger |
| Migraciones | Éxito; error ODBC diferido revierte; fallo al registrar éxito también revierte el SQL |
| Integridad final | DBCC CHECKCONSTRAINTS sin violaciones; cero FK deshabilitadas/no confiables; sin corridas activas, locks adquiridos ni triggers temporales |

**No equivale a cobertura funcional completa:** solo cuatro dominios tuvieron datos no vacíos; los otros once procesadores se ejecutaron con entradas vacías. Tampoco quedó certificada la instalación desde cero: el esquema aislado necesitó prerrequisitos y reparaciones documentadas. No trasladar esos parches a la base actual sin convertirlos antes en un plan de migración revisable.

Al finalizar se cerraron backend y runner temporales. La base sintética se conservó. Su existencia y estado deben comprobarse de nuevo antes de reutilizarla.

Herramientas conservadas:

- `tests/integration/sqlserver_e2e.py`: orquestación por etapas, aislamiento y comprobaciones.
- `tests/integration/sqlserver_worker.py`: tareas dentro del entorno aislado.
- `tests/integration/schema_prerequisites.sql`: soporte del esquema de prueba; no constituye el baseline definitivo.
- `.test-tmp-sqlserver/state.json`: puede contener credenciales de prueba; no publicarlo ni incorporarlo al contexto compartido.

## 6. Auditoría integral: dictamen y deuda principal

El sistema funciona en los recorridos probados, pero conserva deuda importante. Una ejecución con código de salida exitoso no demuestra integridad de las reglas de negocio, reproducibilidad del despliegue o utilidad de cada función.

Inventario estático registrado: 209 archivos Python, 28.349 líneas físicas, 952 funciones/métodos, 65 handlers HTTP identificados, 84 capturas genéricas de excepción y 52 candidatos sin referencia léxica al nombre original (44 en el grupo aproximado del núcleo). Incluye herramientas y pruebas. **Los candidatos no son 52 funciones muertas demostradas:** existen alias, registros dinámicos y posibles consumidores externos.

Hallazgos que explican las prioridades del backlog:

- Snapshot y migraciones incompatibles con una instalación limpia; faltan contratos expresados en el repositorio.
- El modo estricto de MDM existe, pero el recorrido principal de resolución no lo integra completamente.
- La cuarentena almacena `Valor_Corregido`, pero la reinyección no cierra su aplicación efectiva; IDs locales pueden coincidir entre tablas. Decisión y auditoría se confirman por separado. La caché omite el filtro de estado.
- El validador de matriz de proyecciones no está conectado a guardar/ejecutar. Hay riesgos temporales, inputs futuros, sumas de censo sin vigencia y valores de respaldo silenciosos (1.500 plantas y peso fijo 0,00289).
- Las simulaciones sobrescriben resultados sin identidad/versionado completos; guardar por fila puede dejar resultados parciales y el resultado del guardado no se refleja adecuadamente.
- Lluvia/temperatura/variaciones contienen constantes o vacíos; toneladas se presentan con etiqueta de rendimiento t/ha sin superficie. Faltan estados claros de disponibilidad.
- Gold usa vistas con NOLOCK y no tiene publicación estable/versionada; la hora de consulta no demuestra frescura de la carga.
- El runner interpreta stdout por regex con un paso activo, pese a facts paralelas. Blinker es local al proceso y no comunica runner/API.
- Hay breaker central probado y lógica inline distinta; lotes pequeños pueden rechazar todo sin representar claramente el fallo.
- `fact_ciclos_fenologicos.py` recorta fechas posteriores a 2026-06-30: debe revisarse la regla con negocio y evitar alteración silenciosa.
- JWT verifica usuario activo pero puede conservar permisos antiguos del rol del token. Logs saneados solo en message pueden filtrar inputs sensibles en extras. Request ID global puede mezclarse entre peticiones.
- Exportaciones completas a DataFrame/BytesIO y trabajo síncrono en handlers async requieren límites y delegación acotada.
- Configuración duplicada, imports por sys.path, funciones extensas y herramientas administrativas mezcladas complican mantenimiento y reproducibilidad.

Criterio para código aparentemente sobrante:

- Integrar validadores, política estricta y evaluación de calidad que sí sean parte del contrato deseado.
- Revisar consumidores externos antes de retirar herramientas o interfaces públicas.
- No borrar módulos completos porque un wrapper no se usa: sus helpers pueden estar activos.
- Clasificar cada símbolo como conservar, conectar o retirar, con evidencia y verificación de comportamiento.

## 7. Decisión sobre Bronce: SQL Server y Parquet

Recomendación comunicada y aceptada como orientación: **conservar Bronce operativo en SQL Server por ahora; evaluar Parquet para históricos según mediciones. No se implementó un cambio de almacenamiento.**

Parquet es columnar y ofrece compresión/codificación eficiente para analítica e históricos. Fuente técnica: https://parquet.apache.org/ . No es un sustituto automático de los estados y transacciones que utiliza el ETL actual.

Distribución propuesta:

| Información | Destino recomendado |
|---|---|
| Excel original | Archivo conservado y trazable |
| Bronce activo del ETL | SQL Server |
| Histórico voluminoso de Bronce | Parquet opcional, si aporta valor medido |
| Estados, ejecuciones, errores, MDM y control | SQL Server |
| Silver, Gold y consultas del backend | SQL Server |

Evitar duplicar todo indiscriminadamente. Para incorporar Parquet se necesitarían finalidad y retención claras, ID de carga, vínculo al original, versión de esquema, identidad de filas, publicación de archivos y recuperación consistente ante fallos. Una transacción SQL no abarca por sí sola el sistema de archivos. Convertir Excel a Parquet tampoco conserva toda la evidencia del archivo original.

Medir primero almacenamiento/crecimiento, tiempo de carga y reproceso, lectura y memoria con datos representativos. Clima horario es un candidato por su frecuencia, pero no se conoce aún su volumen real ni se demostraron ahorros. Este cambio no es prioridad del refactor inicial.

## 8. Temporales y limpieza pendiente

El usuario mostró estas carpetas y preguntó si podía borrarlas; luego indicó que lo haría más adelante. **No se borraron en ese intercambio.**

- `.test-tmp-critical`, `.test-tmp-critical-approved`, `.test-tmp-regression`, `.test-tmp-regression-final`, `.test-tmp-regression-sql-final`: artefactos de pruebas anteriores; prescindibles tras conservar evidencias útiles.
- `.test-deps`: dependencias del entorno temporal; borrarla obliga a reinstalarlas para repetir esas pruebas.
- `.test-tmp-sqlserver`: copia aislada, fixtures, logs y estado de conexión; se recomendó conservarla mientras sirva para reproducir el ensayo. Puede contener secretos de prueba.

Eliminar carpetas no elimina la base SQL Server ni su login. No ejecutar DROP DATABASE ni borrar recursivamente como parte de una limpieza implícita. Si se solicita limpieza, verificar rutas absolutas dentro del workspace y procesos que las estén usando.

## 9. Entregables para consultar

Rutas relativas a la raíz `D:\DataWareHouse-main`; se mantienen relativas aquí para que el documento siga siendo útil si se traslada el proyecto.

- `docs/analisis-sistema-antes-del-frontend.md`: análisis inicial.
- `docs/correcciones-criticas-etapa-1.md`: correcciones críticas.
- `docs/validacion-sqlserver-aislado.md`: condiciones, resultados y limitaciones del ensayo real.
- `docs/validacion-sqlserver-aislado-resultados.json`: evidencia estructurada sin credenciales.
- `docs/auditoria-refactor/propuesta.md`: propuesta completa, decisiones sobre código, arquitectura objetivo, etapas y aceptación.
- `docs/auditoria-refactor/backlog.json` y `backlog.csv`: 36 acciones, dependencias, referencias y aceptación.
- `docs/auditoria-refactor/inventario-estatico.json`: inventario AST y candidatos.
- `docs/auditoria-refactor/analizar.py`: análisis estático, sin importar la aplicación ni abrir DB.
- `docs/auditoria-refactor/verificacion.json`: verificación de entregables y de que los hashes de 209 archivos de aplicación no cambiaron durante la propuesta.
- `docs/auditoria-refactor/mapas.json`: ubicación y procedencia de mapas.

Archify:

- Herramienta local `.analysis-tools/archify`, versión v3.2.0, commit de la herramienta `208acba8d412335185b2056fedf54b3405df43fb`. Ese commit no es del proyecto ACP.
- Índice `.archify/architecture-acp-audit-20261103-204308/index.html`.
- Mapas `arquitectura-actual.html`, `flujo-etl.html` y `refactor-propuesto.html` en la misma carpeta, con candidatos JSON y recibos de validación.
- Los mapas pasaron validación/entrega/comprobaciones automáticas de navegador. No afirmar revisión visual manual si no se realiza.
- Son diagramas curados del estado local; no contienen atribución probada a un commit del proyecto. Los esquemas SQL representados no implican bases físicas separadas.
- No se subió código a un servicio externo para generarlos ni se instaló la herramienta como skill global.

Este archivo permite entender el contexto por sí solo. Para continuar con precisión de líneas, comandos de ejecución o detalles extensos de cada hallazgo, consultar los artefactos citados y comprobar el estado actual del código.

## 10. Próxima secuencia recomendada

1. Leer este documento, la propuesta y el informe SQL aislado. Revisar instrucciones locales vigentes y cambios posteriores al corte.
2. Confirmar el objetivo que el usuario quiera ejecutar: la propuesta no es una orden para implementar las 36 acciones de una vez.
3. Si se autoriza comenzar el refactor, priorizar R01: baseline reproducible en base vacía aislada, sin parches ad hoc. Separar baseline, migraciones inmutables y mantenimiento.
4. Ampliar pruebas representativas de los 15 dominios y preservar los fallos inducidos/rollback. Cubrir válidos, rechazados, duplicados, reintentos y aislamiento geográfico/temporal.
5. Resolver por bloques pequeños políticas MDM, cuarentena, calidad y contratos de proyecciones, respetando dependencias del backlog.
6. Después consolidar publicación Gold, telemetría, configuración, seguridad, limpieza y límites operativos. Revisar con negocio las reglas que cambian resultados.
7. Revalidar ETL y backend de extremo a extremo en SQL aislado antes de dar cada bloque por cerrado. Definir contratos estables antes del frontend.

No afirmar que todo el sistema está correcto, que los 15 dominios tienen E2E completo o que la instalación limpia ya pasó. No repetir validaciones sobre la base habitual ni empezar una migración a Parquet por inferencia.

## 11. Backlog completo al corte

La tabla siguiente se incorpora desde el backlog existente para que el traspaso conserve las 36 propuestas aunque se comparta solo este Markdown. P0/P1/P2 son prioridades propuestas; esfuerzo S/M/L es estimativo. Ninguna fila se considera implementada por aparecer aquí.

### R01 — Baseline y contratos fuera de sincronía

Prioridad: P0 | Área: SQL | Esfuerzo: L | Dependencias: sin dependencia declarada

Evidencia: Snapshot y migraciones requieren reparaciones para instalar desde cero.

Propuesta: db/baseline + migraciones incrementales inmutables; separar mantenimiento.

Aceptación: Base vacía -> instalación sin parches de prueba -> E2E funcional.

Referencias al corte: `docs/validacion-sqlserver-aislado.md; tests/integration/schema_prerequisites.sql`.

### R02 — Modo estricto desconectado

Prioridad: P1 | Área: MDM | Esfuerzo: M | Dependencias: R01

Evidencia: es_modo_estricto existe pero el resolver principal crea geografías sin consultarlo.

Propuesta: Conectar política estricta; fallo de configuración debe quedar explícito.

Aceptación: ON impide auto-create en los 15 procesadores; OFF conserva política acordada.

Referencias al corte: `ETL/mdm/cuarentena.py:29; ETL/mdm/lookup.py:764`.

### R03 — Corrección y reinyección sin contrato cerrado

Prioridad: P1 | Área: MDM | Esfuerzo: L | Dependencias: R01,R02

Evidencia: Valor_Corregido no se aplica en el recorrido de reinyección y el ID puede probarse en varias tablas.

Propuesta: Origen físico inequívoco + override tipado + estados de aplicación + auditoría atómica.

Aceptación: Corregir cambia Silver; repetir no duplica ni toca una fuente con ID local igual.

Referencias al corte: `backend/repositorios/repo_reinyeccion.py:32; backend/servicios/servicio_cuarentena.py:54`.

### R04 — Caché omite estado de cuarentena

Prioridad: P1 | Área: API | Esfuerzo: S | Dependencias: sin dependencia declarada

Evidencia: La clave no incluye estado_filtro.

Propuesta: Incluir filtros normalizados y versionado/invalidation explícitos.

Aceptación: PENDIENTE y RESUELTO nunca comparten respuesta cacheada.

Referencias al corte: `backend/servicios/servicio_cuarentena.py:29`.

### R05 — Validador de matriz no conectado

Prioridad: P1 | Área: Proyecciones | Esfuerzo: M | Dependencias: sin dependencia declarada

Evidencia: Ejecutar y guardar admiten entradas sin validación semántica completa.

Propuesta: Invocar validador de dominio; validar estados, semanas, sumas, finitud y márgenes.

Aceptación: Matriz 160%, NaN y márgenes inválidos se rechazan antes de calcular/escribir.

Referencias al corte: `backend/servicios/servicio_proyecciones.py:38; backend/api/rutas_proyecciones.py:39`.

### R06 — Corte temporal inconsistente

Prioridad: P1 | Área: Proyecciones | Esfuerzo: L | Dependencias: R01

Evidencia: Censo suma sin vigencia; pesos/condición pueden usar información posterior.

Propuesta: Contrato as-of por entrada; fechas y año ISO conservados.

Aceptación: Proyección histórica no consume observaciones futuras no autorizadas.

Referencias al corte: `backend/repositorios/repo_proyecciones.py:118`.

### R07 — Supuestos silenciosos

Prioridad: P1 | Área: Proyecciones | Esfuerzo: M | Dependencias: R06

Evidencia: Respaldo de 1500 plantas y peso fijo no se identifica al consumidor.

Propuesta: Cobertura, calidad, procedencia y política de estimación visibles.

Aceptación: Cada resultado indica entradas observadas/estimadas y motivo.

Referencias al corte: `backend/servicios/servicio_proyecciones.py:81`.

### R08 — Cálculo sobrescribe escenario sin identidad de simulación

Prioridad: P1 | Área: Proyecciones | Esfuerzo: L | Dependencias: R05,R06

Evidencia: MERGE no conserva cada cutoff/versión y ejecutar persiste automáticamente.

Propuesta: ID de simulación, snapshot de inputs, autor, modelo y publicación separada.

Aceptación: Simulaciones simultáneas no sobrescriben resultados y pueden reproducirse.

Referencias al corte: `backend/repositorios/repo_proyecciones.py:355; backend/servicios/servicio_proyecciones.py:208`.

### R09 — Guardado parcial sin reflejarse en respuesta

Prioridad: P1 | Área: Proyecciones | Esfuerzo: M | Dependencias: R08

Evidencia: Transacción por fila; resultado de persistencia ignorado.

Propuesta: Escritura por lote atómica, idempotente y con estado devuelto.

Aceptación: Fallo en la fila intermedia revierte toda la simulación.

Referencias al corte: `backend/repositorios/repo_proyecciones.py:355`.

### R10 — Métricas fijas y unidades ambiguas

Prioridad: P1 | Área: Analítica | Esfuerzo: M | Dependencias: R01

Evidencia: Lluvia/temperatura/variación son constantes; toneladas se etiquetan rendimiento_tha.

Propuesta: Catálogo semántico con unidades, fórmulas, null y disponibilidad.

Aceptación: No se muestra cero/Estable si no hubo cálculo; t/ha usa superficie.

Referencias al corte: `backend/servicios/servicio_analista_charts.py:146; backend/api/rutas_proyecciones.py:70`.

### R11 — Bloqueo final no equivale a publicación

Prioridad: P1 | Área: Gold | Esfuerzo: L | Dependencias: R01

Evidencia: Vistas y lectores Silver observan el estado cambiante; NOLOCK sigue presente.

Propuesta: Definir versión publicada/snapshot y política de lectura.

Aceptación: Corrida fallida no cambia métricas oficiales; frescura viene de publicación.

Referencias al corte: `ETL/gold/marts.py:67; ETL/sql_migrations/fase70_consolidar_vistas_gold.sql`.

### R12 — Telemetría secuencial sobre facts paralelas

Prioridad: P1 | Área: Operación | Esfuerzo: L | Dependencias: R01

Evidencia: Un único paso activo y regex de stdout asignan eventos por contexto implícito.

Propuesta: Eventos estructurados por corrida/fact/paso con secuencia y métricas.

Aceptación: Logs intercalados de 4 facts conservan dueño, tiempos y estado.

Referencias al corte: `backend/runner/ejecutor.py:42; backend/runner/ejecutor.py:168`.

### R13 — Dependencias y errores de SP incompletos

Prioridad: P1 | Área: ETL | Esfuerzo: M | Dependencias: R12

Evidencia: Rerun y completo no sincronizan exactamente las mismas dependencias; algunas fallas son advertencias.

Propuesta: DAG declarativo; dependencias obligatorias/optativas y calidad agregada.

Aceptación: Fallo de campaña/bridge requerido bloquea consumidores y publicación.

Referencias al corte: `ETL/utils/ejecucion.py:280; ETL/pipeline.py:369`.

### R14 — Adapter EngineTransaccional presta una conexión con API parcial

Prioridad: P2 | Área: Transacciones | Esfuerzo: L | Dependencias: R24

Evidencia: La compatibilidad probada no cubre toda la superficie Engine.

Propuesta: Inyección explícita de Connection/UoW en lectores y escritores.

Aceptación: Ninguna llamada dentro de una fact abre otra conexión; rollback piloto sigue pasando.

Referencias al corte: `ETL/utils/reproceso_atomico.py:8; ETL/utils/contexto_transaccional.py:28`.

### R15 — Dos implementaciones de circuit breaker

Prioridad: P1 | Área: Calidad | Esfuerzo: M | Dependencias: R24

Evidencia: Módulo puro probado y lógica inline en BaseFactProcessor no son el mismo recorrido.

Propuesta: Usar evaluación canónica con umbrales por dominio y errores absolutos.

Aceptación: Pruebas del procesador real y evaluación pura producen el mismo dictamen.

Referencias al corte: `ETL/utils/circuit_breaker.py:62; ETL/silver/facts/_base_processor.py:1081`.

### R16 — Tope fijo altera ciclos fenológicos

Prioridad: P1 | Área: Fechas | Esfuerzo: M | Dependencias: R06

Evidencia: Fechas posteriores a 2026-06-30 se recortan al mismo día.

Propuesta: Preservar fecha original; rechazo o excepción de negocio explícita y versionada.

Aceptación: Julio de 2026 no se convierte silenciosamente en junio.

Referencias al corte: `ETL/silver/facts/fact_ciclos_fenologicos.py:138`.

### R17 — Selección del último archivo sin contrato de entrega

Prioridad: P1 | Área: Ingesta | Esfuerzo: L | Dependencias: R01

Evidencia: Procesa como máximo un pendiente por carpeta y marca por tamaño/mtime.

Propuesta: Definir foto/incremental/corrección; cola durable y hash por contenido.

Aceptación: Tres archivos se procesan según política explícita y un reenvío no duplica.

Referencias al corte: `ETL/bronce/rutas.py:160; ETL/bronce/cargador.py:1636`.

### R18 — Blinker no conecta procesos

Prioridad: P2 | Área: Eventos | Esfuerzo: M | Dependencias: R12

Evidencia: El runner emite señales en otro proceso; listeners API no las reciben.

Propuesta: Mantener Blinker local; usar Control/outbox para eventos durables entre procesos.

Aceptación: Fin ETL invalida lecturas correspondientes sin depender de una señal local.

Referencias al corte: `backend/servicios/event_bus.py:30; backend/servicios/listeners.py:70`.

### R19 — Rol de JWT no se refresca desde DB

Prioridad: P1 | Área: Seguridad | Esfuerzo: M | Dependencias: sin dependencia declarada

Evidencia: Se verifica usuario activo pero se autorizan permisos del token.

Propuesta: Autoridad de rol definida: DB o versión de autorización y revocación.

Aceptación: Token de ex-admin pierde privilegios después de degradación.

Referencias al corte: `backend/nucleo/auth.py:178`.

### R20 — Saneamiento solo de message

Prioridad: P1 | Área: Logs | Esfuerzo: M | Dependencias: sin dependencia declarada

Evidencia: Errores Pydantic completos se añaden a extras sin saneamiento estructural.

Propuesta: Excluir input sensible; sanitizar extras y excepciones por campo.

Aceptación: Payload sintético con clave/DNI inválidos no aparece en logs.

Referencias al corte: `backend/nucleo/excepciones.py:112; backend/nucleo/logging.py:70`.

### R21 — Settings y conexión no comparten entrada efectiva

Prioridad: P1 | Área: Configuración | Esfuerzo: M | Dependencias: R01

Evidencia: Settings lee archivos pero el engine consume os.getenv por otra ruta.

Propuesta: Configuración validada única y explícita para construir Engine.

Aceptación: Arranque directo y launcher usan exactamente el mismo servidor/base; test exige destino aislado.

Referencias al corte: `backend/nucleo/settings.py; backend/nucleo/conexion.py; comun/conexion.py`.

### R22 — Imports por sys.path y dependencias dispersas

Prioridad: P2 | Área: Empaquetado | Esfuerzo: L | Dependencias: R21

Evidencia: Paquetes no instalables y configuración duplicada entre requirements.

Propuesta: Paquetes locales instalables y dependencias por grupo con lock reproducible.

Aceptación: Instalar en entorno limpio sin editar sys.path ni depender de cwd.

Referencias al corte: `comun/validacion.py; backend/nucleo/etl_catalogo.py:18; requirements.txt`.

### R23 — Trabajo bloqueante y exportación completa

Prioridad: P2 | Área: API | Esfuerzo: M | Dependencias: R24

Evidencia: Async exporta leyendo toda la tabla; auth ejecuta trabajo sync directamente.

Propuesta: Delegación acotada, límites de archivos y export en chunks/job según tamaño.

Aceptación: Carga grande no bloquea liveness ni excede un presupuesto de memoria acordado.

Referencias al corte: `backend/api/rutas_ingesta.py:42; backend/nucleo/auth.py:178`.

### R24 — Cobertura parcial y lógica espejada

Prioridad: P1 | Área: Pruebas | Esfuerzo: L | Dependencias: R01

Evidencia: Algunas pruebas duplican implementación; solo 4 dominios tienen evidencia E2E no vacía.

Propuesta: Fixtures de los 15 contratos, tests reales, aislamiento obligatorio y fallos inducidos.

Aceptación: Cada fact tiene caso válido, rechazado, duplicado, retry y rollback aplicables.

Referencias al corte: `ETL/tests/test_base_processor_puro.py; tests/integration/sqlserver_e2e.py`.

### R25 — Cachés sin snapshot por corrida

Prioridad: P2 | Área: Configuración | Esfuerzo: M | Dependencias: R12

Evidencia: Cambios de reglas/parámetros no son una versión persistida del cálculo.

Propuesta: Congelar parámetros al inicio y asociarlos a corrida/simulación.

Aceptación: Repetir una corrida con la misma versión mantiene las reglas efectivas.

Referencias al corte: `ETL/config/parametros.py:58; ETL/mdm/lookup.py:61`.

### R26 — Scripts administrativos dispersos

Prioridad: P2 | Área: Herramientas | Esfuerzo: M | Dependencias: R21

Evidencia: Check, test, reparación y limpieza comparten árbol sin contrato operativo único.

Propuesta: CLI de lectura separada de mantenimiento; inventario de consumidores externos.

Aceptación: Ningún diagnóstico por defecto escribe ni apunta al destino habitual.

Referencias al corte: `ETL/tools; ETL/check_*.py; backend/scratch`.

### R27 — Candidatos sin referencias no clasificados

Prioridad: P2 | Área: Código sobrante | Esfuerzo: M | Dependencias: R24

Evidencia: 52 candidatos AST; 44 en grupo aproximado de núcleo.

Propuesta: Revisión por símbolo: retirar, conectar o conservar; no eliminación masiva.

Aceptación: Cada retiro tiene evidencia de consumidores y prueba de comportamiento.

Referencias al corte: `docs/auditoria-refactor/inventario-estatico.json`.

### R28 — Serialización del catálogo duplicada

Prioridad: P2 | Área: Contratos | Esfuerzo: S | Dependencias: R22

Evidencia: ETL expone obtener_catalogo_facts pero backend vuelve a construir el mismo DTO.

Propuesta: Una función canónica sin importación dinámica de archivo.

Aceptación: Backend y CLI exponen el mismo catálogo y dependencias.

Referencias al corte: `ETL/utils/ejecucion.py:232; backend/nucleo/etl_catalogo.py:27`.

### R29 — Refresh y truncate nombran operaciones inexistentes

Prioridad: P2 | Área: Gold | Esfuerzo: S | Dependencias: R11

Evidencia: _truncar es no-op; refresh consulta y cuenta vistas.

Propuesta: Renombrar comprobación/estadísticas y reservar publicar para una operación real.

Aceptación: Nombres, documentación y métricas coinciden con la operación ejecutada.

Referencias al corte: `ETL/gold/marts.py:67; ETL/gold/marts.py:193`.

### R30 — Errores heterogéneos y exposición de str(error)

Prioridad: P1 | Área: API | Esfuerzo: M | Dependencias: R05

Evidencia: Proyecciones transforma cualquier excepción en HTTP 500 con detalle interno.

Propuesta: Taxonomía de errores de dominio e infraestructura y respuesta consistente.

Aceptación: Cliente recibe 4xx/5xx y request_id sin SQL ni trazas.

Referencias al corte: `backend/api/rutas_proyecciones.py:82; backend/nucleo/excepciones.py`.

### R31 — Página fuera de rango devuelve total cero

Prioridad: P2 | Área: Catálogos | Esfuerzo: S | Dependencias: sin dependencia declarada

Evidencia: COUNT OVER no devuelve su total si no hay filas en la página.

Propuesta: Total estable con consulta de respaldo o contrato de cursor.

Aceptación: Página 999 conserva total real aunque datos esté vacío.

Referencias al corte: `backend/repositorios/repo_catalogos.py:78`.

### R32 — Request ID en variable de clase global

Prioridad: P2 | Área: Observabilidad | Esfuerzo: M | Dependencias: R12

Evidencia: _RequestIdFilter._current se comparte entre peticiones concurrentes.

Propuesta: ContextVar y filtro/fábrica de LogRecord adecuados; propagar a trabajo derivado.

Aceptación: Peticiones solapadas no mezclan request_id y cada evento conserva correlación.

Referencias al corte: `backend/nucleo/middleware.py:30`.

### R33 — Decisión y bitácora se confirman por separado

Prioridad: P1 | Área: Auditoría | Esfuerzo: M | Dependencias: R03,R14

Evidencia: Resolver puede guardar decisión y fallar al auditar después.

Propuesta: UoW para mutación + auditoría u outbox durable según contrato.

Aceptación: Fallo de auditoría no deja una decisión confirmada que el cliente percibe fallida.

Referencias al corte: `backend/servicios/servicio_cuarentena.py:66; backend/repositorios/repo_cuarentena.py:128`.

### R34 — Archivos y funciones con responsabilidades mezcladas

Prioridad: P2 | Área: Mantenibilidad | Esfuerzo: L | Dependencias: R24

Evidencia: Cargador 1788 líneas, base 1136 y ejecutar_corrida 308 líneas.

Propuesta: Extraer parsing, planificación, transformación, persistencia y presentación por contrato.

Aceptación: Cambiar un layout no modifica SQL compartido ni orquestación.

Referencias al corte: `ETL/bronce/cargador.py; ETL/silver/facts/_base_processor.py; backend/runner/ejecutor.py:168`.

### R35 — Ausencia y fallo se confunden

Prioridad: P1 | Área: Analítica | Esfuerzo: M | Dependencias: R30

Evidencia: Notificaciones vacías ante BD caída; comparaciones previas devuelven vacío ante excepción.

Propuesta: Estado disponible/no_disponible/parcial y errores observables.

Aceptación: BD caída no se presenta como cero alertas o cero producción.

Referencias al corte: `backend/servicios/servicio_analista_notificaciones.py:63; backend/repositorios/repo_proyecciones.py:290`.

### R36 — Relojes y zonas heterogéneos

Prioridad: P2 | Área: Fechas | Esfuerzo: M | Dependencias: R06

Evidencia: utcnow/now/SYSDATETIME y reemplazo tzinfo conviven.

Propuesta: UTC en eventos técnicos; zona agronómica explícita para cortes y calendario.

Aceptación: Corte de medianoche y cruce de año ISO tienen expectativas probadas.

Referencias al corte: `backend/repositorios/repo_alertas.py:55; backend/repositorios/repo_calidad.py:20; ETL/pipeline.py:73`.

