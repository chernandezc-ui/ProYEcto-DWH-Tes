/* ============================================================================
   Fase 70 — Consolidación de Capa Gold y eliminación de PowerBI
   ========================================================================== */

USE [ACP_DataWarehose_Proyecciones];
GO

PRINT '=== Iniciando Fase 70: Limpieza de vistas PowerBI ===';
GO

PRINT '=== Modificando vistas Gold (Consolidación con descriptores) ===';
GO

-- 1. Gold.Mart_Fisiologia
DROP TABLE IF EXISTS Gold.Mart_Fisiologia;
GO
CREATE OR ALTER VIEW Gold.Mart_Fisiologia AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.Tercio) AS ID_Mart_Fisiologia,
        f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, ISNULL(f.ID_Campana, 0) AS ID_Campana,
        f.Tercio,
        AVG(CAST(f.Brotes_Productivos AS DECIMAL(10,2))) AS Brotes_Productivos_Promedio, 
        AVG(CAST(f.Brotes_Vegetativos AS DECIMAL(10,2))) AS Brotes_Vegetativos_Promedio,
        AVG(CAST(f.Hinchadas AS DECIMAL(10,2))) AS Hinchadas_Promedio, 
        AVG(CAST(f.Productivas AS DECIMAL(10,2))) AS Productivas_Promedio, 
        AVG(CAST(f.Total_Organos AS DECIMAL(10,2))) AS Total_Organos_Promedio,
        CAST(AVG(f.Brotes_Productivos) AS DECIMAL(10,2)) / NULLIF(AVG(f.Brotes_Vegetativos), 0) AS Ratio_Productivo_Veg
    FROM Silver.Fact_Fisiologia f
    GROUP BY
        f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, ISNULL(f.ID_Campana, 0), f.Tercio
)
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
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
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

-- 2. Gold.Mart_Evaluacion_Vegetativa
DROP TABLE IF EXISTS Gold.Mart_Evaluacion_Vegetativa;
GO
CREATE OR ALTER VIEW Gold.Mart_Evaluacion_Vegetativa AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.ID_Campana, f.Piso) AS ID_Mart_Vegetativa,
        f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.ID_Campana,
        f.Piso,
        AVG(CAST(f.Semanas_Despues_Poda AS DECIMAL(10,2))) AS Semanas_Despues_Poda_Promedio,
        AVG(f.Altura)                                   AS Altura_Promedio,
        AVG(f.Tallos_Basales)                           AS Tallos_Basales_Promedio,
        AVG(f.Tallos_Basales_Nuevos)                    AS Tallos_Basales_Nuevos_Promedio,
        SUM(f.Muestra_Plantas)                          AS Muestra_Plantas_Total,
        AVG(f.Brotes_Generales)                         AS Brotes_Generales_Promedio,
        AVG(f.Brotes_Productivos)                       AS Brotes_Productivos_Promedio,
        AVG(f.Diametro_Brote)                           AS Diametro_Brote_Promedio,
        COUNT(*)                                        AS N_Muestras,
        CAST(AVG(f.Brotes_Productivos) AS DECIMAL(10,2)) / NULLIF(AVG(f.Brotes_Generales), 0) AS Ratio_Productivo_General
    FROM Silver.Fact_Evaluacion_Vegetativa f
    WHERE f.Estado_DQ = 'OK'
    GROUP BY f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.ID_Campana, f.Piso
)
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
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
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

-- 3. Gold.Mart_Maduracion
DROP TABLE IF EXISTS Gold.Mart_Maduracion;
GO
CREATE OR ALTER VIEW Gold.Mart_Maduracion AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY cf.ID_Tiempo, cf.ID_Geografia, cf.ID_Variedad) AS ID_Mart_Maduracion,
        cf.ID_Tiempo,
        cf.ID_Geografia,
        cf.ID_Variedad,
        CAST(0 AS INT) AS ID_Campana,
        cf.ID_Estado_Fenologico,
        cf.ID_Cinta
    FROM Silver.Fact_Ciclos_Fenologicos cf
)
SELECT
    m.ID_Mart_Maduracion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    ef.Nombre_Estado AS Estado_Fenologico,
    ef.Orden_Estado,
    ci.Color_Cinta,
    CAST(NULL AS INT) AS Organos_Observados,
    CAST(NULL AS DECIMAL(8,2)) AS Dias_Pasados_Promedio,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
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

