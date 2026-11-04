/* ============================================================================
   Fase 68 — Conversión de Capa Gold a Vistas SQL & Limpieza Previa
   ========================================================================== */

USE [ACP_DataWarehose_Proyecciones];
GO

PRINT '=== Iniciando Fase 68: Limpieza de vistas PowerBI ===';
DROP VIEW IF EXISTS PowerBI.vw_Cosecha;
DROP VIEW IF EXISTS PowerBI.vw_Censo_Plantas;
DROP VIEW IF EXISTS PowerBI.vw_Ciclo_Poda;
DROP VIEW IF EXISTS PowerBI.vw_Evaluacion_Vegetativa;
DROP VIEW IF EXISTS PowerBI.vw_Fisiologia;
DROP VIEW IF EXISTS PowerBI.vw_Induccion_Floral;
DROP VIEW IF EXISTS PowerBI.vw_Tasa_Crecimiento;
DROP VIEW IF EXISTS PowerBI.vw_Pesos_Calibres;
DROP VIEW IF EXISTS PowerBI.vw_Proyecciones;
DROP VIEW IF EXISTS PowerBI.vw_Maduracion;
DROP VIEW IF EXISTS PowerBI.vw_Clima;
DROP VIEW IF EXISTS PowerBI.vw_Administrativo;
DROP VIEW IF EXISTS PowerBI.vw_Fenologia;
GO

PRINT '=== Limpiando Tablas y Vistas Físicas de Gold ===';
DROP VIEW IF EXISTS Gold.Mart_Cosecha;
DROP TABLE IF EXISTS Gold.Mart_Cosecha;

DROP VIEW IF EXISTS Gold.Mart_Proyecciones;
DROP TABLE IF EXISTS Gold.Mart_Proyecciones;

DROP VIEW IF EXISTS Gold.Mart_Fenologia;
DROP TABLE IF EXISTS Gold.Mart_Fenologia;

DROP VIEW IF EXISTS Gold.Mart_Clima;
DROP TABLE IF EXISTS Gold.Mart_Clima;

DROP VIEW IF EXISTS Gold.Mart_Pesos_Calibres;
DROP TABLE IF EXISTS Gold.Mart_Pesos_Calibres;

DROP VIEW IF EXISTS Gold.Mart_Administrativo;
DROP TABLE IF EXISTS Gold.Mart_Administrativo;

DROP VIEW IF EXISTS Gold.Mart_Fisiologia;
DROP TABLE IF EXISTS Gold.Mart_Fisiologia;

DROP VIEW IF EXISTS Gold.Mart_Evaluacion_Vegetativa;
DROP TABLE IF EXISTS Gold.Mart_Evaluacion_Vegetativa;

DROP VIEW IF EXISTS Gold.Mart_Tasa_Crecimiento;
DROP TABLE IF EXISTS Gold.Mart_Tasa_Crecimiento;

DROP VIEW IF EXISTS Gold.Mart_Induccion_Floral;
DROP TABLE IF EXISTS Gold.Mart_Induccion_Floral;

DROP VIEW IF EXISTS Gold.Mart_Ciclo_Poda;
DROP TABLE IF EXISTS Gold.Mart_Ciclo_Poda;

DROP VIEW IF EXISTS Gold.Mart_Censo_Plantas;
DROP TABLE IF EXISTS Gold.Mart_Censo_Plantas;

DROP VIEW IF EXISTS Gold.Mart_Peladas;
DROP TABLE IF EXISTS Gold.Mart_Peladas;

DROP VIEW IF EXISTS Gold.Mart_Maduracion;
DROP TABLE IF EXISTS Gold.Mart_Maduracion;
GO

PRINT '=== Creando Vistas del esquema Gold ===';
GO

-- 1. Gold.Mart_Fisiologia
CREATE VIEW Gold.Mart_Fisiologia AS
SELECT
    ROW_NUMBER() OVER (ORDER BY f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.Tercio) AS ID_Mart_Fisiologia,
    f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, ISNULL(f.ID_Campana, 0) AS ID_Campana,
    fc.Fundo, mc.Modulo, v.Nombre_Variedad AS Variedad, t.Semana_ISO,
    f.Tercio,
    AVG(f.Brotes_Productivos) AS Brotes_Productivos_Promedio, 
    AVG(f.Brotes_Vegetativos) AS Brotes_Vegetativos_Promedio,
    AVG(f.Hinchadas) AS Hinchadas_Promedio, 
    AVG(f.Productivas) AS Productivas_Promedio, 
    AVG(f.Total_Organos) AS Total_Organos_Promedio,
    CAST(AVG(f.Brotes_Productivos) AS DECIMAL(10,2)) / NULLIF(AVG(f.Brotes_Vegetativos), 0) AS Ratio_Productivo_Veg,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Fisiologia f
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = f.ID_Tiempo
JOIN Silver.Dim_Geografia g ON g.ID_Geografia = f.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad v ON v.ID_Variedad = f.ID_Variedad
GROUP BY
    f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, ISNULL(f.ID_Campana, 0),
    fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, f.Tercio;
