# Data Warehouse y Proyecciones ACP

Bienvenido al repositorio central del Data Warehouse para Proyecciones de ACP. Este proyecto tiene como objetivo consolidar, limpiar y servir datos maestros e históricos (como kilos procesados, ciclos fenológicos y de poda) para permitir la toma de decisiones informadas mediante un portal de control avanzado.

Este repositorio es un "monorepo" que agrupa todas las piezas clave del ecosistema de datos, garantizando que el procesamiento, el servicio de API y la interfaz de usuario se mantengan siempre sincronizados.

## Arquitectura del Proyecto

El sistema está dividido en tres componentes principales que trabajan en cadena:

1. **ETL (Motor de Procesamiento de Datos)**
   Se encarga de la extracción, transformación y carga de los datos crudos. Aplica reglas de negocio, limpia anomalías (como kilos atípicos o falta de geografías) y consolida la información en capas (Bronce, Plata y Oro). 
   [Leer más sobre el ETL](./ETL/README.md)

2. **Backend (API y Capa de Servicio)**
   Una API construida en Python (FastAPI) que lee los datos consolidados en la capa de Oro (**SQL Server**, vía `ODBC Driver 17 for SQL Server` reutilizando `comun/conexion.py`; SQLite solo se usa como *mock* en el perfil `test`) y los expone de forma segura. Maneja la lógica de validación, cuarentena de datos anómalos y provee la información en tiempo real.
   [Leer más sobre el Backend](./backend/README.md)

3. **Portal MDM (Centro de Control)**
   El frontend Next.js mencionado en documentos históricos no está incluido en este checkout. El lanzador prepara los componentes Python presentes: API y runner del ETL.

## Guía de Inicio Rápido

Para ejecutar las pruebas locales sin SQL Server y habilitar integración solo
con un destino aislado, consulta la [guía de pruebas](docs/pruebas-locales.md).

La API, el runner, el ETL y las pruebas comparten **un entorno virtual, un requirements.txt y un .env en la raíz**.

### Requisitos Previos
- Python 3.10 o superior (validado en Python 3.12).
- Git instalado.

### Pasos para Ejecutar
1. Instalar una vez, desde la raíz:
   ```bash
   python instalar.py
   ```
   Reutiliza el entorno virtual activo o crea `.venv`. Instala la lista global y crea `.env` solo si no existe, con una clave JWT local aleatoria y configuración inicial sin BD. No sobrescribe valores existentes.

2. Arrancar desde la misma raíz:
   ```bash
   python acp_start.py
   ```
   Selecciona `.venv` automáticamente si se invoca con Python del sistema; con un entorno virtual activo conserva ese intérprete. En Windows también se puede usar `INICIAR ACP.bat`.

3. Para conectar SQL Server, editar únicamente el `.env` global: `DB_*`, `ACP_ENTORNO=dev` y `ACP_RUNNER_ACTIVO=true`. El driver ODBC y la instancia SQL son requisitos externos a pip. El runner arranca después de comprobar conectividad de la API a la BD; no se ejecutan migraciones automáticamente.

La API usa el puerto definido por `ACP_PUERTO` (8810 por defecto). `python acp_start.py --comprobar` arranca, comprueba liveness y cierra los procesos propios; `--sin-interaccion` mantiene los servicios sin menú. Con la configuración sin BD, readiness devuelve 503 y el runner permanece deshabilitado.

Las variables del sistema tienen prioridad sobre `.env`. Los antiguos `.env` dentro de backend/ o ETL/ ya no se leen. Para trasladar una configuración existente, copiar sus valores al archivo raíz de forma local, sin compartir secretos ni versionarlo.

Más detalles: [configuración global](docs/configuracion-global.md).
# ProYEcto-DWH-Tes
