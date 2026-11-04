-- =============================================================================
-- fase50_dim_condicion_organico_convencional.sql
-- =============================================================================
-- Objetivo:
--   Simplificar Silver.Dim_Condicion_Cultivo de 5 condiciones (combinaciones de
--   Sustrato x Certificacion: Suelo/GlobalGAP, Suelo/Organico, Sustrato/GlobalGAP,
--   Sustrato/Organico, Suelo/Sin certificacion) a SOLO 2:
--     ID=1 -> 'N/A' / 'Convencional'
--     ID=2 -> 'N/A' / 'Organico'
--
-- Estado al planificar (validado contra BD):
--   - Fact_Cosecha_SAP: 125,486 filas con ID_Condicion_Cultivo = 1 (todas
--     Suelo/GlobalGAP, que mapea a Convencional).
--   - Fact_Tasa_Crecimiento_Brotes, Fact_areas_plantas, Bridge_Modulo_Campana,
--     Bridge_Geografia_Campana_Condicion: TODAS con ID_Condicion IS NULL.
--   - UNIQUE (Sustrato, Certificacion) existe -> el UPDATE in-place debe
--     hacerse en orden seguro.
--
-- Estrategia:
--   UPDATE in-place de IDs 1 y 2 (no se reasignan claves; 125K filas de
--   Fact_Cosecha_SAP siguen apuntando al mismo ID=1, ahora etiquetado
--   Convencional). DELETE de IDs 3, 4, 5 (sin referencias).
--
-- Mapping de negocio (documentado):
--   ID=1 Suelo / GlobalGAP            -> Convencional (GlobalGAP es estandar
--                                        de buenas practicas, NO implica
--                                        organico)
--   ID=2 Suelo / Organico             -> Organico
--   ID=3 Sustrato / GlobalGAP         -> Convencional (consolidado a ID=1)
--   ID=4 Sustrato / Organico          -> Organico     (consolidado a ID=2)
--   ID=5 Suelo / Sin certificacion    -> Convencional (consolidado a ID=1)
--
-- Idempotente: chequea estado actual antes de aplicar.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- -----------------------------------------------------------------------------
-- 0. Diagnostico previo (read-only, sin cambios)
-- -----------------------------------------------------------------------------
PRINT '=== Estado actual de Silver.Dim_Condicion_Cultivo ===';
SELECT ID_Condicion, Sustrato, Certificacion FROM Silver.Dim_Condicion_Cultivo ORDER BY ID_Condicion;

PRINT '=== Referencias actuales por FK ===';
SELECT
    'Fact_Cosecha_SAP'            AS Tabla,
    ID_Condicion_Cultivo          AS ID_Condicion,
    COUNT(*)                      AS n
  FROM Silver.Fact_Cosecha_SAP
 WHERE ID_Condicion_Cultivo IS NOT NULL
 GROUP BY ID_Condicion_Cultivo
UNION ALL
SELECT 'Fact_Tasa_Crecimiento_Brotes', ID_Condicion, COUNT(*)
  FROM Silver.Fact_Tasa_Crecimiento_Brotes
 WHERE ID_Condicion IS NOT NULL GROUP BY ID_Condicion
UNION ALL
SELECT 'Fact_areas_plantas', ID_Condicion, COUNT(*)
  FROM Silver.Fact_areas_plantas
 WHERE ID_Condicion IS NOT NULL GROUP BY ID_Condicion
UNION ALL
SELECT 'Bridge_Modulo_Campana', ID_Condicion, COUNT(*)
  FROM Silver.Bridge_Modulo_Campana
 WHERE ID_Condicion IS NOT NULL GROUP BY ID_Condicion
UNION ALL
SELECT 'Bridge_Geografia_Campana_Condicion', ID_Condicion, COUNT(*)
  FROM Silver.Bridge_Geografia_Campana_Condicion
 WHERE ID_Condicion IS NOT NULL GROUP BY ID_Condicion;
GO

-- -----------------------------------------------------------------------------
-- 1. Verificacion de seguridad: IDs 3,4,5 NO deben tener referencias vivas
-- -----------------------------------------------------------------------------
DECLARE @refs_345 INT = 0;
SELECT @refs_345 = @refs_345 + COUNT(*) FROM Silver.Fact_Cosecha_SAP
 WHERE ID_Condicion_Cultivo IN (3,4,5);
SELECT @refs_345 = @refs_345 + COUNT(*) FROM Silver.Fact_Tasa_Crecimiento_Brotes
 WHERE ID_Condicion IN (3,4,5);