GO

-- 2. Gold.Mart_Evaluacion_Vegetativa
CREATE VIEW Gold.Mart_Evaluacion_Vegetativa AS
SELECT
    ROW_NUMBER() OVER (ORDER BY f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.ID_Campana, f.Piso) AS ID_Mart_Vegetativa,
    f.ID_Tiempo,
    f.ID_Geografia,
    f.ID_Variedad,
    f.ID_Campana,
    ISNULL(fundo.Fundo, 'SIN_FUNDO')               AS Fundo,
    ISNULL(mod_cat.Modulo, 0)                       AS Modulo,
    ISNULL(var.Nombre_Variedad, 'SIN_VARIEDAD')     AS Variedad,
    t.Semana_ISO,
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
    SYSDATETIME()                                   AS Fecha_Actualizacion,
    CAST(NULL AS NVARCHAR(100)) AS Tipo_Evaluacion,
    CAST(NULL AS INT) AS Plantas_Evaluadas_Total,
    CAST(NULL AS INT) AS Plantas_En_Floracion_Total,
    CAST(NULL AS DECIMAL(8,2)) AS Pct_Floracion_Promedio,
    CAST(AVG(f.Brotes_Productivos) AS DECIMAL(10,2)) / NULLIF(AVG(f.Brotes_Generales), 0) AS Ratio_Productivo_General
FROM Silver.Fact_Evaluacion_Vegetativa f
JOIN Silver.Dim_Tiempo t
    ON f.ID_Tiempo = t.ID_Tiempo
LEFT JOIN Silver.Dim_Geografia geo
    ON f.ID_Geografia = geo.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fundo
    ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mod_cat
    ON geo.ID_Modulo_Catalogo = mod_cat.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Variedad var
    ON f.ID_Variedad = var.ID_Variedad
WHERE f.Estado_DQ = 'OK'
GROUP BY
    f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.ID_Campana,
    ISNULL(fundo.Fundo, 'SIN_FUNDO'),
    ISNULL(mod_cat.Modulo, 0),
    ISNULL(var.Nombre_Variedad, 'SIN_VARIEDAD'),
    t.Semana_ISO,
    f.Piso;
GO

-- 3. Gold.Mart_Maduracion
CREATE VIEW Gold.Mart_Maduracion AS
SELECT
    ROW_NUMBER() OVER (ORDER BY cf.ID_Tiempo, cf.ID_Geografia, cf.ID_Variedad) AS ID_Mart_Maduracion,
    cf.ID_Tiempo,
    cf.ID_Geografia,
    cf.ID_Variedad,
    CAST(0 AS INT) AS ID_Campana,
    fc.Fundo,
    mc.Modulo,
    v.Nombre_Variedad AS Variedad,
    t.Semana_ISO,
    cf.ID_Estado_Fenologico,
    ef.Nombre_Estado AS Estado_Fenologico,
    cf.ID_Cinta,
    c.Color_Cinta,
    CAST(NULL AS INT) AS Organos_Observados,
    CAST(NULL AS DECIMAL(8,2)) AS Dias_Pasados_Promedio,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Ciclos_Fenologicos cf
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = cf.ID_Tiempo
JOIN Silver.Dim_Geografia g ON g.ID_Geografia = cf.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad v ON v.ID_Variedad = cf.ID_Variedad
LEFT JOIN Silver.Dim_Estado_Fenologico ef ON ef.ID_Estado_Fenologico = ef.ID_Estado_Fenologico
LEFT JOIN Silver.Dim_Cinta c ON c.ID_Cinta = cf.ID_Cinta;
GO

