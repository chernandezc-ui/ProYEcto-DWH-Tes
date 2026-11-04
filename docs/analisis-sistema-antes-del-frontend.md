# Diagnóstico del sistema ACP antes del frontend

Fecha: 3 de noviembre de 2026.

## Dictamen

Existe una base considerable: ingesta especializada, modelo dimensional agrícola, homologación, cuarentena, reproceso dirigido y un plano de control separado de la API. Conviene conservar esta arquitectura y endurecer sus contratos antes de desarrollar el portal completo.

La prioridad es que un resultado tenga significado consistente: qué unidad representa, qué fecha de corte usa, qué datos faltan, qué supuestos se aplicaron y si se publicó correctamente. Actualmente hay rutas que pueden devolver una respuesta técnicamente válida con información parcial, estimada o fija sin distinguirla para el usuario.

Se puede definir navegación y prototipos desde ahora. Las pantallas de proyección oficial, comparación histórica y calidad requieren corregir primero los hallazgos de este documento.

## Alcance y límites de la revisión

Revisión del código local de orquestación, cargador Bronce y rutas de archivos, procesador base Silver, contrato de facts y dependencias, MDM, Gold, conexión compartida, configuración y autenticación, API, runner y servicios/repositorios de proyecciones, cuarentena, reinyección y gráficos. También se contrastaron migraciones y documentación.

No se ejecutó el pipeline, ni migraciones, ni comandos de escritura contra SQL Server. No se inspeccionaron datos reales, planes de ejecución, permisos efectivos ni la lista de migraciones instaladas. Los hallazgos de código están separados de las condiciones que requieren confirmar en la base. El DDL versionado describe la intención; no prueba el esquema actualmente desplegado.

No se modificó lógica de aplicación. Este documento es el entregable de análisis.

## 1. Qué producto representa realmente

El proyecto reúne tres responsabilidades:

1. Plataforma de datos agrícolas: llevar archivos de campo a hechos y dimensiones confiables.
2. Centro de operación y gobierno: lanzar corridas, vigilar errores, corregir cuarentena y administrar parámetros.
3. Herramienta de análisis y planificación: explorar producción y calcular proyecciones a seis semanas.

El frontend debe reflejar estas tareas. Una única pantalla de gráficos no permite operar adecuadamente la calidad ni explicar una proyección.

## 2. Flujo completo, paso a paso

### A. Entrada de archivos

`ETL/bronce/rutas.py` define 23 carpetas lógicas de entrada y sus tablas Bronce. Reconoce alias y puede inferir destino por nombre de archivo. Los pendientes se buscan en `ETL/data/entrada`; el mecanismo incluye archivo más reciente por carpeta y marcas locales basadas en tamaño/mtime.

Esto no equivale a una cola durable de todos los archivos ni a idempotencia por contenido. Conviene explicitar si cada Excel es una foto completa, un incremental o una corrección, y qué sucede cuando llegan varios pendientes del mismo dominio.

### B. Validación y persistencia Bronce

`ETL/bronce/cargador.py` adapta layouts específicos, normaliza encabezados, maneja hojas y headers variables, alinea columnas con SQL y conserva campos adicionales mediante `Valores_Raw` en los casos implementados. Agrega metadatos y estado `CARGADO`; inserta mediante lotes con `fast_executemany` y archiva o marca los archivos.

Bronce ya contiene transformaciones estructurales. El original archivado y su identificación son importantes para reconstruir fielmente la fuente. Los errores críticos de layout/enrutamiento detienen el paso a Silver.

### C. Preparación de dimensiones

`ETL/pipeline.py` verifica conexión y objetos críticos, limpia cachés, ingiere archivos y carga personal con comportamiento SCD1 y geografía mediante `dim_geografia_v2`. Después sincroniza y valida camas mediante procedimientos almacenados.

La geografía usa catálogos jerárquicos y versiones; sus claves deben acompañar el dato a través de todas las capas. Reconstruir identidad con números visibles de módulo/turno/válvula pierde información.

