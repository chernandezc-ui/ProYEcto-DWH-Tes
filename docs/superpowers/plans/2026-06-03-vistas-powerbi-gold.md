# Vistas legibles PowerBI sobre Gold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear 13 vistas `PowerBI.vw_*` desnormalizadas que reemplazan los IDs crudos de los Marts `Gold.*` por columnas legibles (fechas, nombres de campaña, geografía completa, variedad, etc.) para que Power BI muestre datos entendibles en vez de números.

**Architecture:** Un esquema nuevo `PowerBI` que contiene solo vistas (`CREATE OR ALTER VIEW`). Cada vista hace `LEFT JOIN` desde su Mart base hacia las dimensiones de `Silver` y proyecta únicamente columnas de texto/fecha, eliminando los `ID_*` de lookup (conserva la PK surrogate del Mart). Se entrega como un script SQL idempotente versionado en `ETL/sql_migrations/` y un verificador Python.

**Tech Stack:** SQL Server (T-SQL), esquema medallion Gold/Silver. Conexión: server `.`, DB `ACP_DataWarehose_Proyecciones`, Windows Auth, `ODBC Driver 17`. Python 3.12 en `.venv` con `pyodbc` para verificación.

---

## File Structure

- **Create:** `ETL/sql_migrations/fase20_vistas_powerbi.sql` — toda la DDL (schema + 13 vistas). Un solo archivo porque son artefactos cohesivos que se versionan y aplican juntos.
- **Create:** `ETL/sql_migrations/_verificar_fase20.py` — verificador idempotente (existencia, conteos, ausencia de `ID_*` de lookup).

Rutas relativas a la raíz `D:\Proyecto2026\ACP_DWH\ACP Proyecciones`.

### Bloques de join reutilizables (referencia)

Estos bloques se repiten textualmente dentro de cada vista que los necesita (las vistas no comparten código).

**Geografía completa** (para marts con `ID_Geografia`):
```sql
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo
```
Columnas de salida de geografía:
```sql
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector,
    mc.Modulo,
    mc.SubModulo,
    mc.Tipo_Conduccion,
    vc.Valvula,
    cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo,
    g.Nivel_Granularidad,
```

**Tiempo / Campaña / Variedad:**
```sql
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
```
Columnas:
```sql
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    v.Nombre_Variedad AS Variedad, v.Breeder,
```

---

## Task 1: Crear el esquema y el encabezado del script

**Files:**
- Create: `ETL/sql_migrations/fase20_vistas_powerbi.sql`

- [ ] **Step 1: Crear el archivo con encabezado idempotente del esquema**

```sql
/* ============================================================================
   Fase 20 — Vistas legibles para Power BI (capa de consumo sobre Gold)
   Reemplaza IDs crudos por columnas legibles. Idempotente.
   Aplicar:  sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -i fase20_vistas_powerbi.sql
   ========================================================================== */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'PowerBI')
    EXEC('CREATE SCHEMA PowerBI');
GO
```

- [ ] **Step 2: Aplicar y verificar que el esquema existe**

Run:
```powershell
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -i "ETL\sql_migrations\fase20_vistas_powerbi.sql"
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -Q "SELECT name FROM sys.schemas WHERE name='PowerBI'"
```
Expected: imprime `PowerBI`.

> Si `sqlcmd` no está disponible, usar `.\.venv\Scripts\python.exe` con `pyodbc` ejecutando el contenido del archivo (split por `GO`). El verificador del Task 6 ya hace esto.

- [ ] **Step 3: Commit**

```bash
git add "ETL/sql_migrations/fase20_vistas_powerbi.sql"
git commit -m "feat(powerbi): crear esquema PowerBI para vistas de consumo"
```

---

## Task 2: Vistas estrella estándar (Tiempo+Campaña+Geografía+Variedad)

Estas 6 vistas comparten el mismo patrón de joins. Cada una proyecta sus métricas propias. Añadir al final del archivo `fase20_vistas_powerbi.sql`.

**Files:**
- Modify: `ETL/sql_migrations/fase20_vistas_powerbi.sql` (append)

- [ ] **Step 1: vw_Cosecha** (usa `Turno` propio del Mart, no el de geografía)