-- 4. Gold.Mart_Tasa_Crecimiento
CREATE VIEW Gold.Mart_Tasa_Crecimiento AS
SELECT
    ROW_NUMBER() OVER (ORDER BY tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo) AS ID_Mart_Crecimiento,
    tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, ISNULL(tc.ID_Campana, 0) AS ID_Campana,
    fc.Fundo, mc.Modulo, v.Nombre_Variedad AS Variedad, t.Semana_ISO,
    tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo,
    AVG(CAST(tc.Cantidad AS DECIMAL(10,4))) AS Medida_Crecimiento_Promedio, 
    MAX(CAST(tc.Cantidad AS DECIMAL(10,4))) AS Medida_Crecimiento_Max,
    CAST(NULL AS DECIMAL(8,2)) AS Dias_Desde_Poda_Promedio, 
    COUNT(*) AS Cantidad_Mediciones,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Tasa_Crecimiento_Brotes tc
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = tc.ID_Tiempo
JOIN Silver.Dim_Geografia g ON g.ID_Geografia = tc.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad v ON v.ID_Variedad = tc.ID_Variedad
GROUP BY
    tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, ISNULL(tc.ID_Campana, 0),
    fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
    tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo;
GO

-- 5. Gold.Mart_Induccion_Floral
CREATE VIEW Gold.Mart_Induccion_Floral AS
SELECT
    ROW_NUMBER() OVER (ORDER BY i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, i.Tipo_Evaluacion) AS ID_Mart_Induccion,
    i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, ISNULL(i.ID_Campana, 0) AS ID_Campana,
    fc.Fundo, mc.Modulo, v.Nombre_Variedad AS Variedad, t.Semana_ISO,
    i.Tipo_Evaluacion,
    AVG(i.Pct_Plantas_Con_Induccion) AS Pct_Plantas_Con_Induccion_Prom,
    AVG(i.Pct_Brotes_Con_Induccion) AS Pct_Brotes_Con_Induccion_Prom,
    AVG(i.Pct_Brotes_Con_Flor) AS Pct_Brotes_Con_Flor_Prom,
    SUM(i.Cantidad_Brotes_Totales) AS Brotes_Totales,
    SUM(i.Cantidad_Brotes_Con_Flor) AS Brotes_Con_Flor,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Induccion_Floral i
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = i.ID_Tiempo
JOIN Silver.Dim_Geografia g ON g.ID_Geografia = i.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad v ON v.ID_Variedad = i.ID_Variedad
GROUP BY
    i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, ISNULL(i.ID_Campana, 0),
    fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, i.Tipo_Evaluacion;
GO

-- 6. Gold.Mart_Ciclo_Poda
CREATE VIEW Gold.Mart_Ciclo_Poda AS
SELECT
    ROW_NUMBER() OVER (ORDER BY p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, p.Tipo_Evaluacion) AS ID_Mart_Poda,
    p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, ISNULL(p.ID_Campana, 0) AS ID_Campana,
    fc.Fundo, mc.Modulo, v.Nombre_Variedad AS Variedad, t.Semana_ISO,
    p.Tipo_Evaluacion,
    SUM(p.Tallos_Planta) AS Tallos_Planta_Total, 
    SUM(p.Longitud_Tallo) AS Longitud_Tallo_Total,
    SUM(p.Diametro_Tallo) AS Diametro_Tallo_Total, 
    SUM(p.Ramilla_Planta) AS Ramilla_Planta_Total,
    SUM(p.Tocones_Planta) AS Tocones_Planta_Total, 
    SUM(p.Cortes_Defectuosos) AS Cortes_Defectuosos_Total,
    SUM(p.Altura_Poda) AS Altura_Poda_Total, 
    COUNT(*) AS N_Muestras,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Ciclo_Poda p
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = p.ID_Tiempo
JOIN Silver.Dim_Geografia g ON g.ID_Geografia = p.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad v ON v.ID_Variedad = p.ID_Variedad
GROUP BY
    p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, ISNULL(p.ID_Campana, 0),
    fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, p.Tipo_Evaluacion;
GO

-- 7. Gold.Mart_Peladas
CREATE VIEW Gold.Mart_Peladas AS
SELECT
    ROW_NUMBER() OVER (ORDER BY pel.ID_Tiempo, pel.ID_Geografia, pel.ID_Variedad) AS ID_Mart_Peladas,
    pel.ID_Tiempo,
    pel.ID_Geografia,
    pel.ID_Variedad,
    ISNULL(t.ID_Campana, 0) AS ID_Campana,
    fc.Fundo,
    mc.Modulo,
    v.Nombre_Variedad AS Variedad,
    t.Semana_ISO,
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
    SYSDATETIME() AS Fecha_Actualizacion,
    CAST(SUM(CASE WHEN pel.ID_Estado_Fenologico = 9 THEN pel.Cantidad ELSE 0 END) AS DECIMAL(10,2)) / NULLIF(SUM(CASE WHEN pel.ID_Estado_Fenologico IN (1,2,3,4,5,6,7,8) THEN pel.Cantidad ELSE 0 END), 0) * 100 AS Pct_Cosechable
