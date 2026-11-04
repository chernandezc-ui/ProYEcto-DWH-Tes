# ETL Catalog: ACP DataWarehouse Proyecciones

**Arquitectura:** Medallion (Bronce → Silver → Gold)  
**Fecha generada:** 2026-06-03  
**Total tablas:** 79 (25 Bronce + 37 Silver + 12 Gold + 5 Control/Auditoria)

---

## BRONCE: Ingesta Raw (25 tablas)

Todas las tablas Bronce cargan datos Excel/SAP sin tipificación (NVARCHAR), preservando valores originales + auditoria (Fecha_Sistema, Nombre_Archivo, Estado_Carga).

### Fenología & Frutas (Conteos + Maduración)

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Conteo_Fruta** | Conteo de frutas por etapa fenológica (botones, flores, pequeñas, grandes, cremas, maduras, cosechables) | Excel: `/data/entrada/conteo_fruta/` → 20+ métricas por punto de muestreo | (fecha, modulo, turno, valvula, punto, variedad) |
| **Ciclos_Fenologicos** | Etapa fenológica por color de cinta marcadora (rojo/naranja/amarillo) y órgano de la planta | Excel: `/data/entrada/ciclos_fenologicos/` → Seguimiento de color + órgano + etapa | (fecha, modulo, turno, valvula, organo, color) |
| **Maduracion** | Maduración de fruta marcada: color de cinta y días desde marcado | Excel: `/data/entrada/maduracion/` → Progresión de color en frutos etiquetados | (fecha, modulo, turno, valvula, variedad, organo, color) |
| **Peladas** | Frutas desnudadas (expuestas por enfermedad/daño) por etapa fenológica | Excel: `/data/entrada/peladas/` → Daño/enfermedad en frutas visibles | (fecha, modulo, turno, valvula, punto, variedad, estado_fenologico) |

### Evaluaciones de Estructura Vegetal

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Evaluacion_Vegetativa** | Estructura de la planta por piso (1-5): brotes, productivos, diámetro, altura, tallos basales | Excel: `/evaluacion_vegetativa/` OR `/floracion/` layout con "N_Plantas_en_Floracion_Raw" | (fecha, modulo, turno, valvula, cama, variedad, semanas_poda, piso) |
| **Floracion** | Plantas en flor vs evaluadas por cama | Excel: `/evaluacion_vegetativa/` subset con layout específico de floracion | (fecha, modulo, turno, valvula, cama, variedad) |
| **Fisiologia** | Estado fisiológico de yemas: hinchadas/productivas por tercio (tercera parte de altura) | Excel: `/fisiologia/` → Viabilidad de yemas en etapas de repozo | (fecha, modulo, turno, valvula, tercio, variedad, brote) |
| **Induccion_Floral** | Resultados de inducción de floración fuera de estación (plantas/brotes con inducción vs con flores) | Excel: `/induccion_floral/` → Eficiencia de tratamiento de inducción | (fecha, modulo, turno, valvula, cama, variedad, tipo_evaluacion) |

### Crecimientos & Pesos

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Tasa_Crecimiento_Brotes** | Tasa de crecimiento de brotes desde poda (cm/día medidos en ensayos de marcado) | Excel: `/tasa_crecimiento_brotes/` → Hojas BD_General (histórico) o reporte diario | (fecha, modulo, turno, valvula, cama, tipo_tallo, ensayo_id) |
| **Evaluacion_Pesos** | Peso de bayas por etapa (pequeñas/grandes/cremas/maduras/cosechables) + muestra para curva de crecimiento | Excel: `/evaluacion_pesos/` → Multi-formato (peso_baya + cantidad_muestra) | (fecha, modulo, turno, valvula, variedad, tipo_evaluacion) |
| **Calibres** | Diámetro de bayas por variedad → clasificación en calibres comerciales | Excel: `/calibres/` → Medidas de tamaño para proyectar oferta/demanda | (fecha, modulo, turno, variedad, evaluador) |

### Censos & Sanidad

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Censo_Plantas** | Conteo de plantas por estado de salud (buenas/regulares/malas/muertas/hoyos) | Excel: `/censo_plantas/` → Auto-detecta formato ancho (pivoteado) o largo | (fecha, modulo, turno, valvula, variedad, estado_planta) |
| **Seguimiento_Errores** | Seguimiento de plantas muertas/pérdidas y problemas en módulos | Excel: `/seguimiento_errores/` → Reporte de incidentes fitosanitarios | (fecha, modulo, variedad, tipo_error) |