SELECT @refs_345 = @refs_345 + COUNT(*) FROM Silver.Fact_areas_plantas
 WHERE ID_Condicion IN (3,4,5);
SELECT @refs_345 = @refs_345 + COUNT(*) FROM Silver.Bridge_Modulo_Campana
 WHERE ID_Condicion IN (3,4,5);
SELECT @refs_345 = @refs_345 + COUNT(*) FROM Silver.Bridge_Geografia_Campana_Condicion
 WHERE ID_Condicion IN (3,4,5);

IF @refs_345 > 0
BEGIN
    DECLARE @msg NVARCHAR(200) = CONCAT('ABORT fase50: hay ', @refs_345,
        ' fila(s) referenciando IDs 3/4/5. Migrarlas antes de eliminar.');
    RAISERROR(@msg, 16, 1);
    RETURN;
END;

PRINT 'fase50: chequeo de seguridad OK (0 referencias a IDs 3/4/5).';
GO

-- -----------------------------------------------------------------------------
-- 2. UPDATE in-place de IDs 1 y 2 (orden seguro contra UNIQUE)
--    Step A: cambiar Sustrato a 'N/A' en ambas filas (no rompe UNIQUE porque
--            Certificacion sigue siendo distinta entre ID=1 y ID=2).
--    Step B: cambiar Certificacion de ID=1 a 'Convencional'.
-- -----------------------------------------------------------------------------
UPDATE Silver.Dim_Condicion_Cultivo
   SET Sustrato = 'N/A'
 WHERE ID_Condicion IN (1, 2)
   AND Sustrato    <> 'N/A';
PRINT CONCAT('  Step A (Sustrato -> N/A): ', @@ROWCOUNT, ' fila(s).');

UPDATE Silver.Dim_Condicion_Cultivo
   SET Certificacion = 'Convencional'
 WHERE ID_Condicion = 1
   AND Certificacion <> 'Convencional';
PRINT CONCAT('  Step B (ID=1 Certificacion -> Convencional): ', @@ROWCOUNT, ' fila(s).');
GO

-- -----------------------------------------------------------------------------
-- 3. DELETE de IDs 3, 4, 5 (sin referencias confirmadas en paso 1)
-- -----------------------------------------------------------------------------
DELETE FROM Silver.Dim_Condicion_Cultivo
 WHERE ID_Condicion IN (3, 4, 5);
PRINT CONCAT('  DELETE IDs 3/4/5: ', @@ROWCOUNT, ' fila(s).');
GO

-- -----------------------------------------------------------------------------
-- 4. Sanity check final
-- -----------------------------------------------------------------------------
PRINT '=== Estado final de Silver.Dim_Condicion_Cultivo ===';
SELECT ID_Condicion, Sustrato, Certificacion FROM Silver.Dim_Condicion_Cultivo ORDER BY ID_Condicion;

DECLARE @final INT = (SELECT COUNT(*) FROM Silver.Dim_Condicion_Cultivo);
DECLARE @conv  INT = (SELECT COUNT(*) FROM Silver.Dim_Condicion_Cultivo WHERE Certificacion='Convencional');
DECLARE @org   INT = (SELECT COUNT(*) FROM Silver.Dim_Condicion_Cultivo WHERE Certificacion='Organico');

SELECT
    Filas_Finales      = @final,
    Tiene_Convencional = @conv,
    Tiene_Organico     = @org,
    Resultado          = CASE
        WHEN @final = 2 AND @conv = 1 AND @org = 1
            THEN 'OK: Dim_Condicion_Cultivo simplificada a Convencional/Organico'
        ELSE 'FAIL: estado inesperado, revisar'
    END;

-- Verificar que las 125,486 filas de Fact_Cosecha_SAP siguen consistentes
SELECT
    'Fact_Cosecha_SAP post-fase50' AS Etapa,
    f.ID_Condicion_Cultivo,
    dc.Sustrato,
    dc.Certificacion,
    COUNT(*) AS n
  FROM Silver.Fact_Cosecha_SAP f
  LEFT JOIN Silver.Dim_Condicion_Cultivo dc ON dc.ID_Condicion = f.ID_Condicion_Cultivo
 WHERE f.ID_Condicion_Cultivo IS NOT NULL
 GROUP BY f.ID_Condicion_Cultivo, dc.Sustrato, dc.Certificacion;
GO

PRINT 'fase50: Dim_Condicion_Cultivo simplificada a Convencional/Organico.';
GO