FROM Silver.Fact_Peladas pel
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = pel.ID_Tiempo
JOIN Silver.Dim_Geografia g ON g.ID_Geografia = pel.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad v ON v.ID_Variedad = pel.ID_Variedad
GROUP BY
    pel.ID_Tiempo, pel.ID_Geografia, pel.ID_Variedad, ISNULL(t.ID_Campana, 0),
    fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO;
GO

-- 8. Gold.Mart_Censo_Plantas
CREATE VIEW Gold.Mart_Censo_Plantas AS
SELECT
    ROW_NUMBER() OVER (ORDER BY c.ID_Tiempo, c.ID_Geografia, c.ID_Variedad, c.ID_Campana, c.Linea_Raw) AS ID_Mart_Censo,
    c.ID_Tiempo, c.ID_Geografia, c.ID_Variedad, ISNULL(c.ID_Campana, 0) AS ID_Campana,
    MAX(fc.Fundo) AS Fundo, 
    MAX(mc.Modulo) AS Modulo, 
    MAX(v.Nombre_Variedad) AS Variedad, 
    MAX(ep.Nombre_Estado) AS Estado_Planta,
    SUM(c.Cantidad) AS Cantidad, 
    c.Linea_Raw, 
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Censo_Plantas c
INNER JOIN Silver.Dim_Geografia g ON c.ID_Geografia = g.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON g.ID_Fundo_Catalogo = fc.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON g.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
INNER JOIN Silver.Dim_Variedad v ON c.ID_Variedad = v.ID_Variedad
INNER JOIN Silver.Dim_Estado_Planta ep ON c.ID_Estado_Planta = ep.ID_Estado_Planta
GROUP BY
    c.ID_Tiempo, c.ID_Geografia, c.ID_Variedad, c.ID_Campana, c.ID_Estado_Planta, c.Linea_Raw;
GO

-- 9. Gold.Mart_Cosecha
CREATE VIEW Gold.Mart_Cosecha AS
SELECT
    ROW_NUMBER() OVER (ORDER BY cs.ID_Tiempo, cs.ID_Geografia, cs.ID_Variedad) AS ID_Mart_Cosecha,
    cs.ID_Tiempo,
    cs.ID_Geografia,
    cs.ID_Variedad,
    ISNULL(cs.ID_Campana, 0) AS ID_Campana,
    fc.Fundo,
    mc.Modulo,
    tc.Turno,
    v.Nombre_Variedad AS Variedad,
    CAST(cs.Fecha_Evento AS DATE) AS Fecha_Cosecha,
    CAST(NULL AS DECIMAL(12,4)) AS Kg_Brutos,
    cs.Kg_Neto_MP AS Kg_Neto_Real,
    cs.Kg_Neto_MP AS Kg_Neto_MP,
    p.Kg_Proyectados AS Kg_Proyectados,
    p.Kg_Proyectados AS Kg_Proyectado,
    CAST(NULL AS INT) AS Cantidad_Jabas,
    c.Sustrato AS Condicion,
    CAST(cs.Fecha_Evento AS NVARCHAR) AS Fecha_Evento,
    SYSDATETIME() AS Fecha_Actualizacion,
    t.Semana_ISO,
    CAST(NULL AS DECIMAL(10,2)) AS Peso_Promedio_Jaba_kg,
    CAST(NULL AS DECIMAL(8,2)) AS Pct_Cumplimiento
FROM Silver.Fact_Cosecha_SAP cs
JOIN Silver.Dim_Tiempo             t  ON t.ID_Tiempo = cs.ID_Tiempo
JOIN Silver.Dim_Geografia          g  ON g.ID_Geografia = cs.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo tc ON tc.ID_Turno_Catalogo = g.ID_Turno_Catalogo
JOIN Silver.Dim_Variedad           v  ON v.ID_Variedad = cs.ID_Variedad
JOIN Silver.Dim_Condicion_Cultivo  c  ON c.ID_Condicion = cs.ID_Condicion_Cultivo
LEFT JOIN Silver.Fact_Proyecciones p
    ON  p.ID_Tiempo = cs.ID_Tiempo
    AND p.ID_Variedad = cs.ID_Variedad
    AND p.ID_Geografia = cs.ID_Geografia
    AND p.ID_Escenario = 4;