### Cosecha & Producción

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Cosecha_SAP** | Cosecha real desde SAP: kg totales, área, plantas, semana_cosecha_sap | SAP export: `/data_sap/` → Reconciliación cosecha SAP vs campo | (fecha, semana, modulo, turno, valvula, variedad) |
| **Reporte_Cosecha** | Reporte de cosecha diaria: kg neto, jabas por módulo | Excel: `/reporte_cosecha/` → Consolidación diaria de cosecha | (fecha, modulo, turno, valvula, variedad) |
| **Cierre_Mapas_Cosecha** | Cierre de mapas de cosecha: validación que todos los bloques fueron cosechados | Excel: `/cierre_mapas_cosecha/` → Completitud de cosecha por lote | (fecha, modulo, variedad) |
| **Proyeccion_Pesos** | Proyección de peso promedio para modelo de forecasting de rendimiento | Excel: `/proyeccion_pesos/` → Semilla inicial para curva de peso | (fecha, modulo, variedad, peso_proyectado) |

### Operaciones & Labor

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Consolidado_Tareos** | Horas trabajadas por persona, actividad, labor desde planillas SAP | SAP export: `/tareos/` → Consolidacion de actividades+labores | (fecha, dni_responsable, modulo, turno, actividad, labor, horas_trabajadas) |
| **Fiscalizacion** | Auditorias operativas: inspector, módulo, fecha de inspección | Excel: `/fiscalizacion/` → Auditoría de cumplimiento | (fecha, dni_inspector, modulo, turno) |

### Clima & Meteorología

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Telemetria_Clima** | Telemetría horaria: T_exterior, T_max/min, humedad, lluvia, UV, radiación, VPD (calculado), GDD | Logger automático: `/telemetria_clima/` (por sector: A01, B02...) | (fecha_hora, sector_climatico) — 24/7 |
| **Reporte_Clima** | Reporte diario de clima: T_max/min, humedad, precipitación | Excel: `/reporte_clima/` → Cuando telemetría no disponible | (fecha, hora, sector) |
| **Variables_Meteorologicas** | Variables meteorológicas VPD, radiación → fallback cuando telemetría falla | Excel: `/telemetria_clima/` → Actualizaciones esporádicas | (fecha, modulo, sector, vpd, radiacion) |

### SAP Post-Cosecha

| Tabla | Qué registra | De dónde | Granularidad |
|-------|--------|----------|---------|
| **Data_SAP** | Datos de post-cosecha desde SAP: código cliente, material, lote, almacén, peso bruto/tara/neto, remisión | SAP extract: `/data_sap/` → Trazabilidad post-cosecha | (fecha_cosecha, consumidor_pep, variedad, material, lote, almacen) |

### Tablas Auxiliares (no carga operativa)

| Tabla | Propósito |
|-------|----------|
| **Dashboard** | Registro de archivos de dashboard (legacy) |

---

## SILVER: Transformaciones Limpias (37 tablas)

Datos normalizados, tipificados, con reglas MDM (homologación) aplicadas. Todas las facts tienen `Fecha_Sistema`, `Estado_DQ`, `ID_Campana`.

### Dimensiones: Catálogos Maestros

