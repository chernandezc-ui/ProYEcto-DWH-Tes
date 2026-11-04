-- =============================================================================
-- fase24_unique_indexes_silver_facts.sql
-- =============================================================================
-- Agrega UNIQUE INDEX a las 12 tablas Silver.Fact_* para garantizar integridad
-- de unicidad a nivel de base de datos, como segunda linea de defensa detras
-- del mecanismo WHERE NOT EXISTS del ETL Python.
--
-- INSTRUCCIONES DE EJECUCION:
--   1. Ejecutar PRIMERO el bloque de LIMPIEZA de cada tabla (elimina duplicados
--      existentes conservando solo el registro con menor PK).
--   2. Ejecutar DESPUES el bloque CREATE UNIQUE INDEX correspondiente.
--   3. Si CREATE UNIQUE INDEX falla, significa que quedan duplicados no limpiados
--      en esa tabla; revisar y limpiar manualmente antes de reintentar.
-- =============================================================================

USE [ACP_Proyecciones];
GO

-- =============================================================================
-- 1. Silver.Fact_Evaluacion_Pesos
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + ID_Personal
-- =============================================================================
-- Limpieza: conserva el registro con menor PK por grano
DELETE FROM Silver.Fact_Evaluacion_Pesos
WHERE ID_Evaluacion_Pesos NOT IN (
    SELECT MIN(ID_Evaluacion_Pesos)
    FROM Silver.Fact_Evaluacion_Pesos
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_EvalPesos_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_EvalPesos_Grain
    ON Silver.Fact_Evaluacion_Pesos (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal);
GO

-- =============================================================================
-- 2. Silver.Fact_Conteo_Fenologico
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + ID_Estado_Fenologico + Punto
-- =============================================================================
DELETE FROM Silver.Fact_Conteo_Fenologico
WHERE ID_Conteo_Fenologico NOT IN (
    SELECT MIN(ID_Conteo_Fenologico)
    FROM Silver.Fact_Conteo_Fenologico
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, ID_Estado_Fenologico, Punto
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_ConteoFen_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_ConteoFen_Grain
    ON Silver.Fact_Conteo_Fenologico (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Estado_Fenologico, Punto);
GO

-- =============================================================================
-- 3. Silver.Fact_Cosecha_SAP
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + ID_Condicion_Cultivo
-- =============================================================================
DELETE FROM Silver.Fact_Cosecha_SAP
WHERE ID_Cosecha_SAP NOT IN (
    SELECT MIN(ID_Cosecha_SAP)
    FROM Silver.Fact_Cosecha_SAP
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, ID_Condicion_Cultivo
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_CosechaSAP_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Cosecha_SAP')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_CosechaSAP_Grain
    ON Silver.Fact_Cosecha_SAP (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Condicion_Cultivo);
GO

-- =============================================================================
-- 4. Silver.Fact_Evaluacion_Vegetativa
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + ID_Personal + Tipo_Evaluacion
-- =============================================================================
DELETE FROM Silver.Fact_Evaluacion_Vegetativa
WHERE ID_Evaluacion_Veg NOT IN (
    SELECT MIN(ID_Evaluacion_Veg)
    FROM Silver.Fact_Evaluacion_Vegetativa
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Evaluacion
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_EvalVeg_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Evaluacion_Vegetativa')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_EvalVeg_Grain
    ON Silver.Fact_Evaluacion_Vegetativa (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Evaluacion);
GO

-- =============================================================================
-- 5. Silver.Fact_Ciclo_Poda
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + ID_Personal + Tipo_Evaluacion
--    Nota: Tipo_Evaluacion es NULLABLE; filas con NULL se excluyen del indice
--          para evitar conflictos entre multiples NULLs.
-- =============================================================================
DELETE FROM Silver.Fact_Ciclo_Poda
WHERE ID_Poda NOT IN (
    SELECT MIN(ID_Poda)
    FROM Silver.Fact_Ciclo_Poda
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, Tipo_Evaluacion
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_CicloPoda_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclo_Poda')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_CicloPoda_Grain
    ON Silver.Fact_Ciclo_Poda (ID_Geografia, ID_Tiempo, ID_Variedad, Tipo_Evaluacion)
    WHERE Tipo_Evaluacion IS NOT NULL;
GO

-- =============================================================================
-- 6. Silver.Fact_Fisiologia
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + Tercio
-- =============================================================================
DELETE FROM Silver.Fact_Fisiologia
WHERE ID_Fisiologia NOT IN (
    SELECT MIN(ID_Fisiologia)
    FROM Silver.Fact_Fisiologia
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, Tercio
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_Fisiologia_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Fisiologia')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Fisiologia_Grain
    ON Silver.Fact_Fisiologia (ID_Geografia, ID_Tiempo, ID_Variedad, Tercio)
    WHERE Tercio IS NOT NULL;
GO

-- =============================================================================
-- 7. Silver.Fact_Induccion_Floral
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + ID_Personal
--           + Tipo_Evaluacion + Codigo_Consumidor
-- =============================================================================
DELETE FROM Silver.Fact_Induccion_Floral
WHERE ID_Induccion_Floral NOT IN (
    SELECT MIN(ID_Induccion_Floral)
    FROM Silver.Fact_Induccion_Floral
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Evaluacion, Codigo_Consumidor
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_InducFloral_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Induccion_Floral')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_InducFloral_Grain
    ON Silver.Fact_Induccion_Floral (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Tipo_Evaluacion, Codigo_Consumidor);
GO

-- =============================================================================
-- 8. Silver.Fact_Peladas
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad + Punto
-- =============================================================================
DELETE FROM Silver.Fact_Peladas
WHERE ID_Peladas NOT IN (
    SELECT MIN(ID_Peladas)
    FROM Silver.Fact_Peladas
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, Punto
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_Peladas_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Peladas')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Peladas_Grain
    ON Silver.Fact_Peladas (ID_Geografia, ID_Tiempo, ID_Variedad, Punto);
GO

-- =============================================================================
-- 9. Silver.Fact_Sanidad_Activo
--    Grano: ID_Geografia + ID_Tiempo + ID_Variedad
-- =============================================================================
DELETE FROM Silver.Fact_Sanidad_Activo
WHERE ID_Sanidad NOT IN (
    SELECT MIN(ID_Sanidad)
    FROM Silver.Fact_Sanidad_Activo
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_SanidadActivo_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Sanidad_Activo')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_SanidadActivo_Grain
    ON Silver.Fact_Sanidad_Activo (ID_Geografia, ID_Tiempo, ID_Variedad);
GO

-- =============================================================================
-- 10. Silver.Fact_Tareo
--     Grano: ID_Geografia + ID_Tiempo + ID_Personal + ID_Actividad_Operativa
-- =============================================================================
DELETE FROM Silver.Fact_Tareo
WHERE ID_Tareo NOT IN (
    SELECT MIN(ID_Tareo)
    FROM Silver.Fact_Tareo
    GROUP BY ID_Geografia, ID_Tiempo, ID_Personal, ID_Actividad_Operativa
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_Tareo_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Tareo')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Tareo_Grain
    ON Silver.Fact_Tareo (ID_Geografia, ID_Tiempo, ID_Personal, ID_Actividad_Operativa);
GO

-- =============================================================================
-- 11. Silver.Fact_Tasa_Crecimiento_Brotes
--     Grano: ID_Geografia + ID_Tiempo + ID_Variedad + Tipo_Evaluacion
--            + Tipo_Tallo + Codigo_Ensayo + Medida_Crecimiento + Codigo_Origen
-- =============================================================================
DELETE FROM Silver.Fact_Tasa_Crecimiento_Brotes
WHERE ID_Tasa_Crecimiento NOT IN (
    SELECT MIN(ID_Tasa_Crecimiento)
    FROM Silver.Fact_Tasa_Crecimiento_Brotes
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, Tipo_Evaluacion,
             Tipo_Tallo, Codigo_Ensayo, Medida_Crecimiento, Codigo_Origen
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_TCBrotes_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_TCBrotes_Grain
    ON Silver.Fact_Tasa_Crecimiento_Brotes (
        ID_Geografia, ID_Tiempo, ID_Variedad, Tipo_Evaluacion,
        Tipo_Tallo, Codigo_Ensayo, Medida_Crecimiento, Codigo_Origen
    );
GO

-- =============================================================================
-- 12. Silver.Fact_Telemetria_Clima
--     Grano: ID_Tiempo + Sector_Climatico
-- =============================================================================
DELETE FROM Silver.Fact_Telemetria_Clima
WHERE ID_Telemetria_Clima NOT IN (
    SELECT MIN(ID_Telemetria_Clima)
    FROM Silver.Fact_Telemetria_Clima
    GROUP BY ID_Tiempo, Sector_Climatico
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_TelClima_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Telemetria_Clima')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_TelClima_Grain
    ON Silver.Fact_Telemetria_Clima (ID_Tiempo, Sector_Climatico);
GO

-- =============================================================================
-- Fact_Maduracion ya tiene UX_Fact_Maduracion_Origen_Semana_Clave (fase18)
-- No se toca en esta migracion.
-- =============================================================================

PRINT 'fase24: UNIQUE INDEX creados exitosamente en 12 tablas Silver.Fact_*';
GO