GO

-- 10. Gold.Mart_Proyecciones
CREATE VIEW Gold.Mart_Proyecciones AS
SELECT
    ROW_NUMBER() OVER (ORDER BY p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad) AS ID_Mart_Proyeccion,
    p.ID_Tiempo,
    p.ID_Geografia,
    p.ID_Variedad,
    p.ID_Escenario,
    ISNULL(p.ID_Campana, 0) AS ID_Campana,
    fc.Fundo,
    mc.Modulo,
    tc.Turno,
    v.Nombre_Variedad AS Variedad,
    p.Fecha_Cutoff,
    p.Kg_Proyectados,
    CAST(p.MAPE AS NVARCHAR(50)) AS MAPE,
    p.MAPE AS Error_MAPE,
    p.Version_Modelo,
    p.Flag_Override,
    p.Motivo_Override,
    w.Estado AS Estado_Workflow,
    t.Semana_ISO AS Semana_Objetivo,
    e.Tipo_Escenario AS Version_Escenario,
    CAST(p.Fecha_Sistema AS DATE) AS Fecha_Generacion,
    real.Kg_Real,
    SYSDATETIME() AS Fecha_Actualizacion,
    CAST(NULL AS DECIMAL(12,4)) AS Desviacion_kg
FROM Silver.Fact_Proyecciones p
JOIN Silver.Dim_Tiempo                t  ON t.ID_Tiempo = p.ID_Tiempo
JOIN Silver.Dim_Geografia             g  ON g.ID_Geografia = p.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo   fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo  mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo   tc ON tc.ID_Turno_Catalogo = g.ID_Turno_Catalogo
JOIN Silver.Dim_Variedad              v  ON v.ID_Variedad = p.ID_Variedad
JOIN Silver.Dim_Escenario_Proyeccion  e  ON e.ID_Escenario = p.ID_Escenario
JOIN Silver.Dim_Estado_Workflow       w  ON w.ID_Workflow = p.ID_Estado_Workflow
LEFT JOIN (
    SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Kg_Neto_MP) AS Kg_Real
    FROM Silver.Fact_Cosecha_SAP
    GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
) real ON real.ID_Tiempo = p.ID_Tiempo
       AND real.ID_Geografia = p.ID_Geografia
       AND real.ID_Variedad = p.ID_Variedad;
GO

-- 11. Gold.Mart_Fenologia
CREATE VIEW Gold.Mart_Fenologia AS
SELECT
    ROW_NUMBER() OVER (ORDER BY t.Semana_ISO, mc.Modulo, v.Nombre_Variedad, ef.Nombre_Estado) AS ID_Mart_Fenologia,
    t.Semana_ISO,
    mc.Modulo,
    v.Nombre_Variedad AS Variedad,
    COALESCE(MAX(mad.Color_Cinta), 'Sin Cinta') AS Color_Cinta,
    ef.Nombre_Estado AS Estado_Fenologico,
    ef.Orden_Estado,
    MAX(pes.Cantidad_Bayas) AS Cantidad_Bayas,
    CAST(NULL AS DECIMAL(5,2)) AS Pct_Cosechable,
    MAX(fis.Brotes_Productivos) AS Brotes_Productivos,
    MAX(fis.Brotes_Vegetativos) AS Brotes_Vegetativos,
    SYSDATETIME() AS Fecha_Actualizacion,
    CAST(NULL AS DECIMAL(5,2)) AS Pct_Avance_Ciclo,
    CAST(NULL AS DECIMAL(10,2)) AS Ratio_Productivo_Veg
