# Proyecciones: validación y cálculo separados

Esta entrega corresponde al primer bloque de proyecciones: validar escenarios,
aislar el cálculo y comunicar fallos de guardado. No cambia fórmulas agrícolas,
consultas SQL, esquema de persistencia ni el alcance de desarrollo sin BD.

## Responsabilidades

- `backend/dominio/proyecciones.py` contiene normalización, validación y cálculo
  puro sobre los tres DataFrames recibidos. No importa repositorios, configuración,
  caché ni conexión. Puede utilizarse sin leer ni guardar datos externos.
- `backend/servicios/servicio_proyecciones.py` valida antes de leer fuentes,
  delega el cálculo y comprueba el resultado del guardado. Reexporta los helpers
  existentes para conservar sus consumidores.
- Las rutas y schemas usan la misma validación canónica. Se mantienen las rutas,
  permisos y formatos exitosos de respuesta. La ejecución HTTP sigue calculando
  y guardando como antes; no se añadió un cambio implícito a simulación sin guardado.

## Validación activa

Antes de consultar o guardar se comprueban fecha real en formato YYYYMMDD,
márgenes finitos no negativos y ordenados, y la matriz:

- Al menos un estado conocido; se admiten subconjuntos de los estados existentes.
- Semanas entre 1 y 6, con claves enteras o sus strings JSON. No se aceptan
  semanas repetidas después de normalizar ni booleanos como porcentajes/semanas.
- Porcentajes finitos dentro de [0, 1]. `None` y semanas ausentes conservan el
  cierre residual secuencial existente.
- La suma conocida y el resultado del cierre no exceden 1 más la tolerancia
  histórica de 1e-6. Esto también evita un cierre como W1=None, W2=0.2 que antes
  podía repartir un total superior al 100%.

Los datos inválidos devuelven HTTP 422. No se imponen límites nuevos como
pesimista<=1<=optimista, ni se exige completar los siete estados. El caso vacío
de fuentes válidas conserva DataFrames vacíos y no intenta guardar.

## Errores de persistencia y HTTP

El servicio exige que el resumen del repositorio confirme todas las filas
esperadas, cero saltadas y ninguna incidencia. Un resumen ausente/incompleto,
o un error de guardado de matriz, produce HTTP 503 en lugar de éxito aparente.
Los HTTPException existentes conservan su estado y los errores desconocidos
usan el manejador global 500 con mensaje seguro y request_id. Las rutas ya no
exponen `str(error)` de excepciones internas.

**Límite:** el repositorio todavía confirma por fila. Detectar un guardado parcial
y devolver 503 no revierte lo ya confirmado. La transacción de toda una simulación,
su versionado y su verificación con SQL Server aislado pertenecen al siguiente
bloque. No se afirma atomicidad SQL en esta entrega.

## Comportamiento conservado y decisiones pendientes

Se conservan los coeficientes, reparto por semanas, redondeo, prioridad de pesos,
defaults de plantas/peso, separación de fundos e IDs de origen. No se modificaron
los cortes temporales del censo/pesos, la interpretación del año ISO ni las
comparaciones históricas que siguen usando constantes en la respuesta.
Esas decisiones necesitan contratos de negocio y pruebas de persistencia;
la extracción de un cálculo puro no las considera resueltas.

## Verificación

Las pruebas nuevas cubren cálculo histórico, independencia de infraestructura,
validación previa a I/O, HTTP, permisos y errores de guardado con repositorios
sustituidos. La regresión de separación de fundos conserva sus aserciones; su
mock de guardado ahora devuelve el resumen real del contrato en lugar de un
Mock sin datos. No se debilitaron las comprobaciones de resultados.

La integración SQL Server permanece pendiente y no se ejecuta por defecto.
Comando de pruebas desde la raíz: `python -m pytest -q`.

Resultado de la suite completa: **323 aprobadas, 9 omitidas**, sin fallos.
Las 115 pruebas nuevas incluyen siete caracterizaciones ejecutadas sobre el
servicio anterior y sobre el refactor con resultados idénticos. La revisión
independiente adicional no encontró bloqueos en el alcance local. No se
instalaron dependencias ni se modificó el borrador del entorno.

Estado: **APROBADO para validación y separación del cálculo sin BD**.
La persistencia transaccional, versiones de simulación y reglas temporales
siguen pendientes; no se presentan como verificadas mediante mocks.
