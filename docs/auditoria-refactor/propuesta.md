# Propuesta integral de refactor y depuración de ACP

Estado: **propuesta, sin implementar cambios en ETL, backend o base de datos en esta ronda**.

## 1. Dictamen

El sistema funciona en los recorridos verificados, pero todavía tiene deuda técnica relevante y capacidades incompletas. Las pruebas anteriores demuestran comportamiento concreto; no demuestran que todas las reglas de negocio estén conectadas, que todos los módulos aporten valor ni que la instalación sea reproducible.

La deuda más importante combina tres problemas:

1. **El contrato de datos desplegado no está completamente expresado en el repositorio.** La instalación aislada necesitó complementar el snapshot y adaptar una secuencia histórica incompatible.
2. **Hay políticas y capacidades implementadas que el recorrido principal no utiliza.** Destacan el modo estricto de MDM, el validador de matriz y el circuit breaker centralizado.
3. **La operación técnica puede parecer satisfactoria aunque el resultado de negocio sea incompleto.** Aparecen ceros de ejemplo, errores convertidos en vacíos, datos estimados sin procedencia explícita y fechas recortadas.

Recomiendo un refactor incremental con pruebas de caracterización y entregas pequeñas. La limpieza de funciones debe acompañar ese proceso; borrar primero los elementos sin referencias puede eliminar precisamente las validaciones que faltan por integrar.

No recomiendo reescribir el sistema, introducir microservicios ni sustituir simultáneamente FastAPI, SQL Server, el runner y el procesamiento de datos.

## 2. Evidencia y alcance

Se revisaron el código actual, los puntos de entrada, el catálogo de facts, llamadas e imports, registros de rutas, configuración, acceso SQL, decisiones de calidad, migraciones, pruebas y las evidencias del ensayo SQL Server anterior.

El inventario AST se realizó sin importar módulos del proyecto ni abrir conexiones. Cubre `ETL`, `backend` y `comun`; incluye sus pruebas y herramientas. Excluye las copias temporales, dependencias descargadas y artefactos de Archify.

| Medida | Resultado | Interpretación |
|---|---:|---|
| Archivos Python | 209 | Incluye núcleo, pruebas y herramientas |
| Líneas Python | 28.349 | Líneas físicas; no equivale a complejidad ni calidad |
| Funciones y métodos | 952 | Incluye código de pruebas |
| Handlers HTTP identificados | 65 | Decoradores registrados en archivos inspeccionados |
| Capturas genéricas de excepción | 84 | Lugares para clasificar; no son 84 errores demostrados |
| Candidatos sin referencia léxica al nombre original | 52 | Posibles falsos positivos por alias, exportaciones y carga dinámica |
| Candidatos en el grupo aproximado de núcleo | 44 | Clasificación por rutas, no prueba de código muerto |

La última regresión funcional disponible es **138 pruebas aprobadas y una omitida**, más el ensayo real de SQL Server. En esta ronda no se volvió a ejecutar el sistema: el trabajo es de análisis, propuesta y generación de mapas.

No hay metadata Git en esta copia. Los mapas representan el estado local inspeccionado y no incluyen atribución automática a un commit del proyecto. El inventario conserva hashes de los archivos leídos. No se conoce el uso de scripts desde tareas programadas, SQL Agent o equipos externos; ese uso debe comprobarse antes de retirar interfaces públicas.

Entregables asociados:

- `inventario-estatico.json`: métricas, funciones, imports, excepciones y candidatos.
- `backlog.json` y `backlog.csv`: 36 propuestas con prioridad, evidencia, aceptación y dependencias.
- Tres mapas Archify: arquitectura actual, flujo de datos y decisiones propuestas.
- `analizar.py`: análisis estático reproducible, sin ejecutar lógica del sistema.

## 3. Qué está bien encaminado y debe conservarse

