-- =============================================================================
-- fase49b_dim_tiempo_id_campana_fix.sql
-- =============================================================================
-- Fix de fase49:
--   Bug 1: usaba una regla propia (DATEADD(month,-4,...) + ORDER BY Anio DESC)
--          divergente de la del ETL (MDM.fn_Resolver_ID_Campana_Por_Fecha).
--          50% de Dim_Tiempo discrepa con el resolver. Bomba latente en PBI.
--   Bug 2: filtraba `Es_Activa = 1` y boto 1,585 fechas (campanias 2016-2019)
--          al sentinel SIN_CAMPANA.
--
-- Solucion: re-mapeo de Dim_Tiempo.ID_Campana usando UNICAMENTE el resolver
--   SQL de fase48a, que es la misma funcion que usa el ETL Python (vía
--   obtener_id_campana_anual en mdm/lookup.py).
--
-- NO toca: schema (ID_Campana ya existe), populacion de fechas (WHILE de
--          fase49 ya cargo 3,899 filas 2015-01-01 a 2026-06-30).
--
-- Idempotente. Re-ejecutable. Reportable.
-- Pre-requisitos: fase46 + fase48a aplicadas. Verifica en runtime.
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- -----------------------------------------------------------------------------
-- 0. Defensa: el resolver debe existir.
-- -----------------------------------------------------------------------------
IF OBJECT_ID('MDM.fn_Resolver_ID_Campana_Por_Fecha', 'FN') IS NULL
BEGIN
    RAISERROR('MDM.fn_Resolver_ID_Campana_Por_Fecha no existe. Ejecutar fase48a antes.', 16, 1);
    RETURN;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. Diagnostico previo (antes del UPDATE). Imprime resumen.
-- -----------------------------------------------------------------------------
;WITH Diff AS (
    SELECT
        t.ID_Campana                                            AS Actual,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(t.Fecha),0) AS Calculado
      FROM Silver.Dim_Tiempo t
)
SELECT
    'ANTES del fix' AS Etapa,
    SUM(CASE WHEN Actual <> Calculado THEN 1 ELSE 0 END) AS Filas_A_Cambiar,
    SUM(CASE WHEN Actual = 0 AND Calculado <> 0 THEN 1 ELSE 0 END) AS Rescatadas_De_Sentinel,
    SUM(CASE WHEN Actual <> 0 AND Calculado = 0 THEN 1 ELSE 0 END) AS Caen_A_Sentinel,
    COUNT(*) AS Total
  FROM Diff;
GO

-- -----------------------------------------------------------------------------
-- 2. UPDATE: re-mapear ID_Campana usando UNICAMENTE el resolver.
--    NULL del resolver -> 0 (sentinel SIN_CAMPANA, que SI tiene FK valida).
--    Solo actualiza filas que cambian (evita writes innecesarios).
-- -----------------------------------------------------------------------------
UPDATE t
   SET t.ID_Campana = ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(t.Fecha), 0)
  FROM Silver.Dim_Tiempo t
 WHERE t.ID_Campana <> ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(t.Fecha), 0);

DECLARE @upd INT = @@ROWCOUNT;
PRINT CONCAT('fase49b: filas actualizadas = ', @upd);
GO

-- -----------------------------------------------------------------------------
-- 3. Sanity check post-UPDATE: distribucion final.
-- -----------------------------------------------------------------------------
SELECT
    t.ID_Campana,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*) AS n,
    MIN(t.Fecha) AS min_fecha,
    MAX(t.Fecha) AS max_fecha
  FROM Silver.Dim_Tiempo t
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = t.ID_Campana
 GROUP BY t.ID_Campana, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY t.ID_Campana;
GO

-- -----------------------------------------------------------------------------
-- 4. Verificacion: Dim_Tiempo y resolver deben coincidir 100%.
-- -----------------------------------------------------------------------------
;WITH Verif AS (
    SELECT
        t.ID_Campana                                            AS Actual,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(t.Fecha),0) AS Calculado
      FROM Silver.Dim_Tiempo t
)
SELECT
    'VERIFICACION post-fix' AS Etapa,
    SUM(CASE WHEN Actual <> Calculado THEN 1 ELSE 0 END) AS Discrepancias_Restantes,
    CASE WHEN SUM(CASE WHEN Actual <> Calculado THEN 1 ELSE 0 END) = 0
         THEN 'OK: Dim_Tiempo y resolver alineados al 100%'
         ELSE 'FAIL: aun hay discrepancias' END AS Resultado
  FROM Verif;
GO

PRINT 'fase49b: fix de Dim_Tiempo.ID_Campana aplicado.';
GO