```sql
CREATE OR ALTER VIEW PowerBI.vw_Cosecha AS
SELECT
    m.ID_Mart_Cosecha,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Turno,
    m.Condicion,
    m.Fecha_Cosecha,
    m.Fecha_Evento,
    m.Kg_Neto_Real, m.Kg_Brutos, m.Kg_Neto_MP,
    m.Kg_Proyectados, m.Kg_Proyectado,
    m.Pct_Cumplimiento, m.Cantidad_Jabas, m.Peso_Promedio_Jaba_kg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Cosecha m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 2: vw_Censo_Plantas**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Censo_Plantas AS
SELECT
    m.ID_Mart_Censo,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Estado_Planta,
    m.Cantidad,
    m.Linea_Raw,
    m.Fecha_Actualizacion
FROM Gold.Mart_Censo_Plantas m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 3: vw_Ciclo_Poda**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Ciclo_Poda AS
SELECT
    m.ID_Mart_Poda,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tipo_Evaluacion,
    m.Tallos_Planta_Total, m.Longitud_Tallo_Total, m.Diametro_Tallo_Total,
    m.Ramilla_Planta_Total, m.Tocones_Planta_Total, m.Cortes_Defectuosos_Total,
    m.Altura_Poda_Total, m.N_Muestras,
    m.Fecha_Actualizacion
FROM Gold.Mart_Ciclo_Poda m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 4: vw_Evaluacion_Vegetativa**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Evaluacion_Vegetativa AS
SELECT
    m.ID_Mart_Vegetativa,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Piso,
    m.Semanas_Despues_Poda_Promedio, m.Altura_Promedio,
    m.Tallos_Basales_Promedio, m.Tallos_Basales_Nuevos_Promedio,
    m.Muestra_Plantas_Total, m.Brotes_Generales_Promedio,
    m.Brotes_Productivos_Promedio, m.Diametro_Brote_Promedio,
    m.Ratio_Productivo_General, m.N_Muestras,
    m.Fecha_Actualizacion
FROM Gold.Mart_Evaluacion_Vegetativa m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 5: vw_Fisiologia**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Fisiologia AS
SELECT
    m.ID_Mart_Fisiologia,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tercio,
    m.Brotes_Productivos_Promedio, m.Brotes_Vegetativos_Promedio,
    m.Hinchadas_Promedio, m.Productivas_Promedio,
    m.Total_Organos_Promedio, m.Ratio_Productivo_Veg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Fisiologia m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 6: vw_Induccion_Floral**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Induccion_Floral AS
SELECT
    m.ID_Mart_Induccion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tipo_Evaluacion,
    m.Pct_Plantas_Con_Induccion_Prom, m.Pct_Brotes_Con_Induccion_Prom,
    m.Pct_Brotes_Con_Flor_Prom, m.Brotes_Totales, m.Brotes_Con_Flor,
    m.Fecha_Actualizacion
FROM Gold.Mart_Induccion_Floral m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 7: vw_Tasa_Crecimiento**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Tasa_Crecimiento AS
SELECT
    m.ID_Mart_Crecimiento,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Tipo_Evaluacion, m.Estado_Vegetativo, m.Tipo_Tallo,
    m.Medida_Crecimiento_Promedio, m.Medida_Crecimiento_Max,
    m.Dias_Desde_Poda_Promedio, m.Cantidad_Mediciones,
    m.Fecha_Actualizacion
FROM Gold.Mart_Tasa_Crecimiento m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 8: vw_Pesos_Calibres**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Pesos_Calibres AS
SELECT
    m.ID_Mart_Pesos,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Evaluador,
    m.Cant_Bayas_Muestra, m.Peso_Promedio_Baya_g, m.Peso_Proyectado_Baya_g,
    m.Tendencia_Peso, m.Estado_DQ,
    m.Fecha_Actualizacion
FROM Gold.Mart_Pesos_Calibres m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 9: Aplicar y verificar conteos**

Run:
```powershell
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -i "ETL\sql_migrations\fase20_vistas_powerbi.sql"
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -Q "SELECT (SELECT COUNT(*) FROM Gold.Mart_Cosecha) AS mart, (SELECT COUNT(*) FROM PowerBI.vw_Cosecha) AS vista"
```
Expected: `mart` y `vista` iguales (156811 = 156811). Repetir mentalmente para las demás; el verificador del Task 6 lo hace automático.

- [ ] **Step 10: Commit**

```bash
git add "ETL/sql_migrations/fase20_vistas_powerbi.sql"
git commit -m "feat(powerbi): vistas estrella estandar (cosecha, censo, poda, vegetativa, fisiologia, induccion, crecimiento, pesos)"
```

---

## Task 3: Vista de Proyecciones (join extra a Escenario)

**Files:**
- Modify: `ETL/sql_migrations/fase20_vistas_powerbi.sql` (append)

- [ ] **Step 1: vw_Proyecciones**

```sql
CREATE OR ALTER VIEW PowerBI.vw_Proyecciones AS
SELECT
    m.ID_Mart_Proyeccion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    m.Semana_Objetivo,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    m.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    es.Tipo_Escenario, es.Descripcion AS Descripcion_Escenario,
    m.Version_Escenario, m.Version_Modelo, m.Estado_Workflow,
    m.Fecha_Generacion, m.Fecha_Cutoff,
    m.Kg_Proyectados, m.Kg_Real, m.Error_MAPE, m.MAPE, m.Desviacion_kg,
    m.Flag_Override, m.Motivo_Override,
    m.Fecha_Actualizacion