-- 4. Gold.Mart_Tasa_Crecimiento
DROP TABLE IF EXISTS Gold.Mart_Tasa_Crecimiento;
GO
CREATE OR ALTER VIEW Gold.Mart_Tasa_Crecimiento AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo) AS ID_Mart_Crecimiento,
        tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, ISNULL(tc.ID_Campana, 0) AS ID_Campana,
        tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo,
        AVG(CAST(tc.Cantidad AS DECIMAL(10,4))) AS Medida_Crecimiento_Promedio, 
        MAX(CAST(tc.Cantidad AS DECIMAL(10,4))) AS Medida_Crecimiento_Max,
        COUNT(*) AS Cantidad_Mediciones
    FROM Silver.Fact_Tasa_Crecimiento_Brotes tc
    GROUP BY tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, ISNULL(tc.ID_Campana, 0), tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo
)
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
    CAST(NULL AS DECIMAL(8,2)) AS Dias_Desde_Poda_Promedio, m.Cantidad_Mediciones,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
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

-- 5. Gold.Mart_Induccion_Floral
DROP TABLE IF EXISTS Gold.Mart_Induccion_Floral;
GO
CREATE OR ALTER VIEW Gold.Mart_Induccion_Floral AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, i.Tipo_Evaluacion) AS ID_Mart_Induccion,
        i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, ISNULL(i.ID_Campana, 0) AS ID_Campana,
        i.Tipo_Evaluacion,
        AVG(i.Pct_Plantas_Con_Induccion) AS Pct_Plantas_Con_Induccion_Prom,
        AVG(i.Pct_Brotes_Con_Induccion) AS Pct_Brotes_Con_Induccion_Prom,
        AVG(i.Pct_Brotes_Con_Flor) AS Pct_Brotes_Con_Flor_Prom,
        SUM(i.Cantidad_Brotes_Totales) AS Brotes_Totales,
        SUM(i.Cantidad_Brotes_Con_Flor) AS Brotes_Con_Flor
    FROM Silver.Fact_Induccion_Floral i
    GROUP BY i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, ISNULL(i.ID_Campana, 0), i.Tipo_Evaluacion
)
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
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
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

-- 6. Gold.Mart_Ciclo_Poda
DROP TABLE IF EXISTS Gold.Mart_Ciclo_Poda;
GO
CREATE OR ALTER VIEW Gold.Mart_Ciclo_Poda AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, p.Tipo_Evaluacion) AS ID_Mart_Poda,
        p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, ISNULL(p.ID_Campana, 0) AS ID_Campana,
        p.Tipo_Evaluacion,
        SUM(p.Tallos_Planta) AS Tallos_Planta_Total, 
        SUM(p.Longitud_Tallo) AS Longitud_Tallo_Total,
        SUM(p.Diametro_Tallo) AS Diametro_Tallo_Total, 
        SUM(p.Ramilla_Planta) AS Ramilla_Planta_Total,
        SUM(p.Tocones_Planta) AS Tocones_Planta_Total, 
        SUM(p.Cortes_Defectuosos) AS Cortes_Defectuosos_Total,
        SUM(p.Altura_Poda) AS Altura_Poda_Total, 
        COUNT(*) AS N_Muestras
    FROM Silver.Fact_Ciclo_Poda p
    GROUP BY p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, ISNULL(p.ID_Campana, 0), p.Tipo_Evaluacion
)
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
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
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