| Tabla | Qué es | Source | Grain |
|-------|--------|--------|-------|
| **Dim_Tiempo** | Calendario gregoriano + semana ISO + semana cosecha + día semana + nombre mes | Config builder (2020-2035) | 1 fila/día |
| **Dim_Variedad** | Catálogo de variedades: nombre + breeder | Bronce.[all] unique variedad_raw → MDM | 1 fila/variedad única |
| **Dim_Fundo_Catalogo** | Fundos (Las Cruces, San Martín, etc.) | Bronce.[all] unique fundo_raw → MDM | 1 fila/fundo |
| **Dim_Sector_Catalogo** | Sectores dentro de fundos | Bronce.[all] unique sector_raw → MDM | 1 fila/sector |
| **Dim_Modulo_Catalogo** | Módulos (secciones de cultivo) + tipo conducción (espalier/sombrilla/etc) | Bronce.[all] unique modulo_raw → MDM | 1 fila/modulo |
| **Dim_Turno_Catalogo** | Turnos (1/2/3 o A/B/C) | Bronce.[all] unique turno_raw → MDM | 1 fila/turno |
| **Dim_Valvula_Catalogo** | Válvulas de riego (zonas de agua) | Bronce.[all] unique valvula_raw → MDM | 1 fila/valvula |
| **Dim_Cama_Catalogo** | Camas (líneas de plantación) | Bronce.[all] unique cama_raw → MDM | 1 fila/cama |
| **Dim_Personal** | Directorio de empleados: DNI, nombre, rol, sexo, planilla, % asertividad, días ausentismo | Bronce.Consolidado_Tareos deduplicated | 1 fila/dni |
| **Dim_Actividad_Operativa** | Catálogo de actividades laborales (cultivo, cosecha, empaque) + códigos SAP + labor | Bronce.Consolidado_Tareos deduplicated | 1 fila/(actividad, labor) |
| **Dim_Campana** | Campaña/temporada de cosecha (año_cosecha, nombre, estado) | Config Parametros_Pipeline | 1 fila/campaña |
| **Dim_Escenario_Proyeccion** | Escenarios de proyección (Conservador/Base/Optimista) + horizonte semanas | Config Parametros_Pipeline | 1 fila/escenario |
| **Dim_Condicion_Cultivo** | Condiciones de cultivo: sustrato (suelo/hidro/coco) + certificación (orgánico/convencional) | Manual catalog | 1 fila/(sustrato, certificacion) |
| **Dim_Estado_Fenologico** | Etapas fenológicas ordenadas: botones → flores → frutos pequeños → medianos → grandes → maduros → cosechables | Bronce.Conteo_Fruta unique estados → ordered | 1 fila/estado (1-7+) |
| **Dim_Estado_Workflow** | Estados workflow de proyecciones: draft → validado → override → publicado → rechazado | Portal workflow | 1 fila/estado |
| **Dim_Cinta** | Colores de cinta para marcar frutos: rojo/naranja/amarillo/verde/etc | Bronce.Ciclos_Fenologicos unique colors | 1 fila/color |

### Dimensión Geográfica Denormalizada

| Tabla | Qué es | Source | Grain |
|-------|--------|--------|-------|
| **Dim_Geografia** | Composición completa Fundo→Sector→Modulo→Turno→Valvula→Cama con flags (test_block, granularidad, vigencia) | JOIN 6 catalogs (Fundo+Sector+Modulo+Turno+Valvula+Cama) | 1 fila / (fundo, sector, modulo, turno, valvula, cama) |

### Facts: Mediciones & Eventos

