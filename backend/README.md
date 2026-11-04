# Backend (Capa de Servicio de la API)

Bienvenido a la capa intermedia del Data Warehouse de ACP. Este componente está construido con FastAPI y actúa como el puente exclusivo entre los datos consolidados del ETL (Capa Oro) y el Portal Front-End (Centro de Control).

## Propósito del Backend

A diferencia del ETL, que es un proceso pesado, en bloque (batch) y de larga duración, el Backend está optimizado para la velocidad y la seguridad. Su único trabajo es responder a las peticiones HTTP del portal web entregando los datos precisos requeridos para renderizar gráficos, tablas y reportes, todo en milisegundos.

## Características Principales

1. **Lectura de Alto Rendimiento:** Se conecta a la base de datos de salida del ETL — **SQL Server** (vía `ODBC Driver 17 for SQL Server`, reutilizando el engine compartido de `comun/conexion.py`) — para recuperar las vistas materializadas y dimensiones de la Capa Oro, entregándolas a la web en formato JSON. (SQLite solo se usa como *mock* en el perfil de `test`, nunca en `dev`/`prod`.)
2. **Gestión de Cuarentena (Data Governance):** Proporciona los endpoints para que los auditores revisen, corrijan o descarten desde la web aquellos datos que el ETL haya marcado como anómalos o "sospechosos".
3. **Explorador DWH:** Contiene la lógica para la exploración jerárquica de datos, permitiendo al usuario navegar entre años, ciclos fenológicos, fincas y lotes.

## Estructura del Proyecto Backend

- **`/api/`**: Contiene los enrutadores (routers) de FastAPI organizados por dominios de negocio (ej. rutas de cuarentena, explorador, ejecuciones en vivo).
- **`/repositorios/`**: La capa de abstracción de datos. Aquí viven todas las sentencias SQL reales. Mantiene el resto de la aplicación independiente de la estructura exacta de la base de datos.
- **`/schemas/`**: Modelos Pydantic. Sirven para validar estrictamente la forma en que entran o salen los datos (serialización y validación estática).
- **`/servicios/`**: Reglas de negocio del nivel web. Conecta los repositorios con las rutas, añadiendo lógica condicional o manejo de caché.
- **`/migrations/`**: En caso de que el backend requiera sus propias tablas operativas (por ejemplo, para el control de sesiones de usuarios o perfiles), se gestionan aquí.

## Desarrollo Local

Para correr el servidor de la API en tu entorno:

1. Asegúrate de que las dependencias estén instaladas (`pip install -r requirements.txt`).
2. Levanta el servidor con Uvicorn:
   ```bash
   uvicorn main:app --reload
   ```
3. Explora la documentación automática de la API accediendo a `http://localhost:8000/docs`.