### D. Poda y campañas

`Fact_Ciclo_Poda` se ejecuta primero, secuencialmente. Si termina sin error, el pipeline sincroniza períodos de campaña y limpia lookups. Posteriormente lanza el resto de facts en hasta cuatro hilos.

Esta secuencia demuestra una dependencia de negocio: la campaña no es solamente un filtro visual. Debe resolverse con las fechas y la unidad apropiadas. En reprocesos parciales hay que comprobar que se repitan las mismas dependencias necesarias.

### E. Transformación Silver

El catálogo registra 15 facts: poda, cosecha SAP, conteo fenológico, ciclos fenológicos, peladas, clima, evaluación de pesos, tareo, fisiología, floración, inducción floral, crecimiento de brotes, censo, evaluación vegetativa y áreas/plantas.

`BaseFactProcessor` reúne lectura Bronce, normalización, resolución de dimensiones, deduplicación y escritura masiva con tablas temporales. Los rechazos conservan vínculo al origen y preparan cuarentena. Las implementaciones concretas añaden reglas y granularidades propias; no todas deben asumir el mismo grano.

El circuit breaker evalúa tasas de rechazo. Los límites y excepciones deben explicarse por dominio: existe protección para muestras pequeñas y configuración particular. El código contempla persistir trabajo válido antes de elevar ciertos errores de calidad.

### F. Cuarentena y recuperación

La API permite listar, resolver o descartar registros. Resolver guarda el valor corregido, analista y fecha en `MDM.Cuarentena`. La reinyección busca resueltos con ID de origen y vuelve a poner filas Bronce en `CARGADO`.

Reactivar una fila no demuestra que se haya aplicado la corrección ni que haya llegado a Silver. El flujo necesita estados y trazabilidad hasta una carga posterior satisfactoria. En el recorrido revisado, los listeners solo registran eventos; no aplican el valor corregido.

### G. Gold

Las migraciones 68 y 70 convierten/consolidan marts como vistas. En `gold/marts.py`, truncar es un no-op y los supuestos refrescos consultan las vistas y cuentan filas.

Por tanto, si esas migraciones están aplicadas, Gold refleja Silver al consultar. No existe allí una publicación materializada protegida por el final satisfactorio de toda la corrida.

### H. Control y API

La API FastAPI organiza autenticación, salud, ETL, catálogos, auditoría, cuarentena, configuración, reinyección, alertas, analista y proyecciones. Su estructura por rutas, servicios, repositorios y schemas es aprovechable.

Para ETL, la API registra corridas/comandos; un runner separado consume trabajo, coordina locks/heartbeats y ejecuta `pipeline.py` como subproceso. Captura stdout, persiste eventos y expone progreso por SSE. Esta separación permite que una petición HTTP no tenga que esperar todo el procesamiento.

La API utiliza JWT y una jerarquía de roles: viewer, analista MDM, operador ETL y administrador. Conviene validar si el negocio desea que el operador herede también facultades de corrección y simulación.

### I. Proyección de seis semanas

El repositorio extrae conteos, plantas y pesos. El servicio convierte conteos por punto a órganos por planta, distribuye estados mediante una matriz de maduración y calcula aproximadamente:

`kg_semana = suma(órganos_por_planta × fracción_maduración × plantas × peso_baya_kg × fracción_productivas) × factor_semana`

Después aplica márgenes pesimista/optimista y guarda resultados en `Silver.Fact_Proyecciones`. Los factores, estados, diez plantas por punto, márgenes y valores de respaldo requieren validación agronómica y versionado.

El endpoint de ejecución actualmente combina cálculo y persistencia. Para el portal conviene separar simulación, revisión y publicación oficial.

## 3. Hallazgos priorizados

P0: riesgo de pérdida o resultados asignados a unidades equivocadas. P1: comportamiento incorrecto o información engañosa. P2: mantenibilidad y preparación operativa.

### P0 — El runner de migraciones incluye un script de limpieza total