| Tabla | Qué mide | Source | Grain | Propósito |
|--------|----------|--------|-------|----------|
| **Fact_Conteo_Fenologico** | Conteo de frutas por etapa fenológica (órganos totales por stage) | Bronce.Conteo_Fruta → Parse estado_fenologico → Sum bayas por stage | (fecha, geografia, variedad, estado_fenologico, personal, punto, campana) | Core input de forecasting: progresión de etapa → modelo 6 semanas |
| **Fact_Ciclos_Fenologicos** | Maduración de frutas marcadas con cinta: color + días desde marcado | Bronce.Maduracion → JOIN Dim_Cinta → Match frutos marcados | (fecha, geografia, variedad, cinta, organo, estado_fenologico, campana) | Optimización de fecha cosecha + ripeness tracking |
| **Fact_Peladas** | Frutas desnudadas (daño/enfermedad) por etapa | Bronce.Peladas → Parse estado_fenologico | (fecha, geografia, variedad, estado_fenologico, personal, punto, campana) | Detección urgencia sanitaria |
| **Fact_Evaluacion_Vegetativa** | Estructura vegetal por piso: brotes, productivos, diámetro, altura | Bronce.Evaluacion_Vegetativa → Parse pisos 1-5 | (fecha, geografia, variedad, piso, semanas_poda, campana) | Predicción enfermedad + validación madurez cosecha |
| **Fact_Evaluacion_Pesos** | Peso de bayas por etapa (g/baya) + proyección cosecha | Bronce.Evaluacion_Pesos → Clean weights + fit curve | (fecha, geografia, variedad, personal, campana) | Modelado trayectoria peso + estimation kg totales |
| **Fact_Fisiologia** | Estado fisiológico de yemas: hinchadas/productivas por tercio | Bronce.Fisiologia → Parse tercio + count buds | (fecha, geografia, variedad, tercio, campana) | Predicción potencial floración |
| **Fact_Floracion** | Evento de floración: plantas en flor vs evaluadas | Bronce.Floracion → Parse plantas_en_floracion | (fecha, geografia, variedad, personal, campana) | Detección ventana polinización |
| **Fact_Induccion_Floral** | Éxito de inducción de floración fuera estación (% plantas + % brotes con flores) | Bronce.Induccion_Floral → Calculate pct_induccion + pct_floracion | (fecha, geografia, variedad, personal, campana) | Validación protocolo inducción |
| **Fact_Ciclo_Poda** | Calidad de poda: tallos, longitud, diámetro, defectos por geografía | Bronce.Evaluacion_Calidad_Poda → Clean + agg | (fecha, geografia, variedad, tipo_evaluacion, campana) | QA ejecución poda |
| **Fact_Censo_Plantas** | Censo poblacional: plantas buenas/regulares/malas por estado | Bronce.Censo_Plantas → Parse estado_planta | (fecha, geografia, variedad, campana) | Monitoreo salud campo + replanta planning |
| **Fact_Cosecha_SAP** | Cosecha real SAP: kg_neto_mp por geografía, variedad, fecha, condición cultivo | Bronce.Cosecha_SAP → Parse geografia + JOIN Dim_Condicion | (fecha, geografia, variedad, condicion_cultivo, campana) | **Source-of-truth** cosecha para validar forecasts |
| **Fact_areas_plantas** | Área (ha) + cantidad plantas por geografía, variedad, fecha | Bronce.Cosecha_SAP (area_raw, plantas_raw) | (fecha, geografia, variedad, condicion, campana) | Normalización rendimiento (kg/ha, kg/planta) |
| **Fact_Tasa_Crecimiento_Brotes** | Tasa elongación brotes (cm/día) desde poda → vigor vegetativo | Bronce.Tasa_Crecimiento_Brotes → Calculate dias_desde_poda + growth_rate | (fecha, geografia, variedad, personal, condicion, codigo_ensayo, campana) | Vigor vegetativo + timing óptimo poda |
| **Fact_Telemetria_Clima** | Telemetría continua por hora: T, humedad, lluvia, radiación, VPD, GDD calculado | Bronce.Telemetria_Clima (hourly logs) → Parse FechaHora | (fecha_hora, sector_climatico, id_tiempo, campana) | Modelado fisiología continuo + alerta enfermedad + scheduling riego |
| **Fact_Tareo** | Horas trabajadas por persona, actividad, labor, fecha, geografía | Bronce.Consolidado_Tareos → JOIN Dim_Personal + Dim_Actividad | (fecha, personal, actividad_operativa, geografia, campana) | Allocation costo labor + KPIs productividad |
| **Fact_Proyecciones** | Proyección semanal de cosecha: kg_proyectados por escenario (base/optimista/pesimista) + MAPE accuracy + override flags | Modelo ML (6-week rolling) → Stored with version control | (fecha_evento, fecha_cutoff, geografia, variedad, escenario, campana, estado_workflow) | **Weekly forecast** para supply chain + modelo accuracy tracking |

---

## GOLD: Marts de Agregación para Power BI (12 tablas)

Tablas denormalizadas, grano semanal (Semana_ISO), listas para visualización. Cada Mart es TRUNCATE + INSERT al actualizar.

