# ETL Catalog Documentation - ACP DataWarehouse Proyecciones

## Resumen

Este paquete documenta el ETL completo del Data Warehouse de proyecciones de ACP con **79 tablas** organizadas en arquitectura Medallion:
- **Bronce** (25 tablas): Ingesta raw desde Excel de campo + SAP
- **Silver** (37 tablas): Transformaciones limpias con MDM + 14 facts operacionales
- **Gold** (12 tablas): Marts agregados semanales para Power BI
- **Control/Auditoria** (5 tablas): Configuración, auditoría, seguridad, homologación

---

## Archivos Principales

### 1. **ETL_CATALOG_HUMANIZED.md** 
📄 **Lectura recomendada para empezar**

Documento markdown con descripción humanizada en 2-3 líneas por tabla (como pediste):
- ¿Qué registra cada tabla?
- ¿De dónde vienen los datos?
- ¿Cuál es la granularidad?
- ¿Para qué sirve?

Incluye:
- Tabla resumen de tablas Bronce por categoría (Fenología, Estructura Vegetal, Labor, Clima, etc.)
- Detalles de dimensiones Silver (catálogos maestros)
- Definiciones de 14+ Facts operacionales
- 12 Marts Gold con su propósito Power BI
- **Flujos de datos clave** (Forecast, Harvest Readiness, Labor Costing, Climate-Crop Physiology)
- **Casos de uso** por tipo de usuario (Agronomía, Supply Chain, HR, Data Science)
- Convenciones de nombres, MDM, vigencia, auditoría

**Secciones principales:**
```
├─ BRONCE (25 tablas por categoría)
│  ├─ Fenología & Frutas (Conteo + Maduración)
│  ├─ Evaluaciones de Estructura Vegetal
│  ├─ Crecimientos & Pesos
│  ├─ Censos & Sanidad
│  ├─ Cosecha & Producción
│  ├─ Operaciones & Labor
│  ├─ Clima & Meteorología
│  └─ SAP Post-Cosecha
├─ SILVER (37 tablas)
│  ├─ Dimensiones: Catálogos Maestros (Tiempo, Variedad, Fundo, etc.)
│  ├─ Dimensión Geográfica (6-nivel denormalizado)
│  └─ Facts: Mediciones & Eventos (14 facts operacionales)
├─ GOLD (12 marts)
│  └─ Semanales denormalizados para Power BI
└─ CONTROL, AUDITORIA & CONFIG (5 tablas)
```

---

### 2. **ETL_TABLE_CATALOG.json**
🔧 **Para integración programática**

JSON estructurado con metadatos completos para cada tabla:
```json
{
  "project": "ACP DataWarehouse Proyecciones",
  "architecture": "Medallion (Bronce → Silver → Gold)",
  "tables": {
    "Bronce.Conteo_Fruta": {
      "desc": "Conteo de frutas por etapa fenológica...",
      "source": "Excel: /data/entrada/conteo_fruta/ → ...",
      "grain": "One row per (fecha, modulo, turno, valvula, punto, variedad)",
      "parents": [],
      "schema": "Bronce",
      "raw_cols": ["Fecha_Raw", "Modulo_Raw", ...],
      "purpose": "Core input forecasting via fruit stage progression modeling..."
    },
    ...
  },
  "summary": {
    "bronce_count": 25,
    "silver_count": 37,
    "gold_count": 12,
    "auxiliary_count": 5,
    "total_tables": 79
  }
}
```

**Estructura por tabla:**
- `desc`: Descripción 2-3 líneas (qué registra)
- `source`: De dónde vienen los datos (carpeta Excel, SAP, Logger, etc.)
- `grain`: Granularidad (qué combinación de claves = 1 fila)
- `parents`: Tablas de las que se alimenta (lineage)
- `schema`: Bronce/Silver/Gold/Control/Auditoria
- `raw_cols` (Bronce): Columnas raw que lleva
- `purpose`: Para qué sirve

**Ideal para:**
- Scripts de documentación automática
- Generación de vistas de catalogación
- Validación de dependencias
- Data governance tools

---

### 3. **ETL_TABLES_QUICK_REFERENCE.csv**
📊 **Para búsquedas y filtros rápidos**

CSV con 79 filas (una por tabla) y columnas:
```
schema | table_name | category | description_es | source_es | grain_es | primary_use_es
```

**Categorías disponibles:**
- Frutas, Sanidad, Fenología, Estructura, Labor, Cosecha, Clima, Experimental, Post-Cosecha, Catálogo, Geografía, Hecho, Puente, Dashboard, Configuración, Auditoría, Acceso, Maestría

**Usos:**
- Filtrar por `category` (p.ej., "Fenología" → 4 tablas Bronce + facts + marts)
- Búsqueda por nombre o descripción en Excel/Sheets
- Validación de cobertura por dominio
- Reports rápidos (¿cuántas tablas hay en cada esquema?)

---

### 4. **ETL_ARCHITECTURE_FLOWS.txt**
🏗️ **Diagramas y flujos de datos**