Evidencia: `ETL/tools/migration_runner.py:35,70` solo excluye dos archivos y enumera todos los demás `.sql`. Incluye `ETL/sql_migrations/clear_all_data.sql`, que contiene truncados de datos. Se verificó la inclusión mediante la función de listado extraída por AST, sin ejecutar SQL.

Si el archivo está pendiente, el runner lo intentará ejecutar como una migración. Que una sentencia falle no constituye protección operativa.

Acción: separar mantenimiento destructivo de migraciones, usar un manifiesto explícito y validar despliegue desde una base vacía. El orden alfabético mezcla scripts fechados, DDL y fases. El parser también descarta bloques que empiezan por `--`, aunque contengan SQL después, y el bucle continúa tras errores. Registrar SHA no comprueba cambios posteriores si la selección de pendientes solo usa nombres.

Aceptación: la limpieza nunca aparece en el plan de migración; el despliegue falla ante una migración fallida; ningún bloque SQL se omite por tener comentarios iniciales; el esquema resultante se verifica.

### P0 — Las proyecciones pierden la identidad geográfica completa

Evidencia: `backend/servicios/servicio_proyecciones.py:148` agrupa solo módulo/turno/válvula/variedad, sin fundo ni condición. Selecciona etiquetas del primer registro. En `repo_proyecciones.py:369`, el guardado resuelve geografía con `TOP 1` por módulo/turno/válvula, sin fundo, cama ni vigencia.

Reproducción en memoria: dos filas de fundos A y B con los mismos números locales generan un único grupo en el servicio. La ocurrencia y magnitud sobre producción requieren revisar datos reales.

Acción: conservar IDs dimensionales desde extracción hasta cálculo y guardado, y declarar el grano exacto de la proyección. Si agrega camas u otras unidades, hacerlo explícitamente a una unidad de planificación estable.

Aceptación: dos fundos con iguales números locales permanecen separados y se guardan en sus claves correspondientes, incluidas versiones históricas cuando apliquen.

### P0 — El reproceso elimina el destino antes de asegurar su reemplazo

Evidencia: `ETL/pipeline.py:446,524`. La preparación reabre Bronce y elimina la fact destino mediante una transacción que termina antes de ejecutar el procesador.

Si falla la reconstrucción, el estado previamente publicado ya puede haber desaparecido. Con vistas Gold esto se hace visible durante el reproceso y tras un fallo.

Acción: reconstruir en staging, validar y reemplazar/publicar de forma atómica; alternativamente diseñar un reemplazo transaccional viable con límites claros. Asociar versiones/corridas a lo publicado.

Aceptación: un error inducido al reconstruir mantiene consultable la última versión aprobada.

### P1 — Bloquear el refresco Gold no bloquea la visibilidad de cambios

Evidencia: `ETL/gold/marts.py:67` y migraciones 68/70. El código puede omitir el chequeo final de marts, pero una vista ya lee las tablas Silver modificadas. Algunas consultas del backend leen Silver directamente y usan `NOLOCK`.

Acción: decidir conscientemente entre datos operativos en curso y versión analítica publicada. Para tableros oficiales, usar snapshot/versionado o publicación materializada. Para seguimiento operativo, devolver estado parcial y calidad explícita. RCSI no crea por sí solo una versión coherente de toda la corrida.

Aceptación: una corrida fallida no altera los totales oficiales; la UI distingue información en proceso de información publicada.

### P1 — Cuarentena: el filtro de estado no forma parte de la caché

Evidencia: `backend/servicios/servicio_cuarentena.py:29,40`. El repositorio recibe `estado_filtro`, pero la clave solo usa página, tamaño y tabla.

Impacto: consultas consecutivas para estados distintos pueden devolver la primera respuesta cacheada durante el TTL.

Acción: incluir todos los filtros normalizados en la clave. Verificar secuencias PENDIENTE → RESUELTO y viceversa.

### P1 — Resolver y reinyectar no cierra el circuito de corrección