| Elemento | Valor actual | Decisión |
|---|---|---|
| Separación API / runner / ETL | Las peticiones no esperan todo el pipeline | Conservar y precisar los contratos entre procesos |
| Control SQL durable | Cola, corridas, eventos y lock sobreviven al proceso HTTP | Conservar; extender como soporte de eventos estructurados |
| Organización de backend | Rutas, servicios, repositorios y schemas ya existen | Consolidar responsabilidades, sin otra capa ceremonial |
| Medallion y dimensiones | El modelo representa dominios agrícolas reales | Conservar; fijar granularidad y vigencia por dominio |
| Catálogo de 15 facts | Permite descubrir capacidades y planear reprocesos | Convertirlo en contrato canónico, sin serializadores duplicados |
| Deduplicación por lote | Resuelve duplicados con claves y desempates | Mantener, con invariantes y pruebas de cada dominio |
| Reproceso atómico por fact | Rollback probado con driver SQL Server real | Mantener la garantía; migrar gradualmente a conexión explícita |
| Identidad dimensional | ETL y backend ya separan los fundos probados | Extender la prueba a ambigüedad, SCD2 y granularidades distintas |
| Protección de migraciones | Manifiesto, hashes, detención y errores ODBC diferidos | Mantener y construir un baseline compatible |

## 4. Hallazgos de mayor impacto

### 4.1 Contrato SQL e instalación — R01, R24

La instalación aislada demostró que el snapshot no constituye una receta de despliegue suficiente. Faltaban contratos de columnas y existían definiciones antiguas de procedimientos. La secuencia también contenía dependencias de índices y conversiones de tipos de objeto que fallaban.

**Propuesta:** generar un baseline declarativo del estado actual, incluyendo tablas, claves, índices, procedimientos, funciones y vistas. Separar los seeds técnicos obligatorios de los datos maestros y de los ejemplos. Conservar inmutables los archivos ya aplicados; añadir una transición documentada para bases existentes y otra ruta para bases vacías.

**Aceptación:** instalar en una base vacía con un comando y ejecutar el ensayo funcional sin `schema_prerequisites.sql`, sustituciones de SQL ni reparaciones manuales. Una instalación parcial debe fallar y dejar un diagnóstico verificable.

No basta con cambiar a Alembic: primero hay que decidir cuál es el contrato correcto. Después se evalúa si el runner actual puede mantenerlo o conviene adoptar otra herramienta.

### 4.2 Modo estricto MDM sin aplicación en el resolver — R02

[es_modo_estricto](D:/DataWareHouse-main/ETL/mdm/cuarentena.py:29) consulta el flag y tiene pruebas. Sin embargo, el [resolver principal](D:/DataWareHouse-main/ETL/mdm/lookup.py:764) no lo consulta antes de crear nuevas geografías.

Esto no es una función inútil: es una política importante que no está conectada al recorrido que necesita proteger. Además, ante errores de consulta, el helper asume OFF.

**Propuesta:** una política de resolución explícita: resolver, proponer alta o enviar a revisión. En modo estricto, ninguna combinación nueva se crea automáticamente. La indisponibilidad de configuración debe representarse como error o estado controlado según una decisión acordada, no desactivar silenciosamente la protección.

**Aceptación:** probar ON y OFF a través de procesadores reales; verificar que ON no crea dimensiones, conserva el origen y produce una cuarentena accionable.

### 4.3 Fechas reescritas por un tope fijo — R16

[Fact_Ciclos_Fenologicos](D:/DataWareHouse-main/ETL/silver/facts/fact_ciclos_fenologicos.py:138) cambia fechas posteriores al 30 de junio de 2026 por ese mismo día. La validación anterior no incluyó datos no vacíos de este dominio.

**Propuesta:** preservar la fecha observada. Si existe una excepción histórica aprobada, implementarla como regla versionada con rango de aplicación, valor original y justificación. Una fecha fuera del período permitido puede rechazarse o revisarse, pero no convertirse silenciosamente en otra fecha válida.

**Aceptación:** casos anteriores, iguales y posteriores al límite; cruce de año; campaña vigente y cerrada. Ninguno altera la fecha sin una regla explícita trazable.

### 4.4 Calidad centralizada en apariencia — R15

[utils/circuit_breaker.py](D:/DataWareHouse-main/ETL/utils/circuit_breaker.py:62) tiene una evaluación pura probada. [BaseFactProcessor.finalizar_proceso](D:/DataWareHouse-main/ETL/silver/facts/_base_processor.py:1081) mantiene otra implementación inline. El recorrido de producción no importa la evaluación centralizada.