-- 7. Gold.Mart_Peladas
DROP TABLE IF EXISTS Gold.Mart_Peladas;
GO
CREATE OR ALTER VIEW Gold.Mart_Peladas AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY pel.ID_Tiempo, pel.ID_Geografia, pel.ID_Variedad) AS ID_Mart_Peladas,
        pel.ID_Tiempo,
        pel.ID_Geografia,
        pel.ID_Variedad,
                SUM(CASE WHEN pel.ID_Estado_Fenologico = 1 THEN pel.Cantidad ELSE 0 END) AS Botones_Florales_Total, 
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 2 THEN pel.Cantidad ELSE 0 END) AS Flores_Total, 
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 3 THEN pel.Cantidad ELSE 0 END) AS Bayas_Pequenas_Total,
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 4 THEN pel.Cantidad ELSE 0 END) AS Bayas_Grandes_Total, 
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 5 THEN pel.Cantidad ELSE 0 END) AS Fase_1_Total, 
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 6 THEN pel.Cantidad ELSE 0 END) AS Fase_2_Total,
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 7 THEN pel.Cantidad ELSE 0 END) AS Bayas_Cremas_Total, 
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 8 THEN pel.Cantidad ELSE 0 END) AS Bayas_Maduras_Total,
        SUM(CASE WHEN pel.ID_Estado_Fenologico = 9 THEN pel.Cantidad ELSE 0 END) AS Bayas_Cosechables_Total,
        SUM(pel.Plantas_Productivas) AS Plantas_Productivas_Total, 
        SUM(pel.Plantas_No_Productivas) AS Plantas_No_Productivas_Total,
        SUM(pel.Muestras) AS Muestras_Total,
        CAST(SUM(CASE WHEN pel.ID_Estado_Fenologico = 9 THEN pel.Cantidad ELSE 0 END) AS DECIMAL(10,2)) / NULLIF(SUM(CASE WHEN pel.ID_Estado_Fenologico IN (1,2,3,4,5,6,7,8) THEN pel.Cantidad ELSE 0 END), 0) * 100 AS Pct_Cosechable
    FROM Silver.Fact_Peladas pel
    GROUP BY pel.ID_Tiempo, pel.ID_Geografia, pel.ID_Variedad
)
SELECT
    m.ID_Mart_Peladas,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Botones_Florales_Total, m.Flores_Total, m.Bayas_Pequenas_Total, m.Bayas_Grandes_Total,
    m.Fase_1_Total, m.Fase_2_Total, m.Bayas_Cremas_Total, m.Bayas_Maduras_Total,
    m.Bayas_Cosechables_Total, m.Plantas_Productivas_Total, m.Plantas_No_Productivas_Total,
    m.Muestras_Total, m.Pct_Cosechable,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON t.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

-- 8. Gold.Mart_Censo_Plantas
DROP TABLE IF EXISTS Gold.Mart_Censo_Plantas;
GO
CREATE OR ALTER VIEW Gold.Mart_Censo_Plantas AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY c.ID_Tiempo, c.ID_Geografia, c.ID_Variedad, c.ID_Campana, c.Linea_Raw) AS ID_Mart_Censo,
        c.ID_Tiempo, c.ID_Geografia, c.ID_Variedad, ISNULL(c.ID_Campana, 0) AS ID_Campana,
        c.ID_Estado_Planta,
        SUM(c.Cantidad) AS Cantidad, 
        c.Linea_Raw
    FROM Silver.Fact_Censo_Plantas c
    GROUP BY c.ID_Tiempo, c.ID_Geografia, c.ID_Variedad, c.ID_Campana, c.ID_Estado_Planta, c.Linea_Raw
)
SELECT
    m.ID_Mart_Censo,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    ep.Nombre_Estado AS Estado_Planta, m.Cantidad, m.Linea_Raw,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Estado_Planta ep ON m.ID_Estado_Planta = ep.ID_Estado_Planta
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