Evidencia: `repo_cuarentena.marcar_resuelto` guarda `Valor_Corregido`; `repo_reinyeccion.reinyectar_en_bronce` solo modifica `Estado_Carga`. No consume ese valor para corregir la fila. Los candidatos se seleccionan por RESUELTO, sin transición durable que pruebe su consumo.

Además, un origen lógico puede mapear a varias tablas físicas y el código intenta actualizar el mismo ID en cada destino. Los IDs locales pueden coincidir entre tablas: no basta asumir que solo existirá en la correcta.

Acción: registrar origen físico exacto, columna, corrección tipada, versión y estado de aplicación. Aplicar override o corrección controlada, validar la fila completa y enlazar el reproceso exitoso. Una fila con varios errores requiere resolverlos de forma coherente.

Aceptación: corregir un registro logra un cambio verificable en Silver; repetir la reinyección no produce cambios adicionales ni toca otra fuente con un ID coincidente.

### P1 — La matriz inválida puede llegar al cálculo

Evidencia: existe `validar_matriz_inputs`, pero `ejecutar_proyeccion` llama directamente a `cerrar_matriz`. El schema permite floats sin límites de proporción y márgenes sin relación validada.

Reproducción aislada: `{fase_2: {1: 0.8, 2: 0.8}}` cierra en `[0.8, 0.8, 0, 0, 0, 0]`; el validador detecta 160%, pero esa validación no está conectada al camino de ejecución.

Acción: validar antes de calcular y antes de guardar la matriz. Comprobar estados, semanas, proporciones finitas, suma y orden de márgenes; validar fecha real. Definir el significado de varios `None`.

### P1 — Plantas, pesos y condición carecen de un corte temporal consistente

Evidencia: `repo_proyecciones.extraer_datos_granulares` suma censo sin restringir fecha/campaña, asigna productivas a 1.0 y obtiene condición de la última cosecha sin limitarla al cutoff. Pesos consulta semanas futuras respecto de la base y, si faltan, un histórico por semana sin límite de año. El lookup recibe semanas sin preservar el año de cada observación.

Impacto: posible suma de distintos censos, uso de condiciones posteriores y filtración de información futura en una evaluación histórica. La interpretación exacta depende del contrato agronómico pendiente.

Acción: definir fuente y vigencia de cada entrada, escoger censo aplicable, diferenciar peso observado/previsto/histórico, y preservar fecha/año ISO. La validación de integridad debe usar los mismos filtros del cálculo: actualmente `peladas` comprueba existencia global en censo y el parámetro condición no se aplica.

### P1 — Persistencia de proyecciones parcial y sin historial de simulaciones

Evidencia: `repo_proyecciones.guardar_proyeccion` hace un comando/transacción por fila, acumula errores y saltos, y usa MERGE por tiempo/geografía/variedad/escenario. El servicio ignora su resumen. Cutoff/modelo no forman parte de la identidad de la simulación.

Impacto: una respuesta puede mostrar cálculo completo aunque se guardara parcialmente; repetir una simulación puede sobrescribir resultados anteriores para semanas coincidentes.

Acción: introducir ID de simulación, autor, versión, cutoff, parámetros y snapshot de entradas; guardar en lote con atomicidad. Publicar oficialmente mediante una operación separada y devolver estado de persistencia.

### P1 — Indicadores con valores fijos o unidades equivocadas

Evidencia: `servicio_analista_charts.py:146` llama `rendimiento_tha` a toneladas sin dividir entre hectáreas; en :157–158 entrega lluvia y temperatura como 0. En :176–177 la comparación previa y delta son constantes. `rutas_proyecciones.py:70–72` fija anterior=0, variación=0 y tendencia=Estable.

Acción: implementar las métricas o devolver ausencia explícita con motivo. El frontend no debe interpretar estos ceros como observaciones. Mostrar kg, t y t/ha con contratos distintos.

También `SYSDATETIME() AS Fecha_Actualizacion` en las vistas Gold representa la hora de consulta, no la última carga del dato. Obtener frescura desde auditoría/versión publicada.