| Mart | Qué muestra | Grain | Fuentes principales | Usuarios |
|------|-------------|-------|-----------------|---------|
| **Mart_Cosecha** | Cosecha semanal actual vs forecast (kg neto vs kg proyectados, % cumplimiento, jabas) | (semana_iso, geografia, variedad, campana) | Fact_Cosecha_SAP + Fact_Proyecciones | Sales/Supply Chain |
| **Mart_Proyecciones** | Forecast ejecutivo semanal: kg_proyectados (escenario base), MAPE, override audit, estado workflow | (semana_iso, geografia, variedad, escenario, campana) | Fact_Proyecciones | Exec/Planning |
| **Mart_Fenologia** | Progresión fenológica semanal: conteo por etapa + brotes productivos + color cinta + estado fenológico | (semana_iso, modulo, variedad, estado_fenologico, campana) | Fact_Conteo_Fenologico + Fact_Fisiologia + Fact_Ciclos_Fenologicos | Agronomía/Harvesting |
| **Mart_Clima** | Resumen clima diario: T_avg, T_max/min, VPD, humedad, lluvia, GDD acumulado por sector/semana | (id_tiempo, sector, semana_iso, campana) con cálculos Tetens + GDD | Fact_Telemetria_Clima | Agronomía/Crop Protection |
| **Mart_Pesos_Calibres** | Análisis peso baya por etapa + calibre (pequeño/mediano/grande): avg g/baya, distribución | (semana_iso, geografia, variedad, campana) | Fact_Evaluacion_Pesos + Bronce.Calibres | Quality/Harvest |
| **Mart_Evaluacion_Vegetativa** | Resumen estructura vegetal por piso: brotes promedio, productivos, altura, diámetro, ratio productivo | (semana_iso, piso, geografia, variedad, campana) | Fact_Evaluacion_Vegetativa | Agronomía |
| **Mart_Ciclo_Poda** | Calidad de poda semanal: promedio tallos, longitud, diámetro, defectos, muestra count | (semana_iso, geografia, variedad, campana) | Fact_Ciclo_Poda | Field QA |
| **Mart_Tasa_Crecimiento** | Tasa de crecimiento brotes: cm/día por condición (experimento/control) + geografía | (semana_iso, geografia, variedad, condicion, campana) | Fact_Tasa_Crecimiento_Brotes | Agronomía/Pruning |
| **Mart_Induccion_Floral** | Eficacia inducción floración fuera estación: % plantas+brotes con flores | (geografia, variedad, campana) | Fact_Induccion_Floral | Counter-Seasonal Crop Mgmt |
| **Mart_Administrativo** | KPIs labor semanal: horas trabajadas, asertividad %, días trabajados, obs SAP, supervisor | (semana_iso, dni, actividad, campana) | Fact_Tareo + Dim_Personal | HR/Operations |
| **Mart_Censo_Plantas** | Salud población semanal: plantas buenas/regulares/malas, tasa attrition | (semana_iso, geografia, variedad, campana) | Fact_Censo_Plantas | Field Health |
| **Mart_Fenologia** (alt) | aka "Mart_Frutos": conteo semanal por etapa, productividad estimada | (semana_iso, modulo, variedad, campana) | Fact_Conteo_Fenologico | Harvest Scheduling |

---

## CONTROL, AUDITORIA & CONFIGURACIÓN (5 tablas)

| Esquema | Tabla | Propósito |
|---------|-------|----------|
| **Auditoria** | Carga_Archivos | Línea de trazabilidad: archivo → tabla → fecha carga → estado (OK/ERROR) → filas insertadas → errores detectados |
| **Control** | Parametros_Pipeline | Configuración ETL: fact_bloqueantes, escenario_oficial_id, horizon_proyecciones_semanas, umbral_rechazo_%, homologacion_mdm_config |
| **Seguridad** | Roles_Acceso | Control acceso: (rol, tabla, permiso) → Portal MDM user groups & table-level read/write/admin |
| **Config** | Homologacion_MDM | Master data rules: (tabla_destino, valor_raw, valor_normalizado, activo, fecha_vigencia_inicio/fin) |
| | (bonus) Calendario | Dim_Tiempo pre-generado si se almacena en Config en vez de solo en memoria |

---

## FLUJOS DE DATOS CLAVE

### 1. **Forecast Semanal (6 semanas)**
```
Bronce.Conteo_Fruta 
  → Fact_Conteo_Fenologico (count by etapa)
     + Fact_Evaluacion_Pesos (weight trajectory)
     + Fact_Fisiologia (bud viability)
     + Fact_Telemetria_Clima (VPD/GDD)
  → Projection Model (ML 6-week forward)
     → Fact_Proyecciones (escenarios: Conservative/Base/Optimistic)
        → Mart_Proyecciones (Power BI)
        + (vs) Fact_Cosecha_SAP → MAPE accuracy tracking
```

### 2. **Harvest Readiness**
```
Bronce.Ciclos_Fenologicos (color ribbon tracking)
Bronce.Maduracion (dias desde marcado)
  → Fact_Ciclos_Fenologicos
     → Mart_Fenologia (ripeness stage %)
     → Harvest schedule recommendation (when % > X → pick window)
```

### 3. **Labor Costing**
```
Bronce.Consolidado_Tareos (horas + actividad + dni)
  → JOIN Dim_Personal (MDM → nombre, rol, asertivity)
  → JOIN Dim_Actividad_Operativa (MDM → labor code, cost center)
  → Fact_Tareo
     → Mart_Administrativo (weekly hours, KPIs)
```

### 4. **Climate-Crop Physiology**
```
Bronce.Telemetria_Clima (hourly logger data)
  → Fact_Telemetria_Clima (parse + calc VPD Tetens, GDD)
     → Mart_Clima (daily summary by sector, week grain)
        → DSS: disease risk (fungi when RH>90% + T 15-25°C)
        → Irrigation scheduling (VPD threshold)
```

---

## CONVENIOS Y PATRONES