-- 9. Gold.Mart_Cosecha
DROP TABLE IF EXISTS Gold.Mart_Cosecha;
GO
CREATE OR ALTER VIEW Gold.Mart_Cosecha AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY cs.ID_Tiempo, cs.ID_Geografia, cs.ID_Variedad) AS ID_Mart_Cosecha,
        cs.ID_Tiempo, cs.ID_Geografia, cs.ID_Variedad, ISNULL(cs.ID_Campana, 0) AS ID_Campana,
        cs.ID_Condicion_Cultivo,
        CAST(cs.Fecha_Evento AS DATE) AS Fecha_Cosecha,
        cs.Kg_Neto_MP AS Kg_Neto_Real,
        cs.Kg_Neto_MP AS Kg_Neto_MP,
        CAST(cs.Fecha_Evento AS NVARCHAR) AS Fecha_Evento
    FROM Silver.Fact_Cosecha_SAP cs
)
SELECT
    m.ID_Mart_Cosecha,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    c.Sustrato AS Condicion, m.Fecha_Cosecha, m.Fecha_Evento,
    m.Kg_Neto_Real, CAST(NULL AS DECIMAL(12,4)) AS Kg_Brutos, m.Kg_Neto_MP, 
    p.Kg_Proyectados AS Kg_Proyectados, p.Kg_Proyectados AS Kg_Proyectado,
    CAST(NULL AS DECIMAL(8,2)) AS Pct_Cumplimiento, CAST(NULL AS INT) AS Cantidad_Jabas, 
    CAST(NULL AS DECIMAL(10,2)) AS Peso_Promedio_Jaba_kg,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Condicion_Cultivo c ON m.ID_Condicion_Cultivo = c.ID_Condicion
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo
LEFT JOIN Silver.Fact_Proyecciones p ON p.ID_Tiempo = m.ID_Tiempo AND p.ID_Variedad = m.ID_Variedad AND p.ID_Geografia = m.ID_Geografia AND p.ID_Escenario = 4;
GO

-- 10. Gold.Mart_Proyecciones
DROP TABLE IF EXISTS Gold.Mart_Proyecciones;
GO
CREATE OR ALTER VIEW Gold.Mart_Proyecciones AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad) AS ID_Mart_Proyeccion,
        p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, p.ID_Escenario, ISNULL(p.ID_Campana, 0) AS ID_Campana,
        p.Fecha_Cutoff, p.Kg_Proyectados, CAST(p.MAPE AS NVARCHAR(50)) AS MAPE, p.MAPE AS Error_MAPE,
        p.Version_Modelo, p.Flag_Override, p.Motivo_Override, p.ID_Estado_Workflow,
        CAST(p.Fecha_Sistema AS DATE) AS Fecha_Generacion
    FROM Silver.Fact_Proyecciones p
),
RealKg AS (
    SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Kg_Neto_MP) AS Kg_Real
    FROM Silver.Fact_Cosecha_SAP
    GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
)
SELECT
    m.ID_Mart_Proyeccion,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    t.Semana_ISO AS Semana_Objetivo,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    e.Tipo_Escenario, e.Descripcion AS Descripcion_Escenario,
    e.Tipo_Escenario AS Version_Escenario, m.Version_Modelo, w.Estado AS Estado_Workflow,
    m.Fecha_Generacion, m.Fecha_Cutoff,
    m.Kg_Proyectados, r.Kg_Real, m.Error_MAPE, m.MAPE, CAST(NULL AS DECIMAL(12,4)) AS Desviacion_kg,
    m.Flag_Override, m.Motivo_Override,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Escenario_Proyeccion e ON m.ID_Escenario = e.ID_Escenario
LEFT JOIN Silver.Dim_Estado_Workflow w ON m.ID_Estado_Workflow = w.ID_Workflow
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo
LEFT JOIN RealKg r ON r.ID_Tiempo = m.ID_Tiempo AND r.ID_Geografia = m.ID_Geografia AND r.ID_Variedad = m.ID_Variedad;
GO

