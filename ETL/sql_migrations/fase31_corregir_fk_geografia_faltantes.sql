-- =============================================================================
-- FASE 31: Redirigir FKs de ID_Geografia faltantes a Silver.Dim_Geografia
--
-- Problema: Fact_Peladas y Fact_Conteo_Fenologico fueron omitidas en la 
-- Fase 28. Sus FKs seguian apuntando al objeto "Obsoleta".
--
-- NOTA: Fact_Telemetria_Clima NO requiere esta correccion porque desde la 
-- Fase 19 no utiliza ID_Geografia (usa Sector_Climatico).
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

-- ── Fact_Peladas ─────────────────────────────────────────────────────────────
DECLARE @fk NVARCHAR(256);
SELECT @fk = fk.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
WHERE fk.parent_object_id  = OBJECT_ID('Silver.Fact_Peladas')
  AND c.name = 'ID_Geografia'
  AND fk.referenced_object_id <> OBJECT_ID('Silver.Dim_Geografia');

IF @fk IS NOT NULL
BEGIN
    PRINT 'Corrigiendo FK en Fact_Peladas: ' + @fk;
    EXEC('ALTER TABLE Silver.Fact_Peladas DROP CONSTRAINT [' + @fk + ']');
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys 
    WHERE name = 'FK_Fact_Peladas_Geo' 
      AND parent_object_id = OBJECT_ID('Silver.Fact_Peladas')
)
    ALTER TABLE Silver.Fact_Peladas 
        ADD CONSTRAINT FK_Fact_Peladas_Geo 
        FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);
GO

-- ── Fact_Conteo_Fenologico ───────────────────────────────────────────────────
DECLARE @fk NVARCHAR(256);
SELECT @fk = fk.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
WHERE fk.parent_object_id  = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
  AND c.name = 'ID_Geografia'
  AND fk.referenced_object_id <> OBJECT_ID('Silver.Dim_Geografia');

IF @fk IS NOT NULL
BEGIN
    PRINT 'Corrigiendo FK en Fact_Conteo_Fenologico: ' + @fk;
    EXEC('ALTER TABLE Silver.Fact_Conteo_Fenologico DROP CONSTRAINT [' + @fk + ']');
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys 
    WHERE name = 'FK_Fact_ConteoFen_Geo' 
      AND parent_object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
)
    ALTER TABLE Silver.Fact_Conteo_Fenologico 
        ADD CONSTRAINT FK_Fact_ConteoFen_Geo 
        FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);
GO

PRINT 'Migracion Fase 31 completada: FKs de Geografia redirigidas.';
GO