ASCII-art diagrama completo del ETL:

**Secciones:**
1. **BRONCE INGESTION LAYER** - Qué carga cada tabla, de dónde, via qué cargador
2. **SILVER TRANSFORMATION LAYER** - Cómo se transforman Bronce → Silver:
   - MDM Homologación (raw → normalized)
   - Dimension Building (6-level Geografia)
   - Fact Transformations (14+ facts con detalles de cálculos)
   - Bridges M:M
3. **GOLD AGGREGATION LAYER** - Qué expone cada Mart, grain, purpose
4. **ETL ORCHESTRATION & CONTROL FLOW** - Flujo pipeline.py:
   - Bronce Loading
   - Silver Transformation
   - Projection Model
   - Gold Refresh (conditional)
   - Logging & Alerts
5. **POWER BI CONNECTION** - Qué conecta Power BI (SOLO Gold)
6. **DATA QUALITY GATES** - Validaciones en cada nivel (Bronce/Silver/Gold)
7. **MDM & CONFIGURATION** - Cómo funciona Homologacion_MDM y Parametros_Pipeline
8. **LINEAGE & AUDITORIA** - Trazabilidad Bronce → Silver → Gold → Power BI
9. **DEPLOYMENT & RE-RUN SAFETY** - Idempotency, re-run scenarios

**Incluye detalles de:**
- Transformación Conteo_Fruta: cómo se parsean 20+ columnas de frutas
- Cálculo VPD (Tetens formula) en Telemetria_Clima
- Cálculo GDD (Growing Degree Days) por intervalo
- Weight curves fitting para Evaluacion_Pesos
- Aggregations por semana para cada Mart
- Circuit breaker: si facts_bloqueantes fallan → no refresh Gold

---

## Cómo Usar Esta Documentación

### Para **Agronomía / Field Manager**
→ Lee **ETL_CATALOG_HUMANIZED.md** secciones:
- "🌾 Agronomía/Field Manager" (cases de uso)
- Tabla de Mart_Fenologia, Mart_Clima, Mart_Evaluacion_Vegetativa

### Para **Supply Chain / Venta**
→ Busca en **ETL_TABLES_QUICK_REFERENCE.csv** por categoría "Cosecha"
→ Lee en MD: "Mart_Cosecha", "Mart_Proyecciones"

### Para **Data Scientists / Proyecciones**
→ Lee en MD: "Fact_Proyecciones", "Fact_Conteo_Fenologico", "Fact_Evaluacion_Pesos"
→ Revisa en FLOWS.txt: "3. PROJECTION MODEL"

### Para **Desarrolladores ETL**
→ Lee **ETL_ARCHITECTURE_FLOWS.txt** completo:
- Sección 2: SILVER TRANSFORMATION (detalles de transformación)
- Sección 4: ETL ORCHESTRATION (flujo pipeline)
- Sección 9: DEPLOYMENT & RE-RUN SAFETY

### Para **Database Admins**
→ Lee en FLOWS.txt:
- Sección 6: DATA QUALITY GATES
- Sección 8: LINEAGE & AUDITORIA
→ Usa JSON catalog para scripting de auditoría

### Para **Power BI Developers**
→ Ve a MD: "GOLD: Marts de Agregación para Power BI"
→ Busca en CSV: `schema="Gold"` para ver los 12 marts disponibles

### Para **MDM / Data Governance**
→ Lee en FLOWS.txt:
- Sección 7: MDM & CONFIGURATION MANAGEMENT
→ Revisa en MD: "CONVENIOS Y PATRONES > MDM (Homologación)"

---

## Estructura JSON en Detalle

Cada tabla en **ETL_TABLE_CATALOG.json** tiene:

```json
{
  "schema": "Silver|Bronce|Gold|Control|Auditoria",
  "table_name": "Fact_Cosecha_SAP",
  "category": "Hecho",  // Dimension, Hecho, Puente, Dashboard, Catálogo, etc.
  "description_es": "Cosecha real SAP: kg_neto_mp por geografía...",
  "source_es": "Bronce.Cosecha_SAP → parse geografia + JOIN Dim_Condicion",
  "grain_es": "One row per (fecha, id_geografia, id_variedad, id_condicion_cultivo, id_campana)",
  "primary_use_es": "Source-of-truth harvest for forecast validation",
  "parents": ["Bronce.Cosecha_SAP", "Silver.Dim_Condicion_Cultivo"],
  "raw_cols": ["Fecha_Raw", "Kg_Total_Raw", "Area_Raw"],  // solo si Bronce
  "purpose": "Harvest volume truth-set for projection comparison, yield analytics..."
}
```

---

## Convenciones de Documentación

### Nombres de Tablas
- **Bronce**: `Bronce.[Nombre_Tabla]` — ALL CAPS words, sin sufijo
- **Silver**: `Silver.[Dim_/Fact_/Bridge_][Nombre]` — prefijo obligatorio
- **Gold**: `Gold.[Mart_][Nombre]` — prefijo `Mart_` para Public Power BI