-- 11. Gold.Mart_Fenologia
DROP TABLE IF EXISTS Gold.Mart_Fenologia;
GO
CREATE OR ALTER VIEW Gold.Mart_Fenologia AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY t.Semana_ISO, mc.Modulo, v.Nombre_Variedad, ef.Nombre_Estado) AS ID_Mart_Fenologia,
        t.Semana_ISO, mc.Modulo, v.Nombre_Variedad AS Variedad, ef.Nombre_Estado AS Estado_Fenologico, ef.Orden_Estado,
        cf.ID_Tiempo, cf.ID_Geografia, cf.ID_Variedad
    FROM Silver.Fact_Conteo_Fenologico cf
    JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = cf.ID_Tiempo
    JOIN Silver.Dim_Geografia g ON g.ID_Geografia = cf.ID_Geografia
    LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
    JOIN Silver.Dim_Variedad v ON v.ID_Variedad = cf.ID_Variedad
    JOIN Silver.Dim_Estado_Fenologico ef ON ef.ID_Estado_Fenologico = cf.ID_Estado_Fenologico
)
SELECT
    m.ID_Mart_Fenologia,
    m.Semana_ISO, m.Modulo, m.Variedad,
    COALESCE(MAX(mad.Color_Cinta), 'Sin Cinta') AS Color_Cinta,
    m.Estado_Fenologico, m.Orden_Estado,
    MAX(pes.Cantidad_Bayas) AS Cantidad_Bayas, CAST(NULL AS DECIMAL(5,2)) AS Pct_Cosechable,
    MAX(fis.Brotes_Productivos) AS Brotes_Productivos, MAX(fis.Brotes_Vegetativos) AS Brotes_Vegetativos,
    CAST(NULL AS DECIMAL(5,2)) AS Pct_Avance_Ciclo, CAST(NULL AS DECIMAL(10,2)) AS Ratio_Productivo_Veg,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN (
    SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Brotes_Productivos) as Brotes_Productivos, SUM(Brotes_Vegetativos) as Brotes_Vegetativos
    FROM Silver.Fact_Fisiologia GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
) fis ON fis.ID_Tiempo = m.ID_Tiempo AND fis.ID_Geografia = m.ID_Geografia AND fis.ID_Variedad = m.ID_Variedad
LEFT JOIN (
    SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Cantidad_Cosechables) as Cantidad_Bayas
    FROM Silver.Fact_Evaluacion_Pesos GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
) pes ON pes.ID_Tiempo = m.ID_Tiempo AND pes.ID_Geografia = m.ID_Geografia AND pes.ID_Variedad = m.ID_Variedad
LEFT JOIN (
     SELECT t_mad.Semana_ISO, fcf.ID_Geografia, fcf.ID_Variedad, MAX(c.Color_Cinta) as Color_Cinta
     FROM Silver.Fact_Ciclos_Fenologicos fcf
     JOIN Silver.Dim_Tiempo t_mad ON t_mad.ID_Tiempo = fcf.ID_Tiempo
     JOIN Silver.Dim_Cinta c ON c.ID_Cinta = fcf.ID_Cinta
     WHERE fcf.ID_Cinta IS NOT NULL
     GROUP BY t_mad.Semana_ISO, fcf.ID_Geografia, fcf.ID_Variedad
) mad ON mad.Semana_ISO = m.Semana_ISO AND mad.ID_Geografia = m.ID_Geografia AND mad.ID_Variedad = m.ID_Variedad
GROUP BY m.ID_Mart_Fenologia, m.Semana_ISO, m.Modulo, m.Variedad, m.Estado_Fenologico, m.Orden_Estado;
GO

