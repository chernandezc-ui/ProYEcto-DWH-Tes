-- =============================================================================
-- FASE 27: Columna Fecha_Registro para deduplicación "último timestamp gana"
--          en Silver.Fact_Conteo_Fenologico
--
-- Problema:  489 duplicados reales (7%) son re-mediciones con valores distintos.
--            La política previa (INSERT WHERE NOT EXISTS) conservaba el primero
--            que llegara al batch, de forma no determinista.
-- Solución:  Se propaga la columna "Registro" del Excel (timestamp del evento en
--            campo) a Bronze y Silver para que el MERGE posterior mantenga siempre
--            la medición más reciente.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Bronze: agregar columna Fecha_Registro_Raw
-- -----------------------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Bronce.Conteo_Fruta')
      AND name = 'Fecha_Registro_Raw'
)
    ALTER TABLE Bronce.Conteo_Fruta ADD Fecha_Registro_Raw NVARCHAR(50) NULL;
GO

-- -----------------------------------------------------------------------------
-- 2. Silver: agregar columna Fecha_Registro
-- -----------------------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Silver.Fact_Conteo_Fenologico')
      AND name = 'Fecha_Registro'
)
    ALTER TABLE Silver.Fact_Conteo_Fenologico ADD Fecha_Registro DATETIME2 NULL;
GO

-- -----------------------------------------------------------------------------
-- 3. Backfill Bronze: extraer "Registro" del JSON Valores_Raw para filas ya cargadas
--    Solo actualiza si todavía no tiene valor (reingesta futura completará el resto).
-- -----------------------------------------------------------------------------
UPDATE Bronce.Conteo_Fruta
SET    Fecha_Registro_Raw = TRIM(JSON_VALUE(Valores_Raw, '$.Registro'))
WHERE  Fecha_Registro_Raw IS NULL
  AND  JSON_VALUE(Valores_Raw, '$.Registro') IS NOT NULL;
GO