Hay también nomenclatura confusa: `Bloqueo_Integridad` se asigna con `nivel_bloqueo == 'WARNING'`, mientras los bloqueos efectivos usan otras claves.

**Propuesta:** una evaluación canónica que devuelva un resultado tipado: cobertura, rechazos por registro, severidad, dictamen y causas. Separar errores absolutos —identidad inválida, esquema incompatible— de umbrales estadísticos. Conservar las excepciones de negocio por fact donde estén justificadas.

**Aceptación:** las pruebas del procesador real y las del evaluador puro coinciden. Una muestra pequeña totalmente rechazada no se presenta como resultado de negocio satisfactorio solo porque no aplique el umbral estadístico.

### 4.5 Cuarentena, corrección y auditoría — R03, R04, R33

La reinyección reactiva estados de Bronce, pero no aplica el valor corregido en el recorrido revisado. Algunos orígenes lógicos se prueban contra varias tablas físicas usando el mismo ID local. El registro de auditoría y la decisión se confirman mediante llamadas separadas. La caché de listado omite el filtro de estado.

**Propuesta:** identidad de incidente y fila física completas; correcciones tipadas por columna; tratamiento conjunto de varios errores de una fila; transacción para decisión y auditoría; estados de aplicación/reintento; vínculo a la corrida que efectivamente incorporó la corrección. El original debe conservarse como evidencia; un override aprobado es preferible a sobrescribir el Excel archivado.

**Aceptación:** corregir → reinyectar → reprocesar → verificar Silver, con repetición idempotente. Incluir un ID idéntico en dos tablas, varios errores en una fila y un fallo de auditoría.

### 4.6 Proyección todavía sin contrato reproducible completo — R05 a R10

La identidad de fundos se corrigió, pero quedan aspectos distintos:

- El validador de matriz existe y no está conectado a ejecución/guardado.
- El censo carece de selección temporal consistente y los pesos/condición pueden utilizar información posterior al corte.
- Los valores de respaldo de plantas y peso no se identifican suficientemente en la respuesta.
- Ejecutar también persiste; no hay identidad completa de cada simulación.
- Se escribe por fila, se acumulan errores y el servicio ignora el resumen de guardado.
- Anterior, variación y tendencia tienen valores fijos en la respuesta.

**Propuesta:** separar `preparar_entradas`, `validar_escenario`, `calcular`, `guardar_simulacion` y `publicar`. Las entradas deben tener corte, procedencia, versión y cobertura. La fórmula puede ser una función pura; los lectores de datos y la persistencia permanecen fuera de ella.

**Aceptación:** mismo snapshot y parámetros → mismo resultado; cambio de reglas → nueva versión; simulación concurrente → identidad separada; fallo de persistencia → ninguna publicación parcial. Validar el significado de plantas productivas, muestreo, superficie y pesos con el negocio antes de modificar fórmulas.

### 4.7 Publicación y telemetría — R11 a R13, R18

Gold son vistas; las lecturas directas de Silver y el uso de NOLOCK siguen existiendo. El chequeo final no es una publicación de versión. El runner mantiene un único paso activo interpretando stdout, aunque el completo procesa varias facts simultáneamente. Blinker funciona dentro de un proceso; no transporta las señales del runner a los listeners de otro proceso HTTP.

**Propuesta:** eventos estructurados persistidos con corrida, fact, paso, secuencia y métricas. Definir dependencias y políticas de continuación por un plan declarativo. Mantener separados el estado operativo de una corrida y la versión analítica publicada. Utilizar Control/outbox para hechos durables entre procesos; reservar Blinker para avisos locales donde aporte valor.

**Aceptación:** cuatro facts con logs intercalados mantienen su identidad. Un fallo de campaña/bridge requerido bloquea sus consumidores. La versión oficial sigue consultable tras un fallo; frescura es la de los datos publicados, no la hora de consulta de una vista.

### 4.8 Autorización, logs y configuración — R19 a R23, R30, R32

Hallazgos adicionales:

- Se verifica que el usuario siga activo, pero el rol utilizado para autorizar viene del JWT. Un cambio de rol en DB no actualiza ese token.
- Se registran errores Pydantic completos como extras. El sanitizador solo modifica `record.msg`; no limpia esos extras de forma estructural.
- El request ID se guarda en una variable de clase global, sin aislamiento de contexto por petición concurrente.
- Settings valida una configuración, pero el engine común vuelve a leer el entorno por otra ruta. Arranque directo y launcher pueden diferir cuando la configuración solo está en un archivo determinado.
- Hay trabajo SQL/bcrypt síncrono llamado desde rutas/dependencias async. La exportación carga toda la tabla y el CSV en memoria.
- Proyecciones convierte cualquier excepción en HTTP 500 con `str(error)`; otros servicios convierten errores de DB en listas vacías.

**Propuesta:** autoridad explícita del rol; saneamiento por estructura y campo; `ContextVar` para correlación; una sola configuración entregada al constructor del engine; límites y delegación acotada de trabajo bloqueante; taxonomía de errores consistente.

El efecto de rendimiento necesita medición. No propongo cambiar automáticamente de driver ni introducir Redis sin comprobar carga, topología y requisitos de consistencia.

## 5. Funciones sobrantes: decisiones por tipo

Un nombre sin llamadas directas no demuestra que una función sea eliminable. Se inspeccionaron alias y registros además del AST. Debe distinguirse entre implementación desconectada, compatibilidad, entrada externa y residuo real.

| Elemento | Evidencia actual | Propuesta |
|---|---|---|
| `validar_matriz_inputs` | Definida; no llamada por ejecutar/guardar | Integrar; no retirar |
| `es_modo_estricto` y registro de cuarentena de dimensiones | Helpers probados; no aplicados por el resolver principal | Conectar política e integración real |
| `utils.circuit_breaker.evaluar` | Usada por pruebas; evaluación de producción duplicada | Adoptarla y retirar la evaluación inline después |
| `extraer_proyeccion_anterior` | Sin consumidor localizado; endpoint devuelve constantes | Integrar solo tras definir comparación y versiones |
| `obtener_catalogo_facts` | Sin consumidor localizado; backend reimplementa serialización | Hacerla canónica y retirar el duplicado |
| `cargar_dim_geografia` antiguo | Importado por pipeline, sin ejecución allí | Retirar entrada/import legado tras verificar consumidores externos |
| `dim_geografia.py` completo | V2 importa helpers de ese módulo | **Conservar helpers**; no borrar el archivo completo por su nombre |
| `_obtener_id_geografia_dim_basica` | Sin consumidor localizado; camino hacia vista antigua | Candidato a retiro del resolver legado |
| `_es_modulo_especial` | Solo definición localizada | Candidato a retiro privado |
| `_obtener_personal_existente` | Solo definición localizada | Candidato a retiro privado |
| `_safe_int` en evaluación de pesos | Solo definición localizada | Candidato a retiro privado |
| `_obtener_campo` en peladas | Solo definición localizada | Candidato a retiro; comprobar equivalencia con helpers actuales |
| `_es_fila_no_operativa` en tareo | Solo definición localizada | Revisar regla de negocio antes de decidir integración o retiro |
| `_validar_layout_migrado` en floración/inducción | Wrappers sin consumidor localizado | Integrar validación de contrato o retirar wrapper reemplazado |
| `_obtener_escenario_base` en marts | Definida; refrescos actuales consultan vistas | Retirar si el escenario se define de forma canónica en SQL/contrato |
| `refrescar_mart_peladas` | No registrada en `FUNCIONES_MARTS` ni llamada | Decidir si falta asociación en catálogo o sobra la función |
| `sincronizar_bridge_modulo_campana_condicion` | Sin llamadas localizadas | Revisar frente a sincronización vigente y retirar solo si sustituida |
| `notificar_fin_tarea` | Solo definición localizada | Retirar stub si no hay integración externa; no usarlo para fingir eventos entre procesos |
| `dq.aplicar_reglas`, `validar_dataframe`, `hay_criticos` | Orquestadores genéricos sin consumidor localizado | Unificar el motor de DQ; conservar las reglas/validadores atómicos usados |
| `comun/sql_utils.py` y `comun/validacion.py` | Sin importadores localizados en núcleo inspeccionado | Decidir adopción real o retirar fachada preparada; no ampliar abstracción por estética |
| `limpiar_cache` | AST no encuentra nombre original, pero pipeline importa alias | Conservar; falso positivo de análisis léxico |
| `finalizar_resumen_fact` | Importada con alias por varias facts | Conservar hasta retirar la compatibilidad de resultados de forma controlada |
| Wrappers `config/conexion.py` y `nucleo/conexion.py` | Compatibilidad y firmas utilizadas | Conservar durante transición de paquetes/configuración |
| `normalizar_variedad` y `normalizar_nombre_persona` | Cuerpos idénticos, nombres semánticos distintos | No borrar por duplicación trivial; compartir implementación si mejora mantenimiento |