FROM Silver.Fact_Conteo_Fenologico cf
JOIN Silver.Dim_Tiempo            t  ON t.ID_Tiempo = cf.ID_Tiempo
JOIN Silver.Dim_Geografia         g  ON g.ID_Geografia = cf.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad          v  ON v.ID_Variedad = cf.ID_Variedad
JOIN Silver.Dim_Estado_Fenologico ef ON ef.ID_Estado_Fenologico = cf.ID_Estado_Fenologico
LEFT JOIN (
    SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Brotes_Productivos) as Brotes_Productivos, SUM(Brotes_Vegetativos) as Brotes_Vegetativos
    FROM Silver.Fact_Fisiologia
    GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
) fis ON fis.ID_Tiempo = cf.ID_Tiempo AND fis.ID_Geografia = cf.ID_Geografia AND fis.ID_Variedad = cf.ID_Variedad
LEFT JOIN (
    SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Cantidad_Cosechables) as Cantidad_Bayas
    FROM Silver.Fact_Evaluacion_Pesos
    GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
) pes ON pes.ID_Tiempo = cf.ID_Tiempo AND pes.ID_Geografia = cf.ID_Geografia AND pes.ID_Variedad = cf.ID_Variedad
LEFT JOIN (
     SELECT 
         t_mad.Semana_ISO, 
         YEAR(t_mad.Fecha) as Anio_Cinta,
         fcf.ID_Geografia, 
         fcf.ID_Variedad, 
         MAX(c.Color_Cinta) as Color_Cinta
     FROM Silver.Fact_Ciclos_Fenologicos fcf
     JOIN Silver.Dim_Tiempo t_mad ON t_mad.ID_Tiempo = fcf.ID_Tiempo
     JOIN Silver.Dim_Cinta c ON c.ID_Cinta = fcf.ID_Cinta
     WHERE fcf.ID_Cinta IS NOT NULL
     GROUP BY t_mad.Semana_ISO, YEAR(t_mad.Fecha), fcf.ID_Geografia, fcf.ID_Variedad
) mad ON mad.Semana_ISO = t.Semana_ISO 
     AND mad.Anio_Cinta = YEAR(t.Fecha)
     AND mad.ID_Geografia = cf.ID_Geografia 
     AND mad.ID_Variedad = cf.ID_Variedad
GROUP BY
    t.Semana_ISO,
    mc.Modulo,
    v.Nombre_Variedad,
    ef.Nombre_Estado,
    ef.Orden_Estado;
GO

-- 12. Gold.Mart_Clima
CREATE VIEW Gold.Mart_Clima AS
WITH horaria AS (
    SELECT
        cl.ID_Tiempo,
        cl.Sector_Climatico,
        ISNULL(cl.ID_Campana, 0) AS ID_Campana,
        cl.Fecha_Hora,
        cl.Temp_Exterior_C,
        cl.Temp_Maxima_C,
        cl.Temp_Minima_C,
        cl.Humedad_Externa_Pct,
        cl.Lluvia_mm,
        cl.Indice_UV,
        cl.Radiacion_Solar_Wm2,
        CASE
            WHEN cl.Temp_Exterior_C IS NOT NULL
             AND cl.Humedad_Externa_Pct IS NOT NULL
            THEN 0.6108
               * EXP(17.27 * cl.Temp_Exterior_C / (cl.Temp_Exterior_C + 237.3))
               * (1.0 - cl.Humedad_Externa_Pct / 100.0)
        END AS VPD_Horario,
        CASE
            WHEN cl.Temp_Exterior_C IS NULL THEN NULL
            ELSE (cl.Temp_Exterior_C - 10.0) *
                 (DATEDIFF(SECOND,
                      LAG(cl.Fecha_Hora) OVER (
                          PARTITION BY cl.Sector_Climatico
                          ORDER BY cl.Fecha_Hora
                      ),
                      cl.Fecha_Hora) / 86400.0)
        END AS GDD_Intervalo
    FROM Silver.Fact_Telemetria_Clima cl
)
SELECT
    h.ID_Tiempo,
    h.Sector_Climatico,
    h.ID_Campana,
    t.Semana_ISO,
    AVG(h.Temp_Exterior_C) AS Temp_Promedio_Diaria,
    MAX(h.Temp_Maxima_C) AS Temp_Maxima_Dia,
    MIN(h.Temp_Minima_C) AS Temp_Minima_Dia,
    AVG(h.Humedad_Externa_Pct) AS Humedad_Promedio,
    SUM(h.Lluvia_mm) AS Precipitacion_Total,
    MAX(h.Indice_UV) AS Indice_UV_Max,
    MIN(h.Indice_UV) AS Indice_UV_Min,
    AVG(CASE WHEN DATEPART(HOUR, h.Fecha_Hora) BETWEEN 6 AND 18
             THEN h.Radiacion_Solar_Wm2 END) AS Radiacion_Solar_Prom_Diurna,
    MAX(h.Radiacion_Solar_Wm2) AS Radiacion_Solar_Max,
    AVG(h.VPD_Horario) AS VPD_Promedio,
    SUM(h.GDD_Intervalo) AS GDD