-- 12. Gold.Mart_Clima
DROP TABLE IF EXISTS Gold.Mart_Clima;
GO
CREATE OR ALTER VIEW Gold.Mart_Clima AS
WITH horaria AS (
    SELECT
        cl.ID_Tiempo, cl.Sector_Climatico, ISNULL(cl.ID_Campana, 0) AS ID_Campana,
        cl.Fecha_Hora, cl.Temp_Exterior_C, cl.Temp_Maxima_C, cl.Temp_Minima_C,
        cl.Humedad_Externa_Pct, cl.Lluvia_mm, cl.Indice_UV, cl.Radiacion_Solar_Wm2,
        CASE
            WHEN cl.Temp_Exterior_C IS NOT NULL AND cl.Humedad_Externa_Pct IS NOT NULL
            THEN 0.6108 * EXP(17.27 * cl.Temp_Exterior_C / (cl.Temp_Exterior_C + 237.3)) * (1.0 - cl.Humedad_Externa_Pct / 100.0)
        END AS VPD_Horario,
        CASE
            WHEN cl.Temp_Exterior_C IS NULL THEN NULL
            ELSE (cl.Temp_Exterior_C - 10.0) *
                 (DATEDIFF(SECOND, LAG(cl.Fecha_Hora) OVER (PARTITION BY cl.Sector_Climatico ORDER BY cl.Fecha_Hora), cl.Fecha_Hora) / 86400.0)
        END AS GDD_Intervalo
    FROM Silver.Fact_Telemetria_Clima cl
),
Base AS (
    SELECT h.ID_Tiempo, h.Sector_Climatico, h.ID_Campana,
           AVG(h.Temp_Exterior_C) AS Temp_Promedio_Diaria, MAX(h.Temp_Maxima_C) AS Temp_Maxima_Dia, MIN(h.Temp_Minima_C) AS Temp_Minima_Dia,
           AVG(h.Humedad_Externa_Pct) AS Humedad_Promedio, SUM(h.Lluvia_mm) AS Precipitacion_Total,
           MAX(h.Indice_UV) AS Indice_UV_Max, MIN(h.Indice_UV) AS Indice_UV_Min,
           AVG(CASE WHEN DATEPART(HOUR, h.Fecha_Hora) BETWEEN 6 AND 18 THEN h.Radiacion_Solar_Wm2 END) AS Radiacion_Solar_Prom_Diurna,
           MAX(h.Radiacion_Solar_Wm2) AS Radiacion_Solar_Max, AVG(h.VPD_Horario) AS VPD_Promedio, SUM(h.GDD_Intervalo) AS GDD
    FROM horaria h GROUP BY h.ID_Tiempo, h.Sector_Climatico, h.ID_Campana
)
SELECT
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    m.Sector_Climatico,
    m.Temp_Promedio_Diaria, m.Temp_Maxima_Dia, m.Temp_Minima_Dia,
    m.Humedad_Promedio, m.Precipitacion_Total,
    m.Indice_UV_Max, m.Indice_UV_Min,
    m.Radiacion_Solar_Prom_Diurna, m.Radiacion_Solar_Max,
    m.VPD_Promedio, m.GDD
FROM Base m
LEFT JOIN Silver.Dim_Tiempo  t  ON m.ID_Tiempo  = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana ca ON m.ID_Campana = m.ID_Campana;
GO