**Protocolo de retiro:** localizar imports, alias, decoradores, strings, catálogos, CLI, documentación y consumidores externos; definir el reemplazo; agregar una prueba del comportamiento relevante; retirar en una entrega pequeña; ejecutar el contrato afectado y E2E aislado cuando toque persistencia. Las interfaces públicas pueden requerir una fase de deprecación.

No usar Vulture u otra herramienta como autorización automática para borrar. Puede complementar el inventario, pero no conoce por sí sola los contratos dinámicos o los trabajos externos.

## 6. Refactor estructural propuesto

### Límites de módulos

| Área | Responsabilidad final | Qué debe dejar de hacer |
|---|---|---|
| Contratos comunes | Identidad dimensional, tipos de resultado, políticas puras de fecha/calidad | Modificar sys.path o cargar configuración al importar |
| Extracción/layouts | Excel/CSV, encabezados, columnas y conservación del original | Decidir publicación y ejecutar SQL de negocio |
| Plan ETL | Dependencias, orden, selección de facts y políticas de ejecución | Contener detalles de parsing y SQL de inserción |
| Transformación por fact | Filas normalizadas → payload y errores de dominio | Abrir conexiones internas o confirmar transacciones |
| Persistencia SQL | Lotes, deduplicación, constraints y estados en conexión recibida | Aplicar fórmulas agronómicas o generar respuestas HTTP |
| Unidad de trabajo | Propiedad de conexión, commit y rollback | Simular toda la interfaz de un Engine para prestar una conexión |
| Servicios backend | Casos de uso y límites de transacción | SQL ad hoc, figura Plotly y formato HTTP en el mismo método |
| API | Autorización, validación de contrato y serialización | Calcular escenarios, exportar tablas enteras en el event loop |
| Observabilidad | Eventos estructurados, métricas y correlación | Inferir identidad a partir de texto de consola |

El `EngineTransaccional` actual es una adaptación útil y probada para los métodos ejercitados. Como solución permanente tiene una superficie parcial: hereda otras operaciones de Engine que podrían abrir recursos fuera de la conexión prestada. Se propone pasar `Connection`/UoW explícitamente; no retirarlo antes de migrar consumidores y repetir los ensayos de rollback.

### Estructura orientativa, todavía no creada

```text
packages/acp_core/       # Identidad, validación pura y contratos compartidos
etl/acp_etl/
  application/          # Plan, ejecución y dependencias
  extraction/           # Layouts por dominio
  transforms/           # Transformación de cada fact
  persistence/          # Repositorios SQL y unidad de trabajo
backend/acp_api/
  api/                  # Rutas y schemas
  services/             # Casos de uso
  repositories/         # Acceso SQL
db/
  baseline/             # Estado instalable vigente
  migrations/           # Incrementales inmutables
  maintenance/          # Reparación/limpieza fuera del runner normal
tools/                  # Diagnósticos y operaciones explícitas
tests/
  unit/
  contracts/
  integration/sqlserver/
  e2e/
```

Los nombres son orientativos. No conviene mover los 209 archivos como primera entrega. Primero fijar contratos y extraer una capacidad piloto; empaquetar después para evitar un cambio de rutas masivo sin mejora de comportamiento.

### Archivos que requieren extracción gradual