FROM horaria h
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = h.ID_Tiempo
GROUP BY h.ID_Tiempo, h.Sector_Climatico, h.ID_Campana, t.Semana_ISO;
GO

-- 13. Gold.Mart_Pesos_Calibres
CREATE VIEW Gold.Mart_Pesos_Calibres AS
SELECT
    ROW_NUMBER() OVER (ORDER BY ep.ID_Tiempo, ep.ID_Geografia, ep.ID_Variedad) AS ID_Mart_Pesos,
    ep.ID_Tiempo,
    ep.ID_Geografia,
    ep.ID_Variedad,
    ISNULL(ep.ID_Campana, 0) AS ID_Campana,
    fc.Fundo,
    mc.Modulo,
    v.Nombre_Variedad AS Variedad,
    t.Semana_ISO,
    SUM(ep.Peso_Promedio_Baya_g * ep.Cantidad_Bayas_Muestra) / NULLIF(SUM(ep.Cantidad_Bayas_Muestra), 0) AS Peso_Promedio_Baya_g,
    SUM(ep.Cantidad_Cosechables) AS Cant_Bayas_Muestra,
    MAX(dp.Nombre_Completo) AS Evaluador,
    CAST(NULL AS DECIMAL(10,2)) AS Peso_Proyectado_Baya_g,
    (SUM(ep.Peso_Promedio_Baya_g * ep.Cantidad_Bayas_Muestra) / NULLIF(SUM(ep.Cantidad_Bayas_Muestra), 0)) - LAG((SUM(ep.Peso_Promedio_Baya_g * ep.Cantidad_Bayas_Muestra) / NULLIF(SUM(ep.Cantidad_Bayas_Muestra), 0))) OVER (PARTITION BY ep.ID_Geografia, ep.ID_Variedad ORDER BY ep.ID_Tiempo) AS Tendencia_Peso,
    MAX(ep.Estado_DQ) AS Estado_DQ,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Evaluacion_Pesos ep
JOIN Silver.Dim_Tiempo    t  ON t.ID_Tiempo = ep.ID_Tiempo
JOIN Silver.Dim_Geografia g  ON g.ID_Geografia = ep.ID_Geografia
LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
JOIN Silver.Dim_Variedad  v  ON v.ID_Variedad = ep.ID_Variedad
LEFT JOIN Silver.Dim_Personal dp ON dp.ID_Personal = ep.ID_Personal
GROUP BY
    ep.ID_Tiempo, ep.ID_Geografia, ep.ID_Variedad, ISNULL(ep.ID_Campana, 0),
    fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO;
GO

-- 14. Gold.Mart_Administrativo
CREATE VIEW Gold.Mart_Administrativo AS
SELECT
    ROW_NUMBER() OVER (ORDER BY ta.ID_Tiempo, ta.ID_Personal, ta.ID_Actividad_Operativa) AS ID_Mart_Admin,
    ta.ID_Tiempo,
    ta.ID_Personal,
    ta.ID_Actividad_Operativa AS ID_Actividad,
    ISNULL(ta.ID_Campana, 0) AS ID_Campana,
    COALESCE(sp.Nombre_Completo, 'Sin Supervisor') AS Supervisor,
    t.Semana_ISO,
    SUM(ta.Horas_Trabajadas) AS Horas_Trabajadas_Total,
    SUM(ta.Horas_Trabajadas) AS Horas_Trabajadas,
    SUM(CAST(ta.Es_Observado_SAP AS INT)) AS Registros_Observados_SAP,
    dp.DNI AS DNI_Personal,
    dp.Nombre_Completo AS Nombre_Personal,
    dp.Sexo,
    dp.Rol,
    da.Nombre_Actividad AS Actividad,
    da.Nombre_Labor AS Labor,
    COUNT(DISTINCT t.Fecha) AS Dias_Trabajados,
    dp.Pct_Asertividad,
    SYSDATETIME() AS Fecha_Actualizacion