### Descripción "2-3 líneas" (como pediste)
1. **Línea 1**: Qué registra (el qué)
2. **Línea 2**: De dónde viene (el source) + proceso
3. **Línea 3**: Para qué sirve (el propósito)

Ejemplo Conteo_Fruta:
```
Conteo de frutas por etapa fenológica (botones, flores, pequeñas, grandes, etc.) | 
Excel: /conteo_fruta/ → 20+ métricas por punto de muestreo |
Core input para forecasting: progresión semanal de etapa → modelo 6 semanas
```

### Grain (Granularidad)
Formato: `One row per (col1, col2, col3)` o `(fecha, geografia, variedad, campana)`

### Source (Fuente)
Formato: `Excel: /ruta/ → Proceso → Resultado`
Ejemplo: `Excel: /conteo_fruta/ → Parse estado_fenologico → Sum bayas por stage`

---

## Referencias Cruzadas

**Relaciones importantes:**
- 📌 **Fact_Conteo_Fenologico** (core) → **Mart_Fenologia** (weekly output)
- 📌 **Fact_Cosecha_SAP** (actuals) + **Fact_Proyecciones** (forecast) → **Mart_Cosecha** (comparison)
- 📌 **Fact_Evaluacion_Pesos** (weight) + **Fact_Telemetria_Clima** (VPD/GDD) → **Projection Model** (weekly kg forecast)
- 📌 **Fact_Tareo** (hours) + **Dim_Personal** (roles) → **Mart_Administrativo** (HR dashboard)

---

## Control de Cambios

Documento generado desde análisis exhaustivo de:
- ✅ `/bronce/rutas.py` (25 tablas + mapeo)
- ✅ `/bronce/cargador.py` (lógica carga + validaciones)
- ✅ `/silver/facts/*.py` (14 transformadores)
- ✅ `/gold/marts.py` (12 marts)
- ✅ `/sql_migrations/DDL_DataWarehose_Proyecciones_v3.sql` (DDL completo)

**Próximas actualizaciones necesarias si:**
- Se agrega nueva tabla Bronce → Actualizar rutas.py + JSON + CSV
- Se cambia grain de un Mart → Actualizar Architecture Flows
- Se crea nuevo Fact → Actualizar MDN, JSON, CSV
- Se modifica MDM rules → Documentar en Convenios y Patrones

---

## Acceso & Distribución

📂 **Ubicación:**
```
D:\Proyecto2026\ACP_DWH\ACP Proyecciones\
├─ ETL_CATALOG_HUMANIZED.md           (← EMPIEZA AQUÍ)
├─ ETL_TABLE_CATALOG.json             (programmatic)
├─ ETL_TABLES_QUICK_REFERENCE.csv     (búsquedas)
├─ ETL_ARCHITECTURE_FLOWS.txt         (diseño detallado)
└─ README_ETL_CATALOG.md              (este archivo)
```

📧 **Compartir con:**
- Agronomía: MD + Quick Reference CSV
- Supply Chain: CSV filtrado + Mart_Cosecha sección de MD
- Dev Team: JSON + FLOWS.txt
- Datos Governance: JSON + FLOWS.txt sección 7

---

## Preguntas Frecuentes

**P: ¿Cuáles son las tablas clave?**
R: 
- **Bronce**: Conteo_Fruta, Evaluacion_Pesos, Cosecha_SAP, Telemetria_Clima
- **Silver**: Fact_Conteo_Fenologico, Fact_Cosecha_SAP, Fact_Proyecciones
- **Gold**: Mart_Cosecha, Mart_Proyecciones, Mart_Fenologia

**P: ¿Si falla Conteo_Fruta, qué no funciona?**
R: Fact_Conteo_Fenologico → Mart_Fenologia (harvest timing) + Proyecciones (no se generan). Es un fact bloqueante.

**P: ¿Puedo conectar Power BI a Silver?**
R: NO. Solo conecta a Gold (12 Marts). Silver es interno ETL.

**P: ¿Cómo agrego una nueva métrica a Mart_Cosecha?**
R: 
1. Crea fact en Silver (si no existe)
2. Modifica refrescar_mart_cosecha() en /gold/marts.py
3. TRUNCATE Gold.Mart_Cosecha
4. INSERT with new column
5. Test en Power BI

**P: ¿Cómo cambio una regla MDM (ej: Variedad)?**
R: Portal MDM → Edit Config.Homologacion_MDM → Next ETL run aplica rules (no need redeploy código)

---

## Soporte

Para preguntas:
- 🌾 Agronomía: Revisar casos de uso en MD + Mart relevante
- 🔧 Técnicas: Ver FLOWS.txt sección 4 (Orchestration)
- 📊 Datos: Revisar lineage en FLOWS.txt sección 8

---

**Última actualización:** 2026-06-03  
**Versión:** 1.0  
**Creado por:** Claude Code Agent  
**Formato:** Markdown + JSON + CSV + ASCII-art