### P1 — Telemetría secuencial para trabajo paralelo

Evidencia: `backend/runner/ejecutor.py:42,358` interpreta encabezados textuales y mantiene un único paso activo. El pipeline ejecuta 14 facts en paralelo y los logs pueden intercalarse.

Impacto: no es posible asociar de forma fiable una métrica o error a su fact usando solo el paso activo. Puede afectar duración, avance y diagnóstico del futuro monitor.

Acción: eventos estructurados con corrida, fact/paso, tipo, timestamp y métricas. Mantener estados independientes por tarea y definir progreso con denominadores explícitos.

### P2 — La validación de carga web todavía es una implementación preliminar

`servicio_ingesta.validar_csv_polars` lee todo el archivo y devuelve sus filas en memoria. Sus reglas son genéricas y contienen validaciones de ejemplo; no equivalen a los layouts y reglas del cargador Excel. El nombre de tabla no garantiza una validación real del contrato de destino.

Acción: unificar contratos de layout y reglas, limitar tamaño/filas, devolver resumen y muestra paginada, y diseñar staging/confirmación con ID de carga. No presentar esta ruta como ingesta integral ya terminada.

### P2 — Documentación, dependencias y reproducibilidad

- El README referencia `Portal_MDM_NEXTJS`, ausente en esta copia.
- Documenta `uvicorn main:app`; el objeto real se llama `aplicacion`.
- Hay referencias a 8000/3000 frente al puerto backend por defecto 8810.
- Gold se describe como materializado aunque el código y migraciones recientes usan vistas.
- Se promete SQLite de test, pero la conexión backend delega al engine SQL Server y su fixture indica BD de desarrollo.
- Los requirements tienen diferencias y rangos amplios; por ejemplo, Polars y statsmodels están en backend y no en raíz. El event bus usa Blinker sin dependencia explícita en esos archivos.
- No existe metadata Git en esta copia, lo que limita establecer versión y revisar cambios mediante diff.

Acción: documentar arranque real, Python soportado, configuración ejemplo sin secretos y dependencias reproducibles por componente. Separar pruebas unitarias de integración con SQL de prueba.

## 4. Qué conviene conservar

- Separación API/runner/ETL y persistencia del plano de control.
- Catálogo central de facts y reprocesos por dominio.
- Módulo común de conexión y capas rutas/servicios/repositorios.
- Deduplicación en lote, trazabilidad al origen y cuarentena estricta.
- Modelo agrícola rico en campañas, geografía, variedades y estados.
- Protección de esquema y circuit breaker.

No hace falta introducir microservicios ni reescribir todo para corregir los problemas descritos. Las fronteras existentes permiten cambios focalizados.

## 5. Orden de mejora propuesto

### Etapa 1 — Proteger datos e identidad

1. Excluir limpieza del runner y definir un plan de migraciones reproducible.
2. Declarar grano e IDs de cada fact/proyección; conservarlos de extremo a extremo.
3. Sustituir borrado previo por reconstrucción/publicación segura.
4. Corregir la caché de cuarentena y la aplicación de correcciones.

Salida: errores de proceso no destruyen la última versión válida; no se mezclan unidades; la recuperación corrige datos de verdad.

### Etapa 2 — Hacer defendible el cálculo

1. Validar matriz, márgenes y fechas.
2. Definir cutoff y vigencia de conteos/censo/pesos/condición.
3. Mostrar supuestos y cobertura; establecer cuándo bloquear y cuándo permitir estimación.
4. Versionar simulaciones y separar cálculo de publicación.
5. Sustituir indicadores fijos por valores reales o ausencia explícita.

Salida: una simulación puede reproducirse y explicarse; sus resultados guardados coinciden con los entregados.

### Etapa 3 — Contrato del portal y operación

1. Eventos ETL estructurados y estados por tarea concurrente.
2. API estable de filtros jerárquicos y métricas con unidades, calidad y frescura.
3. Pruebas HTTP de roles, errores, paginación, SSE y contratos.
4. Ensayo de instalación/restauración y medición de consultas sobre volúmenes representativos.