FROM Silver.Fact_Tareo ta
JOIN Silver.Dim_Tiempo      t  ON t.ID_Tiempo = ta.ID_Tiempo
JOIN Silver.Dim_Personal    dp ON dp.ID_Personal = ta.ID_Personal
LEFT JOIN Silver.Dim_Personal sp ON sp.ID_Personal = ta.ID_Personal_Supervisor
JOIN Silver.Dim_Actividad_Operativa da ON da.ID_Actividad = ta.ID_Actividad_Operativa
GROUP BY
    ta.ID_Tiempo, ta.ID_Personal, ta.ID_Actividad_Operativa, ISNULL(ta.ID_Campana, 0),
    sp.Nombre_Completo, t.Semana_ISO, dp.DNI, dp.Nombre_Completo, dp.Sexo, dp.Rol,
    da.Nombre_Actividad, da.Nombre_Labor, dp.Pct_Asertividad;
GO

PRINT '=== Recreando vistas del esquema PowerBI ===';
GO

-- 1. PowerBI.vw_Cosecha
CREATE VIEW PowerBI.vw_Cosecha AS
SELECT
    m.ID_Mart_Cosecha,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Turno, m.Condicion, m.Fecha_Cosecha, m.Fecha_Evento,
    m.Kg_Neto_Real, m.Kg_Brutos, m.Kg_Neto_MP, m.Kg_Proyectados, m.Kg_Proyectado,
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

-- 2. PowerBI.vw_Censo_Plantas
CREATE VIEW PowerBI.vw_Censo_Plantas AS
SELECT
    m.ID_Mart_Censo,
    t.Fecha, t.Anio, t.Mes, t.Nombre_Mes, t.Semana_ISO,
    COALESCE(ca.Nombre_Campana, 'SIN_CAMPAÑA') AS Nombre_Campana,
    COALESCE(fc.Fundo, '(sin asignar)') AS Fundo,
    sc.Sector, mc.Modulo, mc.SubModulo, mc.Tipo_Conduccion,
    tc.Turno, vc.Valvula, cc.Cama_Normalizada AS Cama,
    g.Codigo_SAP_Campo, g.Nivel_Granularidad,
    v.Nombre_Variedad AS Variedad, v.Breeder,
    m.Estado_Planta, m.Cantidad, m.Linea_Raw,
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

-- 3. PowerBI.vw_Ciclo_Poda
CREATE VIEW PowerBI.vw_Ciclo_Poda AS
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
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

-- 4. PowerBI.vw_Evaluacion_Vegetativa
CREATE VIEW PowerBI.vw_Evaluacion_Vegetativa AS
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

-- 5. PowerBI.vw_Fisiologia
CREATE VIEW PowerBI.vw_Fisiologia AS
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

-- 6. PowerBI.vw_Induccion_Floral
CREATE VIEW PowerBI.vw_Induccion_Floral AS
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
LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = mc.ID_Modulo_Catalogo
LEFT JOIN Silver.Dim_Turno_Catalogo  tc ON g.ID_Turno_Catalogo  = tc.ID_Turno_Catalogo
LEFT JOIN Silver.Dim_Valvula_Catalogo vc ON g.ID_Valvula_Catalogo = vc.ID_Valvula_Catalogo
LEFT JOIN Silver.Dim_Cama_Catalogo   cc ON g.ID_Cama_Catalogo    = cc.ID_Cama_Catalogo;
GO

-- 7. PowerBI.vw_Tasa_Crecimiento
CREATE VIEW PowerBI.vw_Tasa_Crecimiento AS
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

-- 8. PowerBI.vw_Pesos_Calibres
CREATE VIEW PowerBI.vw_Pesos_Calibres AS
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

-- 9. PowerBI.vw_Proyecciones
CREATE VIEW PowerBI.vw_Proyecciones AS
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

-- 10. PowerBI.vw_Maduracion
CREATE VIEW PowerBI.vw_Maduracion AS
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

-- 11. PowerBI.vw_Clima
CREATE VIEW PowerBI.vw_Clima AS
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

-- 12. PowerBI.vw_Administrativo
CREATE VIEW PowerBI.vw_Administrativo AS
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

-- 13. PowerBI.vw_Fenologia
CREATE VIEW PowerBI.vw_Fenologia AS
SELECT
    m.ID_Mart_Fenologia,
    m.Semana_ISO, m.Modulo, m.Variedad, m.Color_Cinta,
    m.Estado_Fenologico, m.Orden_Estado,
    m.Cantidad_Bayas, m.Pct_Cosechable, m.Pct_Avance_Ciclo,
    m.Brotes_Productivos, m.Brotes_Vegetativos, m.Ratio_Productivo_Veg,
    m.Fecha_Actualizacion
FROM Gold.Mart_Fenologia m;
GO

PRINT '=== Fase 68: Migración a vistas completada exitosamente ===';
GO