### Convenciones de Nombres
- **Bronce:** `_Raw` suffix para todas las columnas (e.g., `Fecha_Raw`, `Modulo_Raw`)
- **Silver:** Nombres limpios sin `_Raw`; columnas tipo datos específicos (INT, DECIMAL, DATE)
- **Gold:** Denormalizados; prefijo `Mart_` para público Power BI

### Deduplicación & Quality Gates
- Bronce: `WHERE NOT EXISTS` check antes de INSERT para evitar duplicados
- Silver: `Estado_DQ` = 'Aprobado' por defecto; rechazados flagged como 'Error'
- Gold: Solo inserta si todos los facts bloqueantes (Cosecha_SAP, Conteo, Pesos, Clima, Fisiologia, Peladas, Induccion, Tasa_Crecimiento, Ciclo_Poda) completaron sin ERROR

### MDM (Homologación)
Todas las dimensiones (Variedad, Fundo, Sector, Modulo, Turno, Valvula, Cama) se limpian contra `Config.Homologacion_MDM` antes de cargar a Silver. Portal MDM permite agregar nuevas reglas sin redeploy de ETL.

### Vigencia & Auditoría
- Silver dims: `Fecha_Creacion`, `Fecha_Modificacion`, `Es_Activa` flags
- Facts: `Fecha_Sistema`, `ID_Origen_Bronce` (linkback)
- Proyecciones: `Flag_Override`, `Motivo_Override`, `Version_Modelo`, `MAPE` para tracking

---

## CASOS DE USO POR USUARIO

### 🌾 Agronomía/Field Manager
- **Mart_Fenologia:** ¿En qué etapa están las frutas? → Momento óptimo cosecha
- **Mart_Evaluacion_Vegetativa:** ¿Qué tan vigorosa está la planta? → Predicción enfermedad
- **Mart_Clima:** ¿Riesgo de hongos? (RH>90% + T óptima) → Alertas tratamiento
- **Mart_Ciclo_Poda:** ¿Calidad de poda? → QA operativa

### 📊 Supply Chain / Venta
- **Mart_Cosecha:** ¿Cuánto cosechamos vs forecast? → Cumplimiento cliente
- **Mart_Proyecciones:** ¿Cuánto esperar próximas 6 semanas? → Offer planning

### 👤 HR / Administración
- **Mart_Administrativo:** ¿Horas trabajadas? ¿Quién más asertivo? → Payroll + performance

### 🤖 Data Science / Proyecciones
- **Fact_Proyecciones:** Versiones modelo, MAPE histórico, overrides → Model drift detection
- **Fact_Telemetria_Clima:** VPD/GDD diarios → Features para modelos de fisiología

---

## ARCHIVOS CLAVE DEL CÓDIGO

| Path | Propósito |
|------|----------|
| `/bronce/rutas.py` | Mapeo carpeta Excel → tabla Bronce destino |
| `/bronce/cargador.py` | Lectura Excel, normalización, validación layout, inserción |
| `/silver/dims/dim_geografia.py` | Construcción jerarquía geografía 6-niveles |
| `/silver/facts/*.py` | 14+ transformadores Bronce→Silver c/ MDM + homologación |
| `/gold/marts.py` | Refresh de 12 Marts (TRUNCATE + INSERT) |
| `/sql_migrations/DDL_*_v3.sql` | Schema + tablas completo (autogenerado) |
| `/config/parametros.py` | Facts bloqueantes, escenario oficial, umbrales DQ |
| `/auditoria/log.py` | Logging de inicio/fin carga + trazabilidad |

---

## RESUMEN EJECUTIVO

**79 tablas totales**, arquitectura Medallion probada:
- **Bronce (25):** Raw ingestion desde campo (Excel) + SAP; preserva 100% original + audit trail
- **Silver (37):** Cleaned, deduped, MDM-homologadas, typed; 14+ facts operacionales
- **Gold (12):** Agregados semanales denormalizados → Power BI dashboards
- **Control (5):** Auditoría, parámetros, seguridad, homologación rules

**Ciclo operacional:**
1. **Carga Bronce:** T+1 diaria (archivos Excel de campo + extracts SAP)
2. **Silver:** Transformación inmediata (homologación MDM, cálculos, dedup)
3. **Gold:** Si todos los facts bloqueantes completaron sin error → Refresh Marts
4. **Power BI:** Conecta SOLO a Gold (12 Marts públicos)

**KPIs centrales:** Forecasting (MAPE tracking), Cosecha (actual vs plan), Fenología (stage %), Labor (horas+asertivity), Clima (VPD/GDD risk alerts)
