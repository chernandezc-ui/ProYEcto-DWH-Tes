-- =============================================================================
-- fase65_fact_ciclos_fenologicos_color_cinta.sql
-- =============================================================================
-- Objetivo:
--   Agregar las columnas Color_Cinta y Organo a Silver.Fact_Ciclos_Fenologicos.
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'Color_Cinta') IS NULL
BEGIN
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos ADD Color_Cinta NVARCHAR(50) NULL;
    PRINT 'OK: Agregada columna Color_Cinta a Silver.Fact_Ciclos_Fenologicos';
END
ELSE
    PRINT 'SKIP: Color_Cinta ya existe.';
GO

IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'Organo') IS NULL
BEGIN
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos ADD Organo NVARCHAR(50) NULL;
    PRINT 'OK: Agregada columna Organo a Silver.Fact_Ciclos_Fenologicos';
END
ELSE
    PRINT 'SKIP: Organo ya existe.';
GO

IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas WHERE Nombre_Fase = 'fase65_fact_ciclos_fenologicos_color_cinta'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES ('fase65_fact_ciclos_fenologicos_color_cinta', GETDATE(), 
            'Agregar columnas Color_Cinta y Organo a Fact_Ciclos_Fenologicos');
    PRINT 'Migración registrada en Silver.Migraciones_Aplicadas.';
END;
GO
