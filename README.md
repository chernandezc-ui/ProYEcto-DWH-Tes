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
   Una interfaz web moderna construida con Next.js y React. Actúa como el centro de mando donde los usuarios pueden visualizar tableros de control, auditar los datos procesados, gestionar registros en cuarentena y ejecutar simulaciones de proyecciones.
   [Leer más sobre el Portal](./Portal_MDM_NEXTJS/README.md)

## Guía de Inicio Rápido

Para ejecutar las pruebas locales sin SQL Server y habilitar integración solo
con un destino aislado, consulta la [guía de pruebas](docs/pruebas-locales.md).

Para levantar el ecosistema completo en tu entorno local de forma rápida, puedes utilizar los scripts automatizados ubicados en la raíz del proyecto.

### Requisitos Previos
- Python 3.9 o superior.
- Node.js 18 o superior.
- Git instalado.

### Pasos para Ejecutar
1. **Inicializar todo el entorno:** 
   Simplemente ejecuta el script por lotes que configurará las variables de entorno, levantará el Backend y preparará el ETL:
   ```cmd
   INICIAR ACP.bat
   ```

2. **Ejecutar el pipeline de datos:**
   Si deseas procesar nuevos archivos o correr el ETL desde cero:
   ```cmd
   ejecutar_etl_acp.bat
   ```

3. **Acceder al sistema:**
   Una vez que los servicios estén corriendo, el portal web y la API estarán disponibles en tus puertos locales (usualmente `localhost:3000` para el Portal y `localhost:8000` para el Backend).
# ProYEcto-DWH-Tes
