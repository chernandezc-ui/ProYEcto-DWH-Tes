-- =============================================================================
-- fase35_optimizaciones_etl.sql
-- =============================================================================
-- Refactorizacion de indices existentes y nuevos indices de cobertura
-- para acelerar el refresco de Marts Gold y queries analiticas.
--
-- PREREQUISITOS: Fases 1-34 aplicadas.
-- BASE DE DATOS:  ACP_DataWarehose_Proyecciones
-- IDEMPOTENTE:    Si — todos los bloques usan IF NOT EXISTS / IF EXISTS.
--
-- PROBLEMA RESUELTO:
--   Los indices creados en fase34 incluian columnas metricas (Kg, Cantidades)
--   como KEY columns en lugar de INCLUDE columns. Esto causa:
--   - Arboles B+ mas anchos y lentos de recorrer
--   - Inserciones mas costosas durante ETL (mas splits de pagina)
--   - No mejora los JOINs de Gold (que filtran por IDs, no por metricas)
--
-- ESTRATEGIA:
--   1. DROP + CREATE de indices existentes con estructura corregida
--   2. CREATE de nuevos indices para facts sin cobertura Gold
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

SET QUOTED_IDENTIFIER ON;
GO

PRINT '=== fase35: Inicio de optimizaciones ETL ===';
PRINT CONVERT(NVARCHAR, GETDATE(), 120);
GO

-- =============================================================================
-- BLOQUE 1: Refactorizar IX_FactCosecha_Tiempo_Variedad
-- -----------------------------------------------------------------------------
-- ANTES:  Keys(ID_Geografia, Kg_Neto_MP, Kg_Brutos, Cantidad_Jabas, Estado_DQ,
--              ID_Tiempo, ID_Variedad)
-- DESPUES: Keys(ID_Tiempo, ID_Variedad, ID_Geografia)
--          Include(Kg_Neto_MP, Kg_Brutos, Cantidad_Jabas, Estado_DQ,
--                  ID_Condicion_Cultivo, ID_Campana, Fecha_Evento)
-- =============================================================================

PRINT '--- BLOQUE 1: Refactorizar IX_FactCosecha_Tiempo_Variedad ---';
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactCosecha_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Cosecha_SAP')
)
BEGIN
    DROP INDEX IX_FactCosecha_Tiempo_Variedad ON Silver.Fact_Cosecha_SAP;
    PRINT 'Eliminado: IX_FactCosecha_Tiempo_Variedad (estructura anterior).';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactCosecha_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Cosecha_SAP')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactCosecha_Tiempo_Variedad
        ON Silver.Fact_Cosecha_SAP (ID_Tiempo, ID_Variedad, ID_Geografia)
        INCLUDE (Kg_Neto_MP, Kg_Brutos, Cantidad_Jabas, Estado_DQ,
                 ID_Condicion_Cultivo, ID_Campana, Fecha_Evento);
    PRINT 'Creado: IX_FactCosecha_Tiempo_Variedad (estructura optimizada).';
END
GO

-- =============================================================================
-- BLOQUE 2: Refactorizar IX_FactConteoFen_Tiempo_Estado
-- -----------------------------------------------------------------------------
-- ANTES:  Keys(ID_Geografia, ID_Variedad, Cantidad_Organos, Estado_DQ,
--              ID_Tiempo, ID_Estado_Fenologico)
-- DESPUES: Keys(ID_Tiempo, ID_Estado_Fenologico, ID_Geografia, ID_Variedad)
--          Include(Cantidad_Organos, Estado_DQ, ID_Campana)
-- =============================================================================

PRINT '--- BLOQUE 2: Refactorizar IX_FactConteoFen_Tiempo_Estado ---';
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactConteoFen_Tiempo_Estado'
      AND object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
)
BEGIN
    DROP INDEX IX_FactConteoFen_Tiempo_Estado ON Silver.Fact_Conteo_Fenologico;
    PRINT 'Eliminado: IX_FactConteoFen_Tiempo_Estado (estructura anterior).';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactConteoFen_Tiempo_Estado'
      AND object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactConteoFen_Tiempo_Estado
        ON Silver.Fact_Conteo_Fenologico (ID_Tiempo, ID_Estado_Fenologico, ID_Geografia, ID_Variedad)
        INCLUDE (Cantidad_Organos, Estado_DQ, ID_Campana);
    PRINT 'Creado: IX_FactConteoFen_Tiempo_Estado (estructura optimizada).';
