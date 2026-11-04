# Esquema Autoritativo — Mapeo Código ↔ DB

> **Propósito:** Prevenir regresiones por drift nombre-en-código ↔ nombre-en-DB durante reestructuras.  
> **Última actualización:** 2026-04-22  
> **Regla:** Cada vez que se renombre un objeto en SQL Server o en Python, actualizar este archivo **antes** del commit.

---

## Capas y Esquemas SQL

| Capa    | Schema SQL | Propósito                                   |
|---------|-----------|----------------------------------------------|
| Bronce  | `Bronce`  | Staging raw desde Excel (1:1 con archivos)   |
| Silver  | `Silver`  | Dimensiones y Facts normalizados             |
| Gold    | `Gold`    | Marts analíticos (vistas materializadas)     |
| MDM     | `MDM`     | Master Data Management (reglas, catálogos)   |
| Admin   | `Admin`   | Control plane (logs, migraciones, config)    |

---

## Dimensiones Silver

| Nombre en Código (Python)       | Tabla/Vista en DB                   | Tipo | Notas                                             |
|---------------------------------|-------------------------------------|------|---------------------------------------------------|
| `Dim_Geografia`                 | `Silver.Dim_Geografia`              | V    | Vista emuladora (fase26), apunta a `_Base`        |
| `Dim_Geografia_Base`            | `Silver.Dim_Geografia_Base`         | U    | Tabla real, arquitectura catálogos (fase25)        |
| `Dim_Geografia_Obsoleta`        | `Silver.Dim_Geografia_Obsoleta`     | U    | Legacy, solo lectura para rescate de datos         |
| `Dim_Fundo_Catalogo`           | `Silver.Dim_Fundo_Catalogo`        | U    | Catálogo normalizado de fundos                     |
| `Dim_Sector_Catalogo`          | `Silver.Dim_Sector_Catalogo`       | U    | Catálogo normalizado de sectores                   |
| `Dim_Modulo_Catalogo`          | `Silver.Dim_Modulo_Catalogo`       | U    | Catálogo de módulos (Modulo + SubModulo)           |
| `Dim_Turno_Catalogo`           | `Silver.Dim_Turno_Catalogo`        | U    | Catálogo de turnos                                 |
| `Dim_Valvula_Catalogo`         | `Silver.Dim_Valvula_Catalogo`      | U    | Catálogo de válvulas                               |
| `Dim_Cama_Catalogo`            | `Silver.Dim_Cama_Catalogo`         | U    | Catálogo de camas (normalizado)                    |
| `Bridge_Geografia_Cama`        | `Silver.Bridge_Geografia_Cama`     | U    | Relación N:M Geografía-Cama                        |
| `Bridge_Modulo_Campana`        | `Silver.Bridge_Modulo_Campana`     | U    | Relación Módulo-Variedad-Campaña con fechas        |
| `Dim_Personal`                 | `Silver.Dim_Personal`              | U    | SCD1 por DNI                                       |
| `Dim_Tiempo`                   | `Silver.Dim_Tiempo`                | U    | Calendario (ID_Tiempo = YYYYMMDD)                  |
| `Dim_Variedad`                 | `Silver.Dim_Variedad`              | U    | Variedades de arándano                             |
| `Dim_Estado_Fenologico`        | `Silver.Dim_Estado_Fenologico`     | U    | Estados fenológicos canónicos                      |
| `Dim_Actividad_Operativa`      | `Silver.Dim_Actividad_Operativa`   | U    | Actividades de tareo                               |
| `Dim_Cinta`                    | `Silver.Dim_Cinta`                 | U    | Colores de cinta (maduración)                      |
| `Dim_Campana`                  | `Silver.Dim_Campana`               | U    | Campañas agrícolas                                 |
| `vDim_Geografia`               | `Silver.vDim_Geografia`            | V    | Vista de compatibilidad (lookup legacy)            |

---

## Facts Silver