-- 13. Gold.Mart_Pesos_Calibres
DROP TABLE IF EXISTS Gold.Mart_Pesos_Calibres;
GO
CREATE OR ALTER VIEW Gold.Mart_Pesos_Calibres AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY ep.ID_Tiempo, ep.ID_Geografia, ep.ID_Variedad) AS ID_Mart_Pesos,
        ep.ID_Tiempo, ep.ID_Geografia, ep.ID_Variedad, ISNULL(ep.ID_Campana, 0) AS ID_Campana,
        SUM(ep.Peso_Promedio_Baya_g * ep.Cantidad_Bayas_Muestra) / NULLIF(SUM(ep.Cantidad_Bayas_Muestra), 0) AS Peso_Promedio_Baya_g,
        SUM(ep.Cantidad_Cosechables) AS Cant_Bayas_Muestra,
        MAX(ep.ID_Personal) AS ID_Personal, MAX(ep.Estado_DQ) AS Estado_DQ,
        (SUM(ep.Peso_Promedio_Baya_g * ep.Cantidad_Bayas_Muestra) / NULLIF(SUM(ep.Cantidad_Bayas_Muestra), 0)) - LAG((SUM(ep.Peso_Promedio_Baya_g * ep.Cantidad_Bayas_Muestra) / NULLIF(SUM(ep.Cantidad_Bayas_Muestra), 0))) OVER (PARTITION BY ep.ID_Geografia, ep.ID_Variedad ORDER BY ep.ID_Tiempo) AS Tendencia_Peso
    FROM Silver.Fact_Evaluacion_Pesos ep
    GROUP BY ep.ID_Tiempo, ep.ID_Geografia, ep.ID_Variedad, ISNULL(ep.ID_Campana, 0)
)
SELECT
    m.ID_Mart_Pesos,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    dp.Nombre_Completo AS Evaluador,
    m.Cant_Bayas_Muestra, m.Peso_Promedio_Baya_g, CAST(NULL AS DECIMAL(10,2)) AS Peso_Proyectado_Baya_g,
    m.Tendencia_Peso, m.Estado_DQ, SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Variedad v  ON m.ID_Variedad = v.ID_Variedad
LEFT JOIN Silver.Dim_Geografia       g  ON m.ID_Geografia      = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo  fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Sector_Catalogo sc ON g.ID_Sector_Catalogo = sc.ID_Sector_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo
LEFT JOIN Silver.Dim_Personal dp ON dp.ID_Personal = m.ID_Personal;
GO

-- 14. Gold.Mart_Administrativo
DROP TABLE IF EXISTS Gold.Mart_Administrativo;
GO
CREATE OR ALTER VIEW Gold.Mart_Administrativo AS
WITH Base AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY ta.ID_Tiempo, ta.ID_Personal, ta.ID_Actividad_Operativa) AS ID_Mart_Admin,
        ta.ID_Tiempo, ta.ID_Personal, ta.ID_Actividad_Operativa AS ID_Actividad, ISNULL(ta.ID_Campana, 0) AS ID_Campana,
        MAX(ta.ID_Personal_Supervisor) AS ID_Supervisor,
        SUM(ta.Horas_Trabajadas) AS Horas_Trabajadas, SUM(ta.Horas_Trabajadas) AS Horas_Trabajadas_Total,
        SUM(CAST(ta.Es_Observado_SAP AS INT)) AS Registros_Observados_SAP,
        COUNT(DISTINCT ta.ID_Tiempo) AS Dias_Trabajados
    FROM Silver.Fact_Tareo ta
    GROUP BY ta.ID_Tiempo, ta.ID_Personal, ta.ID_Actividad_Operativa, ISNULL(ta.ID_Campana, 0)
)
SELECT
    m.ID_Mart_Admin,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    p.Nombre_Completo AS Nombre_Personal, p.DNI AS DNI_Personal,
    p.Sexo, p.Rol, COALESCE(sp.Nombre_Completo, 'Sin Supervisor') AS Supervisor,
    ao.Nombre_Actividad AS Actividad, ao.Nombre_Labor AS Labor, ao.Categoria,
    m.Horas_Trabajadas, m.Horas_Trabajadas_Total, m.Dias_Trabajados,
    p.Pct_Asertividad, m.Registros_Observados_SAP, SYSDATETIME() AS Fecha_Actualizacion
FROM Base m
LEFT JOIN Silver.Dim_Tiempo   t  ON m.ID_Tiempo   = t.ID_Tiempo
LEFT JOIN Silver.Dim_Campana  ca ON m.ID_Campana  = ca.ID_Campana
LEFT JOIN Silver.Dim_Personal p  ON m.ID_Personal = p.ID_Personal
LEFT JOIN Silver.Dim_Personal sp ON sp.ID_Personal = m.ID_Supervisor
LEFT JOIN Silver.Dim_Actividad_Operativa ao ON m.ID_Actividad = ao.ID_Actividad;
GO

PRINT '=== Fase 70 completada exitosamente ===';
GO