END
GO

-- =============================================================================
-- BLOQUE 3: Refactorizar IX_FactPeladas_Tiempo_Variedad
-- -----------------------------------------------------------------------------
-- ANTES:  Keys(ID_Geografia, Bayas_Cosechables, Bayas_Maduras, Muestras,
--              Estado_DQ, ID_Tiempo, ID_Variedad)
-- DESPUES: Keys(ID_Tiempo, ID_Variedad, ID_Geografia)
--          Include(Botones_Florales, Flores, Bayas_Pequenas, Bayas_Grandes,
--                  Fase_1, Fase_2, Bayas_Cremas, Bayas_Maduras,
--                  Bayas_Cosechables, Plantas_Productivas,
--                  Plantas_No_Productivas, Muestras, Estado_DQ, ID_Campana)
-- =============================================================================

PRINT '--- BLOQUE 3: Refactorizar IX_FactPeladas_Tiempo_Variedad ---';
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactPeladas_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Peladas')
)
BEGIN
    DROP INDEX IX_FactPeladas_Tiempo_Variedad ON Silver.Fact_Peladas;
    PRINT 'Eliminado: IX_FactPeladas_Tiempo_Variedad (estructura anterior).';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactPeladas_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Peladas')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactPeladas_Tiempo_Variedad
        ON Silver.Fact_Peladas (ID_Tiempo, ID_Variedad, ID_Geografia)
        INCLUDE (Botones_Florales, Flores, Bayas_Pequenas, Bayas_Grandes,
                 Fase_1, Fase_2, Bayas_Cremas, Bayas_Maduras,
                 Bayas_Cosechables, Plantas_Productivas,
                 Plantas_No_Productivas, Muestras, Estado_DQ, ID_Campana);
    PRINT 'Creado: IX_FactPeladas_Tiempo_Variedad (estructura optimizada).';
END
GO

-- =============================================================================
-- BLOQUE 4: Refactorizar IX_FactFisiologia_Tiempo_Variedad
-- -----------------------------------------------------------------------------
-- ANTES:  Keys(ID_Geografia, Tercio, Brotes_Productivos, Brotes_Vegetativos,
--              Total_Organos, Estado_DQ, ID_Tiempo, ID_Variedad)
-- DESPUES: Keys(ID_Tiempo, ID_Variedad, ID_Geografia)
--          Include(Tercio, Brotes_Productivos, Brotes_Vegetativos,
--                  Hinchadas, Productivas, Total_Organos, Estado_DQ, ID_Campana)
-- =============================================================================

PRINT '--- BLOQUE 4: Refactorizar IX_FactFisiologia_Tiempo_Variedad ---';
GO

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactFisiologia_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Fisiologia')
)
BEGIN
    DROP INDEX IX_FactFisiologia_Tiempo_Variedad ON Silver.Fact_Fisiologia;
    PRINT 'Eliminado: IX_FactFisiologia_Tiempo_Variedad (estructura anterior).';
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactFisiologia_Tiempo_Variedad'
      AND object_id = OBJECT_ID('Silver.Fact_Fisiologia')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactFisiologia_Tiempo_Variedad
        ON Silver.Fact_Fisiologia (ID_Tiempo, ID_Variedad, ID_Geografia)
        INCLUDE (Tercio, Brotes_Productivos, Brotes_Vegetativos,
                 Hinchadas, Productivas, Total_Organos, Estado_DQ, ID_Campana);
    PRINT 'Creado: IX_FactFisiologia_Tiempo_Variedad (estructura optimizada).';
END
GO

