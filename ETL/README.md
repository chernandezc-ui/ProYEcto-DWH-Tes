# Motor ETL (Extracción, Transformación y Carga)

Bienvenido a la capa de procesamiento de datos del proyecto ACP. Este componente es el corazón analítico del ecosistema. Su propósito principal es tomar datos crudos (archivos CSV sueltos, reportes históricos), limpiarlos exhaustivamente y convertirlos en información confiable y estructurada lista para ser consumida.

## ¿Qué problema resuelve?
Los datos de origen del campo (kilos cosechados, conteos fenológicos, registros de poda) suelen venir con inconsistencias: IDs no coincidentes, datos duplicados, o métricas fuera de rango lógico. Este ETL aplica una serie de "Reglas de Negocio" para auditar y sanear cada registro antes de que llegue a los tableros de control.

## Arquitectura por Capas (Medallion Architecture)

El procesamiento de datos sigue un modelo de madurez en tres fases principales:

1. **Capa Bronce (Ingesta):**
   - Recibe los datos originales sin ninguna modificación estructural.
   - Actúa como un respaldo del estado original para auditorías.
   - Lee archivos ubicados en `data/entrada`.

2. **Capa Plata (Limpieza y Auditoría):**
   - Aquí ocurre la magia. Se aplican scripts de limpieza y normalización.
   - Se validan claves foráneas (ej. asegurando que el ID del campo exista en el catálogo de geografía).
   - Los datos que no cumplen las reglas estrictas se separan en un "backlog" o "cuarentena" para revisión manual, evitando que corrompan los reportes finales.

3. **Capa Oro (Servicio y Agregación):**
   - Los datos totalmente saneados se estructuran en Modelos Dimensionales (Esquema Estrella).
   - Genera tablas de Hechos (Fact Tables) y Dimensiones (Dim Tables) optimizadas para consultas ultra rápidas.
   - Estos resultados finales se materializan en SQL Server (capa de Oro), que es la que el Backend leerá. (SQLite/CSV solo aparecen como mock de test o export puntual, no como almacén de Oro.)

## Estructura del Directorio

- **`/bronce/`**: Lógica para cargar y validar esquema básico inicial.
- **`/silver/`**: Reglas de limpieza complejas, manejo de cuarentena y normalización.
- **`/tools/`**: Herramientas auxiliares, scripts de migración y auditorías sueltas.
- **`/tests/`**: Pruebas unitarias para asegurar que los procesadores no fallen con datos inesperados.

## Ejecución

El ETL está diseñado para ejecutarse de manera programada o manual a través del script en la raíz del proyecto `ejecutar_etl_acp.bat`. Si necesitas correr una etapa específica para depuración, puedes ejecutar los scripts principales de `silver` o `bronce` usando tu entorno de Python (activando `.venv` previamente).
