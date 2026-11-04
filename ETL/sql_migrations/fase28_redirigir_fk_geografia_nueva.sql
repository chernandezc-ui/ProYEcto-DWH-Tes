-- =============================================================================
-- FASE 28: Redirigir FKs de ID_Geografia a Silver.Dim_Geografia
--
-- Problema: Algunas Facts tienen FKs auto-generadas (sin nombre explícito)
-- que quedaron rotas después de operaciones de renombrado. SQL Server muestra
-- el error como "conflicted with ... Dim_Geografia_Obsoleta" aunque la tabla
-- real se llama Silver.Dim_Geografia.
--
-- Facts afectadas según el log del pipeline:
--   - Fact_Evaluacion_Pesos   → FK__Fact_Eval__ID_Ge__4C6B5938  (auto-generada)
--   - Fact_Fisiologia         → FK__Fact_Fisi__ID_Ge__6442E2C9  (auto-generada)
--   - Fact_Induccion_Floral   → FK_Fact_Induccion_Floral_Geografia
--   - Fact_Tasa_Crecimiento_Brotes → FK_Fact_TasaCrecimiento_Geografia
--
-- Solución: DROP de cada FK rota + ADD apuntando a Silver.Dim_Geografia.
-- Idempotente: cada bloque comprueba existencia antes de actuar.
-- =============================================================================

-- ── Fact_Evaluacion_Pesos ────────────────────────────────────────────────────
DECLARE @fk NVARCHAR(256);
SELECT @fk = fk.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
WHERE fk.parent_object_id  = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
  AND c.name = 'ID_Geografia'
  AND fk.referenced_object_id <> OBJECT_ID('Silver.Dim_Geografia');
IF @fk IS NOT NULL
    EXEC('ALTER TABLE Silver.Fact_Evaluacion_Pesos DROP CONSTRAINT [' + @fk + ']');
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Fact_EvalPesos_Geo'
      AND parent_object_id = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
)
    ALTER TABLE Silver.Fact_Evaluacion_Pesos
        ADD CONSTRAINT FK_Fact_EvalPesos_Geo
        FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);
GO

-- ── Fact_Fisiologia ──────────────────────────────────────────────────────────
DECLARE @fk NVARCHAR(256);
SELECT @fk = fk.name
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
WHERE fk.parent_object_id  = OBJECT_ID('Silver.Fact_Fisiologia')
  AND c.name = 'ID_Geografia'
  AND fk.referenced_object_id <> OBJECT_ID('Silver.Dim_Geografia');
IF @fk IS NOT NULL
    EXEC('ALTER TABLE Silver.Fact_Fisiologia DROP CONSTRAINT [' + @fk + ']');
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Fact_Fisiologia_Geo'
      AND parent_object_id = OBJECT_ID('Silver.Fact_Fisiologia')
)
    ALTER TABLE Silver.Fact_Fisiologia
        ADD CONSTRAINT FK_Fact_Fisiologia_Geo
        FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);
GO

-- ── Fact_Induccion_Floral ────────────────────────────────────────────────────
DECLARE @fk NVARCHAR(256);
SELECT @fk = fk.name
FROM sys.foreign_keys fk
WHERE fk.parent_object_id    = OBJECT_ID('Silver.Fact_Induccion_Floral')
  AND fk.name                = 'FK_Fact_Induccion_Floral_Geografia'
  AND fk.referenced_object_id <> OBJECT_ID('Silver.Dim_Geografia');
IF @fk IS NOT NULL
    EXEC('ALTER TABLE Silver.Fact_Induccion_Floral DROP CONSTRAINT [FK_Fact_Induccion_Floral_Geografia]');
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Fact_Induccion_Floral_Geografia'
      AND parent_object_id = OBJECT_ID('Silver.Fact_Induccion_Floral')
)
    ALTER TABLE Silver.Fact_Induccion_Floral
        ADD CONSTRAINT FK_Fact_Induccion_Floral_Geografia
        FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);
GO

-- ── Fact_Tasa_Crecimiento_Brotes ─────────────────────────────────────────────
DECLARE @fk NVARCHAR(256);
SELECT @fk = fk.name
FROM sys.foreign_keys fk
WHERE fk.parent_object_id    = OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes')
  AND fk.name                = 'FK_Fact_TasaCrecimiento_Geografia'
  AND fk.referenced_object_id <> OBJECT_ID('Silver.Dim_Geografia');
IF @fk IS NOT NULL
    EXEC('ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes DROP CONSTRAINT [FK_Fact_TasaCrecimiento_Geografia]');
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Fact_TasaCrecimiento_Geografia'
      AND parent_object_id = OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes')
)
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes
        ADD CONSTRAINT FK_Fact_TasaCrecimiento_Geografia
        FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);
GO

-- =============================================================================
-- Verificación post-ejecución:
--
-- SELECT fk.name, OBJECT_NAME(fk.parent_object_id) AS tabla_fact,
--        OBJECT_NAME(fk.referenced_object_id)       AS tabla_dim
-- FROM sys.foreign_keys fk
-- JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
-- JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
-- WHERE c.name = 'ID_Geografia'
-- ORDER BY tabla_fact;
--
-- Todas las filas deben mostrar tabla_dim = 'Dim_Geografia'.
-- =============================================================================