-- =============================================================================
-- BLOQUE 5: Nuevo indice de cobertura en Fact_Evaluacion_Pesos
-- -----------------------------------------------------------------------------
-- Mart_Fenologia y Mart_Pesos_Calibres hacen subqueries:
--   SELECT ID_Tiempo, ID_Geografia, ID_Variedad,
--          SUM(Cantidad_Bayas_Muestra), AVG(Peso_Promedio_Baya_g)
--   FROM Silver.Fact_Evaluacion_Pesos
--   GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
-- Sin indice, esto es un Full Table Scan.
-- =============================================================================

PRINT '--- BLOQUE 5: Indice cobertura en Fact_Evaluacion_Pesos ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactPesos_Gold_Cobertura'
      AND object_id = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactPesos_Gold_Cobertura
        ON Silver.Fact_Evaluacion_Pesos (ID_Tiempo, ID_Geografia, ID_Variedad)
        INCLUDE (Peso_Promedio_Baya_g, Cantidad_Bayas_Muestra,
                 Peso_Proyectado_Baya_g, Estado_DQ, ID_Personal, ID_Campana);
    PRINT 'Creado: IX_FactPesos_Gold_Cobertura en Silver.Fact_Evaluacion_Pesos.';
END
ELSE
    PRINT 'OMITIDO: IX_FactPesos_Gold_Cobertura ya existe.';
GO

-- =============================================================================
-- BLOQUE 6: Nuevo indice de cobertura en Fact_Maduracion
-- -----------------------------------------------------------------------------
-- Mart_Fenologia y Mart_Maduracion hacen subqueries con joins a Dim_Cinta:
--   SELECT m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad,
--          m.ID_Estado_Fenologico, m.ID_Cinta, ...
--   FROM Silver.Fact_Maduracion m
--   GROUP BY m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad, ...
-- El indice existente (ID_Geografia, ID_Tiempo) no cubre ID_Variedad ni metricas.
-- =============================================================================

PRINT '--- BLOQUE 6: Indice cobertura en Fact_Maduracion ---';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_FactMaduracion_Gold_Cobertura'
      AND object_id = OBJECT_ID('Silver.Fact_Maduracion')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_FactMaduracion_Gold_Cobertura
        ON Silver.Fact_Maduracion (ID_Tiempo, ID_Geografia, ID_Variedad)
        INCLUDE (ID_Estado_Fenologico, ID_Cinta,
                 Dias_Pasados_Del_Marcado, ID_Campana);
    PRINT 'Creado: IX_FactMaduracion_Gold_Cobertura en Silver.Fact_Maduracion.';
END
ELSE
    PRINT 'OMITIDO: IX_FactMaduracion_Gold_Cobertura ya existe.';
GO

-- =============================================================================
-- REGISTRO EN CONTROL DE MIGRACIONES
-- =============================================================================

IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas WHERE Nombre_Fase = 'fase35_optimizaciones_etl'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES ('fase35_optimizaciones_etl', GETDATE(),
            'Refactorizacion de indices (metricas a INCLUDE) + cobertura Gold para Pesos y Maduracion');
    PRINT 'Registrado en Silver.Migraciones_Aplicadas.';
END
GO

-- =============================================================================
-- RESUMEN
-- =============================================================================

PRINT '';
PRINT '=== fase35: Optimizaciones ETL completadas ===';
PRINT 'BLOQUE 1  — Refactorizado IX_FactCosecha_Tiempo_Variedad (Keys=IDs, Include=metricas)';
PRINT 'BLOQUE 2  — Refactorizado IX_FactConteoFen_Tiempo_Estado (Keys=IDs, Include=metricas)';
PRINT 'BLOQUE 3  — Refactorizado IX_FactPeladas_Tiempo_Variedad (Keys=IDs, Include=metricas)';
PRINT 'BLOQUE 4  — Refactorizado IX_FactFisiologia_Tiempo_Variedad (Keys=IDs, Include=metricas)';
PRINT 'BLOQUE 5  — Nuevo IX_FactPesos_Gold_Cobertura (cobertura para Mart_Fenologia/Pesos)';
PRINT 'BLOQUE 6  — Nuevo IX_FactMaduracion_Gold_Cobertura (cobertura para Mart_Fenologia/Maduracion)';
PRINT CONVERT(NVARCHAR, GETDATE(), 120);
GO