- `ETL/bronce/cargador.py`: separar lectores especializados, normalización, routing/layout, persistencia y archivado.
- `ETL/silver/facts/_base_processor.py`: separar resolución dimensional, deduplicación, repositorio masivo, política DQ y métricas.
- `backend/runner/ejecutor.py`: separar supervisión de proceso, heartbeat/cancelación, eventos y cierre de corrida.
- `backend/repositorios/repo_proyecciones.py`: separar selección temporal, lectura de escenarios y escritura por lote.
- `backend/servicios/servicio_analista_charts.py`: distinguir contratos de métricas, consultas y presentación. Se puede conservar Plotly como adaptador; no necesita dictar el modelo de datos del frontend.

El tamaño es una señal para inspeccionar responsabilidades, no una razón para dividir funciones arbitrariamente en fragmentos pequeños.

## 7. Orden completo de ejecución

Esfuerzo S/M/L = pequeño/medio/grande en complejidad relativa; no es un plazo comprometido. El CSV contiene las dependencias por tarea. La prioridad expresa impacto, no obliga a mezclar todos los cambios P1 en una misma entrega.

| Etapa | Trabajo | Condición para cerrar |
|---|---|---|
| 0. Congelar evidencia | Inventario de jobs externos, contratos de granularidad, reglas y fuentes | Lista de consumidores y decisiones pendientes aprobadas; datos de referencia preservados |
| 1. Baseline SQL | R01 y cimientos de R24 | Instalación vacía y transición desde esquema existente sin parches ad hoc |
| 2. Corrección de negocio | R02–R07, R10, R15, R16 y corrección de caché | Reglas conectadas, fechas fieles y resultados con calidad/procedencia explícitas |
| 3. Cierre MDM/transacciones | R03, R09, R14, R33 | Corrección/reinyección y auditoría atómicas e idempotentes |
| 4. Versionado y operación | R08, R11–R13, R18, R25 | Simulación reproducible, versión publicada y eventos por fact durables |
| 5. Modularidad y configuración | R21–R23, R28, R34, R36 | Paquetes instalables y responsabilidades separadas con contratos conservados |
| 6. Limpieza verificada | R26, R27, R29 | Cada retiro documenta reemplazo o falta de consumidor; sin pérdidas funcionales |
| 7. Endurecimiento API | R19, R20, R30–R32, R35 | Roles, errores, logs, paginación y concurrencia cubiertos |
| 8. Puerta frontend | Ensayo de todos los recorridos necesarios para el portal | Contratos estables y criterios de calidad/publicación satisfechos |

Seguridad y observabilidad pueden abordarse antes si se confirma exposición real. La tabla organiza paquetes de entrega; no propone dejar un defecto sensible activo por conveniencia del calendario.

## 8. Plan de depuración profunda

### Por cada fact

Definir: fuente física, PK de origen, granularidad Silver, reglas de dimensionalidad, campos obligatorios, política de fecha, deduplicación/desempate, cuarentena y salida Gold. Para cada uno de los 15 dominios —cosecha, conteo, ciclos, peladas, clima, pesos, tareo, fisiología, floración, inducción, crecimiento, censo, poda, vegetativa y áreas/plantas— cubrir:

1. Fila válida y suma/medida esperada en SQL.
2. Campo obligatorio ausente, nulo, texto inválido y valor fuera de rango.
3. Dos fundos con códigos operativos iguales; sector ambiguo y geografía desconocida.
4. Variante de layout y columnas nuevas conservadas o rechazadas explícitamente.
5. Duplicado exacto, conflicto de clave, timestamp ausente, empate y orden invertido.
6. Fecha límite, posterior al límite, año ISO y campaña solapada.
7. Segunda carga sin cambios; reenvío de archivo; corrección; reproceso parcial.
8. Fallo antes/después de preparar datos, insertar, marcar estados y registrar cuarentena.
9. Reconciliación de leídos, aceptados, rechazados y duplicados, considerando expansión de una fila Raw a varias filas Silver.

No se debe exigir `leídos = insertados + rechazados` indiscriminadamente: algunas facts expanden estados u órganos y otras agrupan registros. Cada transformación necesita su propia ecuación de reconciliación.

### Proyecciones

