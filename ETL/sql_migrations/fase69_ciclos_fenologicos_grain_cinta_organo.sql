-- =============================================================================
-- fase69_ciclos_fenologicos_grain_cinta_organo.sql
-- =============================================================================
-- Objetivo:
--   Actualizar el grain de Silver.Fact_Ciclos_Fenologicos para incluir ID_Cinta y Organo,
--   evitando pérdidas silenciosas de información al colapsar mediciones con el mismo
--   modulo/fecha/variedad/estado pero con distinta cinta (color) y organo (conteo).
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 1. Eliminar duplicados si los hubiera (conservando el menor ID_Ciclo_Fenologico_Silver)
DELETE FROM Silver.Fact_Ciclos_Fenologicos
WHERE ID_Ciclo_Fenologico_Silver NOT IN (
    SELECT MIN(ID_Ciclo_Fenologico_Silver)
    FROM Silver.Fact_Ciclos_Fenologicos
    GROUP BY ID_Geografia, ID_Tiempo, ID_Variedad, Cama, Tipo_Evaluacion, ID_Estado_Fenologico, ID_Cinta, Organo
);
GO

-- 2. Eliminar el índice único anterior (si existe)
IF EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'UX_Fact_Ciclos_Fenologicos_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclos_Fenologicos')
)
BEGIN
    DROP INDEX UX_Fact_Ciclos_Fenologicos_Grain ON Silver.Fact_Ciclos_Fenologicos;
    PRINT 'OK: Drop de index anterior UX_Fact_Ciclos_Fenologicos_Grain';
END
GO

-- 3. Crear el nuevo índice único incluyendo ID_Cinta y Organo
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = 'UX_Fact_Ciclos_Fenologicos_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclos_Fenologicos')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_Ciclos_Fenologicos_Grain
    ON Silver.Fact_Ciclos_Fenologicos
        (ID_Geografia, ID_Tiempo, ID_Variedad, Cama, Tipo_Evaluacion, ID_Estado_Fenologico, ID_Cinta, Organo)
    WHERE ID_Estado_Fenologico IS NOT NULL;
    PRINT 'OK: Creado nuevo index UX_Fact_Ciclos_Fenologicos_Grain con ID_Cinta y Organo';
END
GO

-- 4. Registrar en la tabla de migraciones de Silver (por consistencia con fase65 y fase66)
IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas WHERE Nombre_Fase = 'fase69_ciclos_fenologicos_grain_cinta_organo'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES ('fase69_ciclos_fenologicos_grain_cinta_organo', GETDATE(), 
            'Incluir ID_Cinta y Organo en el grain index de Fact_Ciclos_Fenologicos');
END;
GO