FROM Gold.Mart_Proyecciones m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Escenario_Proyeccion es ON m.ID_Escenario = es.ID_Escenario
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 2: Aplicar**

Run:
```powershell
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -i "ETL\sql_migrations\fase20_vistas_powerbi.sql"
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -Q "SELECT TOP 1 * FROM PowerBI.vw_Proyecciones"
```
Expected: la vista existe (0 filas hoy, Mart vacío); sin error de columnas.

- [ ] **Step 3: Commit**

```bash
git add "ETL/sql_migrations/fase20_vistas_powerbi.sql"
git commit -m "feat(powerbi): vista de proyecciones con escenario resuelto"
```

---

## Task 4: Vista de Maduración (joins a Estado Fenológico + Cinta)

**Files:**
- Modify: `ETL/sql_migrations/fase20_vistas_powerbi.sql` (append)

- [ ] **Step 1: vw_Maduracion** (el Mart ya trae `Estado_Fenologico` y `Color_Cinta` como texto; se usa el join a la dimensión como fuente y se descartan los `ID_*`)

```sql
CREATE OR ALTER VIEW PowerBI.vw_Maduracion AS
SELECT
    m.ID_Mart_Maduracion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    COALESCE(ef.Nombre_Estado, m.Estado_Fenologico) AS Estado_Fenologico,
    ef.Orden_Estado,
    COALESCE(ci.Color_Cinta, m.Color_Cinta) AS Color_Cinta,
    m.Organos_Observados, m.Dias_Pasados_Promedio,
    m.Fecha_Actualizacion
FROM Gold.Mart_Maduracion m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Estado_Fenologico ef ON m.ID_Estado_Fenologico = ef.ID_Estado_Fenologico
LEFT JOIN Silver.Dim_Cinta    ci ON m.ID_Cinta    = ci.ID_Cinta
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO
```

- [ ] **Step 2: Aplicar y verificar**

Run:
```powershell
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -i "ETL\sql_migrations\fase20_vistas_powerbi.sql"
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -Q "SELECT TOP 1 * FROM PowerBI.vw_Maduracion"
```
Expected: vista existe (0 filas hoy), sin error.

- [ ] **Step 3: Commit**

```bash
git add "ETL/sql_migrations/fase20_vistas_powerbi.sql"
git commit -m "feat(powerbi): vista de maduracion con estado fenologico y cinta resueltos"
```

---

## Task 5: Vistas especiales (Clima, Administrativo, Fenologia)

**Files:**
- Modify: `ETL/sql_migrations/fase20_vistas_powerbi.sql` (append)

- [ ] **Step 1: vw_Clima** (sin geografía ni variedad; `Sector_Climatico` ya es texto)

```sql
CREATE OR ALTER VIEW PowerBI.vw_Clima AS
SELECT
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    m.Sector_Climatico,
    m.Temp_Promedio_Diaria, m.Temp_Maxima_Dia, m.Temp_Minima_Dia,
    m.Humedad_Promedio, m.Precipitacion_Total,
    m.Indice_UV_Max, m.Indice_UV_Min,
    m.Radiacion_Solar_Prom_Diurna, m.Radiacion_Solar_Max,
    m.VPD_Promedio, m.GDD
FROM Gold.Mart_Clima m
LEFT JOIN Silver.Dim_Tiempo  t  ON m.ID_Tiempo  = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana ca ON m.ID_Campana = ca.ID_Campana;
GO
```

- [ ] **Step 2: vw_Administrativo** (resuelve Tiempo+Campaña; el Mart ya trae texto de personal/actividad)