- Matriz inválida, estados extra, semanas fuera de rango y valores no finitos.
- Censo inexistente, repetido o de otra vigencia; geografía a nivel cama frente a válvula.
- Peso observado/estimado/histórico y ausencia por cada nivel de fallback.
- Cruce de año ISO, distintos fundos y condiciones a la fecha del corte.
- Cálculo sin persistencia, guardado, publicación, repetición y simulaciones concurrentes.
- Comparación con escenario anterior correcto y diferencia entre ausencia y cero.

### API y runner

- Login válido/inválido, usuario desactivado, rol degradado y token vencido.
- HTTP de error estable sin SQL ni secretos; logs con entradas sintéticas sensibles.
- Listado vacío, última página y página fuera de rango con total estable.
- Solicitudes concurrentes con IDs diferentes y caché con todos los filtros.
- Cola duplicada, lock ocupado, heartbeat vencido, reinicio y recuperación del runner.
- Cancelación cuando el subproceso no imprime; timeout; error de DB al cerrar corrida.
- SSE reconectado sin pérdida/duplicación lógica de eventos, indicando el cursor soportado.
- Exports y cargas grandes con medición de memoria/latencia; no basarse únicamente en muestras pequeñas.

### Migraciones y despliegue

- Instalación vacía y actualización desde una versión anterior conocida.
- Archivo no declarado, limpieza fuera del plan y hash aplicado modificado.
- Error inicial, error de resultado ODBC posterior y fallo de auditoría.
- Reintento, ejecución concurrente, batches con comentarios/literales y cambios operativos fuera de transacción.
- Restauración de respaldo en entorno aislado y comparación de objetos/constraints.

La cobertura de porcentajes debe medirse, no inferirse del número de tests. Priorizar ramas que pueden perder datos, publicar resultados incorrectos o convertir fallos en éxito aparente.

## 9. Reglas para aprobar cada cambio

Cada entrega debe resolver un problema observable y tener criterios de aceptación. Debe declarar si cambia comportamiento o solo estructura; conservar una muestra de referencia; probar el módulo real; ejecutar contrato SQL cuando toque persistencia; y ofrecer una reversión que no dependa de borrar datos confirmados.

Los cambios de fórmulas, granularidad, campaña y definición de planta productiva requieren decisión de negocio. Las rutinas técnicas de empaquetado, serialización y retirada de privados sin consumidor pueden resolverse con evidencia de código y pruebas.

La puerta para el frontend no exige una limpieza perfecta. Exige que identidad, métricas, errores, frescura, correcciones, publicación y permisos tengan significado estable. Las mejoras cosméticas pueden seguir después.

## 10. Qué no propongo ahora

- Reemplazar SQL Server o migrar a microservicios.
- Cambiar pandas por otra librería sin medir el cuello de botella.
- Introducir Redis, Kafka, Airflow o Dagster solo porque el sistema crezca en código.
- Eliminar todas las capturas genéricas o todos los wrappers de compatibilidad de una vez.
- Reescribir migraciones ya registradas y romper sus hashes para que un install pase.
- Borrar scripts operativos sin revisar su uso fuera del repositorio.
- Tratar las recomendaciones del catálogo antiguo como verdades actuales. Por ejemplo, no describe fielmente el frontend ausente, y `asyncio.to_thread` no implica por sí mismo que todas las consultas estén serializadas.

## 11. Decisiones pendientes antes de implementar

1. Unidad de planificación y reglas de correspondencia entre geografía, cama y válvula.
2. Semántica de cada archivo: foto, incremental o corrección.
3. Política estricta de altas MDM y responsable de aprobarlas.
4. Corte temporal de censo, condición y peso; datos futuros permitidos por escenario.
5. Cuándo una estimación es aceptable y cuándo bloquea publicación.
6. Autoridad para publicar una simulación y conservar su historial.
7. Si los roles son jerárquicos o permisos independientes por tarea.
8. Qué jobs externos consumen scripts o funciones que aparecen sin referencias locales.

Con esas respuestas, la primera implementación recomendable es el baseline SQL y los contratos de prueba. Después, conectar las reglas de negocio hoy desconectadas y cerrar MDM/proyecciones; la eliminación de código debe seguir esa evidencia.
