-- =============================================================================
-- fase67_purgar_columnas_ciclos_fenologicos.sql
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 1. Eliminar columnas innecesarias que no se utilizan
IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'Cantidad') IS NOT NULL
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos DROP COLUMN Cantidad;
GO

IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'Dia') IS NOT NULL
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos DROP COLUMN Dia;
GO

-- 2. Registrar migración aplicada
IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas WHERE Nombre_Fase = 'fase67_purgar_columnas_ciclos_fenologicos'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES ('fase67_purgar_columnas_ciclos_fenologicos', GETDATE(), 
            'Purgar columnas Cantidad y Dia de Fact_Ciclos_Fenologicos');
END;
GO