Salida: frontend puede consumir contratos estables y representar fallos/reconexión/datos parciales correctamente.

## 6. Forma propuesta para el frontend

| Área | Pregunta del usuario | Pantallas principales | Condición previa |
|---|---|---|---|
| Inicio | ¿Puedo confiar en lo disponible? | Última publicación, frescura, cobertura y alertas accionables | Frescura y calidad reales |
| Operación | ¿Qué está procesando y dónde falló? | Corridas, detalle por fact, eventos, reproceso y cancelación | Telemetría concurrente fiable |
| Calidad | ¿Qué dato debo corregir? | Bandeja, detalle origen/regla/corrección, reinyección y resultado | Corrección aplicada e idempotente |
| Exploración | ¿Qué pasó en mi unidad agrícola? | Filtros, series, tabla y exportación | Grano y métricas coherentes |
| Proyecciones | ¿Qué espero cosechar y bajo qué supuestos? | Cobertura, matriz, simulación, comparación y publicación | Modelo temporal y persistencia corregidos |
| Administración | ¿Quién puede cambiar qué? | Usuarios, catálogos, parámetros y auditoría | Matriz de permisos acordada |

Una sola aplicación puede alojar estas áreas con navegación por rol. Los filtros deberían usar IDs estables y dependencias: fundo → sector → módulo/submódulo → turno → válvula → cama cuando corresponda; campaña, variedad y condición deben respetar su vigencia.

No empezar por un constructor libre de dashboards. Primero asegurar vistas de trabajo concretas y métricas bien definidas. El constructor existente puede incorporarse después como función avanzada.

Flujo de proyección recomendado:

`Seleccionar corte/unidad → revisar cobertura → ajustar supuestos → calcular simulación → inspeccionar detalle → comparar → publicar versión`

Estados de UI necesarios: sin datos, incompleto, estimado, en proceso, fallido y publicado. El cero debe reservarse para una medición o cálculo que realmente valga cero.

## 7. Verificación realizada y siguiente validación

Se ejecutó:

`python -m pytest ETL/tests/test_utils_capa1.py ETL/tests/test_circuit_breaker.py ETL/tests/test_dedup_vectorizado.py -q -p no:cacheprovider`

Resultado: **47 pruebas aprobadas**. Hubo un aviso de configuración futura del plugin pytest-asyncio. Estas pruebas cubren utilidades, rechazo/calidad y deduplicación; no certifican la integración completa.

También se reprodujeron en memoria, sin SQL, la mezcla de dos fundos bajo el agrupamiento actual, el cierre de una matriz con suma de 160% y la inclusión del script de limpieza en el listado de migraciones. Se extrajeron funciones por AST para evitar inicialización de servicios o conexiones.

La validación siguiente debe usar una base SQL Server aislada: instalación desde cero; corrida con archivos representativos; segunda corrida idempotente; fallo durante reproceso; corrección y reinyección; dos fundos con códigos locales repetidos; corte histórico sin datos futuros; guardado fallido a mitad de simulación; y reconexión del monitor. No ejecutar indiscriminadamente las suites actuales: algunas usan la BD de desarrollo y otras contienen lógica espejada que no valida directamente la implementación.

## Decisiones pendientes de negocio

1. ¿Cuál es la unidad exacta de planificación y qué dimensiones distinguen dos resultados?
2. ¿Qué significa cada archivo: foto, incremental o corrección?
3. ¿Qué medición define plantas totales/productivas y su vigencia?
4. ¿Los pesos de semanas futuras son previsiones permitidas o datos observados usados para retrospectiva?
5. ¿Qué faltantes admiten estimación y cuáles bloquean una proyección oficial?
6. ¿Quién publica un escenario y cómo se conserva el histórico?

Estas decisiones afectan al modelo y a los contratos. Conviene resolverlas antes de fijar los formularios y gráficos definitivos.