```sql
CREATE OR ALTER VIEW PowerBI.vw_Administrativo AS
SELECT
    m.ID_Mart_Admin,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes,
    COALESCE(t.Semana_ISO, m.Semana_ISO) AS Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(p.Nombre_Completo, m.Nombre_Personal) AS Nombre_Personal,
    COALESCE(p.DNI, m.DNI_Personal) AS DNI_Personal,
    m.Sexo, m.Rol, m.Supervisor,
    COALESCE(ao.Nombre_Actividad, m.Actividad) AS Actividad,
    COALESCE(ao.Nombre_Labor, m.Labor) AS Labor,
    ao.Categoria,
    m.Horas_Trabajadas, m.Horas_Trabajadas_Total, m.Dias_Trabajados,
    m.Pct_Asertividad, m.Registros_Observados_SAP,
    m.Fecha_Actualizacion
FROM Gold.Mart_Administrativo m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Personal p  ON m.ID_Personal = p.ID_Personal
LEFT JOIN Silver.Dim_Actividad_Operativa ao ON m.ID_Actividad = ao.ID_Actividad;
GO
```

- [ ] **Step 3: vw_Fenologia** (sin IDs de lookup; puro renombre/orden de columnas ya legibles)

```sql
CREATE OR ALTER VIEW PowerBI.vw_Fenologia AS
SELECT
    m.ID_Mart_Fenologia,
    m.Semana_ISO,
    m.Modulo,
    m.Variedad,
    m.Color_Cinta,
    m.Estado_Fenologico,
    m.Orden_Estado,
    m.Cantidad_Bayas,
    m.Pct_Cosechable,
    m.Pct_Avance_Ciclo,
    m.Brotes_Productivos,
    m.Brotes_Vegetativos,
    m.Ratio_Productivo_Veg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Fenologia m;
GO
```

- [ ] **Step 4: Aplicar y verificar conteos**

Run:
```powershell
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -i "ETL\sql_migrations\fase20_vistas_powerbi.sql"
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -Q "SELECT (SELECT COUNT(*) FROM Gold.Mart_Clima) AS clima_mart, (SELECT COUNT(*) FROM PowerBI.vw_Clima) AS clima_vista, (SELECT COUNT(*) FROM Gold.Mart_Fenologia) AS feno_mart, (SELECT COUNT(*) FROM PowerBI.vw_Fenologia) AS feno_vista"
```
Expected: `clima_mart=clima_vista=3333`, `feno_mart=feno_vista=37352`.

- [ ] **Step 5: Commit**

```bash
git add "ETL/sql_migrations/fase20_vistas_powerbi.sql"
git commit -m "feat(powerbi): vistas especiales clima, administrativo y fenologia"
```

---

## Task 6: Verificador automático

**Files:**
- Create: `ETL/sql_migrations/_verificar_fase20.py`

- [ ] **Step 1: Escribir el verificador**