| Procesador Python                   | Bronce (Origen)                  | Silver (Destino)                        |
|-------------------------------------|----------------------------------|-----------------------------------------|
| `fact_cosecha_sap.py`               | `Bronce.Cosecha_SAP`             | `Silver.Fact_Cosecha_SAP`               |
| `fact_conteo_fenologico.py`         | `Bronce.Conteo_Fruta`            | `Silver.Fact_Conteo_Fenologico`         |
| `fact_maduracion.py`                | `Bronce.Maduracion`              | `Silver.Fact_Maduracion`                |
| `fact_peladas.py`                   | `Bronce.Peladas`                 | `Silver.Fact_Peladas`                   |
| `fact_telemetria_clima.py`          | `Bronce.Telemetria_Clima`        | `Silver.Fact_Telemetria_Clima`          |
| `fact_evaluacion_pesos.py`          | `Bronce.Evaluacion_Pesos`        | `Silver.Fact_Evaluacion_Pesos`          |
| `fact_tareo.py`                     | `Bronce.Consolidado_Tareos`      | `Silver.Fact_Tareo`                     |
| `fact_fisiologia.py`                | `Bronce.Fisiologia`              | `Silver.Fact_Fisiologia`                |
| `fact_evaluacion_vegetativa.py`     | `Bronce.Evaluacion_Vegetativa`   | `Silver.Fact_Evaluacion_Vegetativa`     |
| `fact_induccion_floral.py`          | `Bronce.Induccion_Floral`        | `Silver.Fact_Induccion_Floral`          |
| `fact_tasa_crecimiento_brotes.py`   | `Bronce.Tasa_Crecimiento_Brotes` | `Silver.Fact_Tasa_Crecimiento_Brotes`   |
| `fact_censo_plantas.py`             | `Bronce.Seguimiento_Errores`     | `Silver.Fact_Censo_Plantas`             |
| `fact_ciclo_poda.py`                | `Bronce.Evaluacion_Calidad_Poda` | `Silver.Fact_Ciclo_Poda` *(grain por punto: `[Geo, Tiempo, Variedad, Tipo_Evaluacion, Punto]`; Gold suma + reporta `N_Muestras`)* |

---

## Tablas MDM

| Nombre en Código          | Tabla en DB                          | Propósito                                     |
|--------------------------|--------------------------------------|------------------------------------------------|
| `Regla_Modulo_Raw`       | `MDM.Regla_Modulo_Raw`              | Mapeo Modulo_Raw → (Modulo_Int, SubModulo_Int) |
| `Regla_Modulo_Turno_SubModulo` | `MDM.Regla_Modulo_Turno_SubModulo` | Reglas por rango de turno                 |
| `Catalogo_Geografia`     | `MDM.Catalogo_Geografia`            | Geografías aprendidas (learning table)         |
| `Diccionario_Homologacion` | `MDM.Diccionario_Homologacion`    | Homologación de variedades y otros campos      |
| `Cuarentena`             | `MDM.Cuarentena`                    | Registros rechazados por DQ                    |

---

## Errores Históricos por Drift Código↔DB

| Fecha       | Error                                          | Causa Raíz                                                         | Fix                           |
|-------------|------------------------------------------------|--------------------------------------------------------------------|-------------------------------|
| 2026-04-22  | `Invalid object name 'Silver.Dim_Geografia_Base'` | Tabla no creada porque fase25 no se había aplicado               | Aplicar `fase25_versionar_ddl_geografia_catalogos.sql` |
| 2026-04-21  | FK apunta a `Dim_Geografia_Obsoleta`            | Migraciones aplicadas fuera de orden                              | `fase28_redirigir_fk_geografia_nueva.sql`              |
| 2026-04-20  | Alias `tmp.ID_Geografia` no encontrado          | Código Python referencia alias temporal post-renombrado           | Actualizar SQL dinámico en `_base_processor`            |
| 2026-04-16  | Columnas planas en SP de Cama                   | SP esperaba columnas nuevas que aún no existían en tabla          | `fase29_fix_sp_upsert_cama_nueva_arquitectura.sql`     |
| 2026-05-18  | Silver.Fact_Ciclo_Poda colapsaba puntos por valvula | Grain `[Geo, Tiempo, Variedad, Tipo_Eval]` ignoraba `Punto_Raw`; Gold hacía `AVG()` sobre falsos promedios | `fase37_restructurar_ciclo_poda.sql` + `fase38_renombrar_mart_ciclo_poda.sql` (Silver granular por punto, Gold `SUM(...) + N_Muestras`) |

---

## Convenciones de Nombres

| Concepto              | Patrón DB                      | Patrón Python                        |
|-----------------------|--------------------------------|--------------------------------------|
| Fact Table            | `Silver.Fact_{NombrePascal}`   | `fact_{nombre_snake}.py`             |
| Dimension             | `Silver.Dim_{NombrePascal}`    | `dim_{nombre_snake}.py`              |
| Catálogo normalizado  | `Silver.Dim_{X}_Catalogo`      | Variable: `id_{x}` (int)            |
| Bridge table          | `Silver.Bridge_{A}_{B}`        | N/A (usado en SQL directo)           |
| Tabla Bronce          | `Bronce.{NombrePascal}`        | Constante `TABLA_ORIGEN` en cada fact|
| Vista emuladora       | `Silver.vDim_{X}` o `Silver.Dim_{X}` (VIEW) | Usado desde `lookup.py`   |
| Stored Procedure      | `Silver.sp_{Verbo}_{Objeto}`   | Llamado via `EXEC` en `pipeline.py`  |
