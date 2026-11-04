# Instalación y configuración global de ACP

Los componentes Python comparten dependencias y configuración por proyecto.
La API, el runner y el subproceso ETL siguen separados para conservar sus
límites de ejecución y transacción; no necesitan instalaciones independientes.

```bash
# Primera instalación desde la raíz
python instalar.py
# Arranque habitual
python acp_start.py
```

El instalador usa el entorno virtual que ya esté ejecutándolo o crea `.venv`
en la raíz. El lanzador y el runner usan ese mismo Python mediante
`sys.executable`. Si se usa un entorno virtual externo, ejecutar ambos comandos
con su Python o activarlo antes; con Python del sistema el lanzador busca `.venv`.

`requirements.txt` contiene la unión de las dependencias del proyecto.
`backend/requirements.txt` conserva solo una inclusión del archivo raíz para
compatibilidad. No hay una segunda lista que mantener. El instalador es
repetible y solo se necesita al preparar el entorno o cambiar dependencias.

El archivo `.env` se crea a partir de `.env.example` únicamente cuando no existe.
Se genera una clave JWT local aleatoria sin imprimirla; `.env` está excluido
de Git. No copiarlo a documentos ni subirlo al repositorio. En despliegues
administrados, las variables inyectadas por el entorno mantienen prioridad.

## Lectura y precedencia

`comun/configuracion.py` define los campos de conexión y la ruta absoluta al
`.env` raíz, independiente del directorio de ejecución. `Settings` del backend
hereda ese contrato y añade sus parámetros HTTP, JWT, logging y runner.
`comun/conexion.py` usa el mismo contrato para crear cada engine por proceso.

La precedencia, de mayor a menor, es:

1. Parámetros explícitos al construir la configuración o cadena de conexión.
2. Variables del proceso/sistema.
3. `.env` de la raíz.
4. Defaults declarados, como el nombre del driver ODBC.

Servidor y base son obligatorios: ya no se adivina un servidor habitual si
faltan. Un usuario vacío significa Windows Auth; no vuelve a tomar un usuario
anterior del archivo. La configuración de conexión se cachea por proceso;
reiniciar los servicios después de editar `.env`. `resetear_engine` invalida
también esa configuración para pruebas y usos explícitos.

Los `.env` en subcarpetas ya no se leen. Las plantillas antiguas se conservan
como avisos hacia la raíz. No se eliminan ni migran automáticamente archivos
locales existentes: trasladar los valores deliberadamente y resolver conflictos
antes de arrancar servicios.

## Desarrollo sin base de datos

La instalación nueva deja `ACP_ENTORNO=test`, driver `ACP_OFFLINE_NO_DATABASE`
y `ACP_RUNNER_ACTIVO=false`. Esto permite arrancar la API y sus documentos,
con readiness 503 esperado. El driver deliberadamente inexistente impide
intentos de conexión en este modo. El perfil test por sí solo no crea un mock.
Las pruebas pytest conservan su bloqueo SQL independiente.

```bash
python acp_start.py --comprobar
python -m pytest -q
```

`--comprobar` comprueba el arranque y liveness de la API; no certifica login,
reglas de negocio ni integridad del DWH. Cierra únicamente procesos creados
por el lanzador. Un puerto ocupado produce un error, sin matar procesos ajenos.
`--sin-interaccion` mantiene los servicios en primer plano sin menú.

## Uso con SQL Server

Configurar `DB_SERVIDOR`, `DB_NOMBRE`, `DB_DRIVER` y autenticación en el archivo
global o en variables del entorno. El servidor SQL, sus esquemas/datos y el
driver ODBC instalado son prerrequisitos externos a la instalación Python.
Después establecer `ACP_ENTORNO=dev` y `ACP_RUNNER_ACTIVO=true` para arrancar
API y runner con un comando. El launcher comprueba readiness de la API antes
de iniciar el consumidor de la cola. No aplica migraciones ni lanza una carga
completa automáticamente; un runner habilitado sí puede consumir comandos
pendientes de la instancia configurada.

Las pruebas de integración mantienen selección explícita de servidor/base
aislada; ver [pruebas locales](pruebas-locales.md). SQL Server y el comportamiento
nativo de Windows quedan pendientes de validación en sus entornos respectivos.

## Validación de esta entrega

En Python 3.12/Linux: **208 pruebas aprobadas y 9 omitidas** por SQL Server.
Incluyen precedencia de configuración, directorios de ejecución diferentes,
conservación de `.env`, selección del intérprete, espera de readiness y cierre
de la API real al ejecutar `--comprobar`. Se probó el instalador con la lista
global y su repetición conservó el archivo local sin cambios. Las dependencias
ya instaladas se reutilizaron en el mismo entorno virtual.