```python
"""Verifica las 13 vistas PowerBI.vw_* de la fase 20.

Reglas:
1. Las 13 vistas existen y son consultables.
2. Para Marts no vacíos, COUNT(vista) == COUNT(mart) (los LEFT JOIN no inflan
   ni reducen filas).
3. Ninguna vista expone columnas ID_* de lookup; solo se permite la PK
   surrogate ID_Mart_*.
"""
import sys
import pyodbc

CN = (
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;"
    "DATABASE=ACP_DataWarehose_Proyecciones;Trusted_Connection=yes"
)

# vista -> mart base
PARES = {
    "vw_Cosecha": "Mart_Cosecha",
    "vw_Censo_Plantas": "Mart_Censo_Plantas",
    "vw_Ciclo_Poda": "Mart_Ciclo_Poda",
    "vw_Evaluacion_Vegetativa": "Mart_Evaluacion_Vegetativa",
    "vw_Fisiologia": "Mart_Fisiologia",
    "vw_Induccion_Floral": "Mart_Induccion_Floral",
    "vw_Tasa_Crecimiento": "Mart_Tasa_Crecimiento",
    "vw_Pesos_Calibres": "Mart_Pesos_Calibres",
    "vw_Proyecciones": "Mart_Proyecciones",
    "vw_Maduracion": "Mart_Maduracion",
    "vw_Clima": "Mart_Clima",
    "vw_Administrativo": "Mart_Administrativo",
    "vw_Fenologia": "Mart_Fenologia",
}

def main() -> int:
    cn = pyodbc.connect(CN)
    cur = cn.cursor()
    fallos = []

    for vista, mart in PARES.items():
        # 1. existe / consultable + conteo
        try:
            n_vista = cur.execute(f"SELECT COUNT(*) FROM PowerBI.{vista}").fetchval()
        except pyodbc.Error as e:
            fallos.append(f"[{vista}] no consultable: {e}")
            continue
        n_mart = cur.execute(f"SELECT COUNT(*) FROM Gold.{mart}").fetchval()
        if n_mart > 0 and n_vista != n_mart:
            fallos.append(f"[{vista}] conteo {n_vista} != mart {n_mart}")

        # 3. columnas ID_* prohibidas (salvo PK surrogate ID_Mart_*)
        cols = [r.COLUMN_NAME for r in cur.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='PowerBI' AND TABLE_NAME=?", vista
        ).fetchall()]
        malas = [c for c in cols
                 if c.upper().startswith("ID_") and not c.upper().startswith("ID_MART")]
        if malas:
            fallos.append(f"[{vista}] expone IDs de lookup: {malas}")

    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA='PowerBI'"
    )
    total = cur.fetchval()
    if total != 13:
        fallos.append(f"Se esperaban 13 vistas en PowerBI, hay {total}")

    if fallos:
        print("VERIFICACION FALLIDA:")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"OK: {total} vistas PowerBI.vw_* validadas (conteos e IDs correctos).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Ejecutar el verificador**

Run:
```powershell
.\.venv\Scripts\python.exe "ETL\sql_migrations\_verificar_fase20.py"
```
Expected: `OK: 13 vistas PowerBI.vw_* validadas (conteos e IDs correctos).` y exit code 0.

- [ ] **Step 3: Inspección manual de muestra (lo que verá Power BI)**

Run:
```powershell
sqlcmd -S . -d ACP_DataWarehose_Proyecciones -E -Q "SELECT TOP 3 Fecha, Nombre_Campana, Fundo, Sector, Variedad, Kg_Neto_Real FROM PowerBI.vw_Cosecha"
```
Expected: `Fecha` como fecha real (ej. `2025-05-16`), `Nombre_Campana` como texto, `Fundo`/`Sector`/`Variedad` con nombres — cero IDs crudos.

- [ ] **Step 4: Commit**

```bash
git add "ETL/sql_migrations/_verificar_fase20.py"
git commit -m "test(powerbi): verificador de vistas fase 20 (conteos + ausencia de IDs)"
```

---

## Task 7: Reapuntar Power BI a las vistas

Esto lo hace el usuario en Power BI Desktop (no es código del repo). Documentar como cierre.

- [ ] **Step 1:** En Power BI: *Obtener datos → SQL Server* → seleccionar las vistas del esquema `PowerBI` en vez de las tablas `Gold.Mart_*`.
- [ ] **Step 2:** Eliminar las consultas viejas que apuntaban a `Gold.Mart_*` o reemplazar su origen.
- [ ] **Step 3:** Confirmar que la columna `Fecha` quedó tipada como *Fecha* en el modelo (no número entero) y que las columnas de nombres aparecen.

---

## Self-Review

**1. Cobertura del spec:**
- 13 vistas (§3.2): Tasks 2 (×8), 3, 4, 5 (×3) = 13. ✔
- Esquema `PowerBI` (§3.3): Task 1. ✔
- Reemplazo de IDs por nombres (§3.1): cada `SELECT` proyecta texto; verificador Task 6 step 1 regla 3. ✔
- Geografía completa (§3.4): bloque de 6 catálogos en cada vista con `ID_Geografia`. ✔
- `LEFT JOIN` + `COALESCE` + `Fecha` date (§4): aplicado en todas. ✔
- Tabla de resolución (§5): Tiempo, Campaña, Geografía, Variedad, Escenario, Estado_Fenologico, Cinta, Personal, Actividad — todos cubiertos en Tasks 2-5. ✔
- Mapa por Mart (§6): coincide con las vistas escritas (Fenologia sin joins, Clima/Administrativo sin geo). ✔
- Entregable: script SQL (Task 1-5) + verificador (Task 6). ✔
- PK surrogate conservada (§3.1): incluida en cada vista salvo `vw_Clima` (Mart_Clima no tiene PK surrogate; su grano es ID_Tiempo+Sector_Climatico+Campana). ✔

**2. Placeholders:** ninguno; todo el SQL y Python está completo.

**3. Consistencia de tipos/nombres:** nombres de columnas tomados del volcado real de `INFORMATION_SCHEMA`. Alias consistentes (`Descripcion_Escenario`, `Cama`). El verificador usa los mismos nombres de vista que la DDL.

**Nota detectada y resuelta:** `vw_Clima` no tiene PK surrogate porque `Mart_Clima` no la tiene — el verificador no la exige (regla 3 solo prohíbe IDs de lookup, no exige PK).
