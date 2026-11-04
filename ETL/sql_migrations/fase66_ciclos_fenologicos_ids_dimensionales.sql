-- =============================================================================
-- fase66_ciclos_fenologicos_ids_dimensionales.sql
-- =============================================================================
-- Migra Silver.Fact_Ciclos_Fenologicos:
--   * Categoria      NVARCHAR  →  ID_Estado_Fenologico INT (FK Dim_Estado_Fenologico)
--   * Color_Cinta    NVARCHAR  →  ID_Cinta             INT (FK Dim_Cinta)
-- Estrategia: ADD columnas ID, poblar desde Dim con match best-effort,
-- luego DROP columnas texto. El grain no cambia, solo el tipo de la clave.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 1. Agregar columnas ID (si no existen)
IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'ID_Estado_Fenologico') IS NULL
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos ADD ID_Estado_Fenologico INT NULL;
GO

IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'ID_Cinta') IS NULL
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos ADD ID_Cinta INT NULL;
GO

-- 2. Poblar ID_Estado_Fenologico desde Categoria (match directo + aliases comunes)
UPDATE f
SET f.ID_Estado_Fenologico = ef.ID_Estado_Fenologico
FROM Silver.Fact_Ciclos_Fenologicos f
JOIN Silver.Dim_Estado_Fenologico ef
    ON LOWER(TRIM(ef.Nombre_Estado)) = LOWER(TRIM(f.Categoria))
WHERE f.ID_Estado_Fenologico IS NULL AND f.Categoria IS NOT NULL;
GO

-- 2b. Aliases de Categoria que no coinciden con el Nombre_Estado exacto
UPDATE f
SET f.ID_Estado_Fenologico = alias_map.ID_Estado_Fenologico
FROM Silver.Fact_Ciclos_Fenologicos f
JOIN (VALUES
    -- Categoria texto → Nombre_Estado en Dim
    ('ffase1',         5),  -- Inicio F1
    ('ffase2',         6),  -- Inicio F2
    ('inicio fase 1',  5),
    ('inicio fase 2',  6),
    ('cosecha',        9),  -- Cosechable
    ('floracion',      2),  -- Flor
    ('floración',      2),
    ('pequena',        3),
    ('pequeña',        3),
    ('punta verde',    4),  -- Verde
    ('produccion',     NULL),
    ('producción',     NULL),
    ('induccion floral', NULL),
    ('inducción floral', NULL),
    ('poda',           NULL),
    ('siembra',        NULL),
    ('vegetativo',     NULL),
    ('eliminacion',    NULL),
    ('eliminación',    NULL)
) AS alias_map(Alias, ID_Estado_Fenologico)
    ON LOWER(TRIM(f.Categoria)) = alias_map.Alias
WHERE f.ID_Estado_Fenologico IS NULL
  AND alias_map.ID_Estado_Fenologico IS NOT NULL
  AND f.Categoria IS NOT NULL;
GO

-- 3. Poblar ID_Cinta desde Color_Cinta (match directo + aliases de género)
UPDATE f
SET f.ID_Cinta = c.ID_Cinta
FROM Silver.Fact_Ciclos_Fenologicos f
JOIN Silver.Dim_Cinta c
    ON LOWER(TRIM(c.Color_Cinta)) = LOWER(TRIM(f.Color_Cinta))
WHERE f.ID_Cinta IS NULL AND f.Color_Cinta IS NOT NULL;
GO

-- 3b. Aliases de género (Rojo→Roja, Amarillo→Amarilla, Blanco→Blanca)
UPDATE f
SET f.ID_Cinta = c.ID_Cinta
FROM Silver.Fact_Ciclos_Fenologicos f
JOIN Silver.Dim_Cinta c
    ON c.Color_Cinta = CASE LOWER(TRIM(f.Color_Cinta))
        WHEN 'rojo'     THEN 'Roja'
        WHEN 'amarillo' THEN 'Amarilla'
        WHEN 'blanco'   THEN 'Blanca'
        ELSE NULL
    END
WHERE f.ID_Cinta IS NULL AND f.Color_Cinta IS NOT NULL;
GO

-- 4. Eliminar columnas texto originales
IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'Categoria') IS NOT NULL
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos DROP COLUMN Categoria;
GO

IF COL_LENGTH('Silver.Fact_Ciclos_Fenologicos', 'Color_Cinta') IS NOT NULL
    ALTER TABLE Silver.Fact_Ciclos_Fenologicos DROP COLUMN Color_Cinta;
GO

-- 5. Registrar migración
IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas
        WHERE Nombre_Fase = 'fase66_ciclos_fenologicos_ids_dimensionales'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES (
        'fase66_ciclos_fenologicos_ids_dimensionales',
        GETDATE(),
        'Migrar Categoria→ID_Estado_Fenologico y Color_Cinta→ID_Cinta en Fact_Ciclos_Fenologicos'
    );
END;
GO

PRINT '✓ fase66: Categoria e Color_Cinta migradas a IDs dimensionales en Silver.Fact_Ciclos_Fenologicos';
GO
