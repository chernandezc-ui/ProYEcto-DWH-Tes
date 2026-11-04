-- =============================================================================
-- fase48a_resolver_campana_por_fecha.sql
-- =============================================================================
-- Objetivo:
--   1. Crear MDM.fn_Resolver_ID_Campana_Por_Fecha(@fecha DATE) -> ID_Campana.
--      Regla: la campana vigente para una fecha de evaluacion es aquella cuyo
--      anchor (Fecha_Inicio_Poda si existe, sino Fecha_Inicio_Campana) sea el
--      MAS RECIENTE menor o igual a la fecha del evento.
--      Esto desambigua el solape entre campanias consecutivas.
--   2. Backfill correctivo de Silver.Fact_Evaluacion_Vegetativa:
--      hoy todas las 96,360 filas tienen ID_Campana=3 (incorrecto).
--      Recalcular ID_Campana en base a Fecha_Evento.
--
-- Reversible: el backfill se ejecuta SOLO si la fact tiene >50% concentrada
-- en una sola campana (heuristica de "esta mal poblado"). Idempotente.
--
-- Pre-requisito: fase46 ejecutada (Dim_Campana con fechas).
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- -----------------------------------------------------------------------------
-- 1. Funcion resolver por fecha
-- -----------------------------------------------------------------------------
CREATE OR ALTER FUNCTION MDM.fn_Resolver_ID_Campana_Por_Fecha (@Fecha DATE)
RETURNS INT
WITH SCHEMABINDING
AS
BEGIN
    IF @Fecha IS NULL RETURN NULL;

    -- Anchor = Fecha_Inicio_Poda si existe, sino Fecha_Inicio_Campana.
    -- Tomamos la campana cuyo anchor sea el MAS RECIENTE <= @Fecha.
    DECLARE @id INT;
    SELECT TOP 1 @id = ID_Campana
      FROM Silver.Dim_Campana
     WHERE Anio_Cosecha > 1900  -- excluye sentinel SIN_CAMPANA
       AND COALESCE(Fecha_Inicio_Poda, Fecha_Inicio_Campana) IS NOT NULL
       AND COALESCE(Fecha_Inicio_Poda, Fecha_Inicio_Campana) <= @Fecha
       -- y la fecha no esta despues del cierre (si esta cerrada)
       AND (Fecha_Fin_Campana IS NULL OR @Fecha <= DATEADD(MONTH, 3, Fecha_Fin_Campana))
     ORDER BY COALESCE(Fecha_Inicio_Poda, Fecha_Inicio_Campana) DESC;

    RETURN @id;
END;
GO

-- -----------------------------------------------------------------------------
-- 2. Tests unitarios (PRINT). No bloquean el deploy si fallan.
-- -----------------------------------------------------------------------------
DECLARE @t1 INT = MDM.fn_Resolver_ID_Campana_Por_Fecha('2024-06-15');  -- esperado: Anio=2024
DECLARE @t2 INT = MDM.fn_Resolver_ID_Campana_Por_Fecha('2025-03-15');  -- esperado: Anio=2024 (eval cierra 2025-01) o 2025 (poda 2024-12)
DECLARE @t3 INT = MDM.fn_Resolver_ID_Campana_Por_Fecha('2026-02-15');  -- esperado: Anio=2026 (poda 2025-11)
DECLARE @t4 INT = MDM.fn_Resolver_ID_Campana_Por_Fecha('2020-08-15');  -- esperado: Anio=2020 (camp 2020 inicia 2020-06-11)
DECLARE @t5 INT = MDM.fn_Resolver_ID_Campana_Por_Fecha('2015-01-01');  -- esperado: NULL (antes de cualquier campana)
DECLARE @t6 INT = MDM.fn_Resolver_ID_Campana_Por_Fecha(NULL);          -- esperado: NULL

SELECT
    Test1_2024_06_15 = CONCAT('ID=', ISNULL(CAST(@t1 AS VARCHAR(10)),'NULL'),
                              ' Anio=', ISNULL((SELECT Anio_Cosecha FROM Silver.Dim_Campana WHERE ID_Campana=@t1),0)),
    Test2_2025_03_15 = CONCAT('ID=', ISNULL(CAST(@t2 AS VARCHAR(10)),'NULL'),
                              ' Anio=', ISNULL((SELECT Anio_Cosecha FROM Silver.Dim_Campana WHERE ID_Campana=@t2),0)),
    Test3_2026_02_15 = CONCAT('ID=', ISNULL(CAST(@t3 AS VARCHAR(10)),'NULL'),
                              ' Anio=', ISNULL((SELECT Anio_Cosecha FROM Silver.Dim_Campana WHERE ID_Campana=@t3),0)),
    Test4_2020_08_15 = CONCAT('ID=', ISNULL(CAST(@t4 AS VARCHAR(10)),'NULL'),
                              ' Anio=', ISNULL((SELECT Anio_Cosecha FROM Silver.Dim_Campana WHERE ID_Campana=@t4),0)),
    Test5_2015_01_01 = ISNULL(CAST(@t5 AS VARCHAR(10)), 'NULL (esperado)'),
    Test6_NULL       = ISNULL(CAST(@t6 AS VARCHAR(10)), 'NULL (esperado)');
GO

-- -----------------------------------------------------------------------------
-- 3. Dry-run del backfill: muestra cuantas filas cambiarian POR campana,
--    sin tocar la fact. Revisa el output antes de aprobar el UPDATE.
-- -----------------------------------------------------------------------------
;WITH Proyeccion AS (
    SELECT
        f.ID_Campana                                                       AS ID_Camp_Actual,
        MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)) AS ID_Camp_Calc
      FROM Silver.Fact_Evaluacion_Vegetativa f
)
SELECT
    'DRY RUN backfill Fact_Evaluacion_Vegetativa' AS Etapa,
    SUM(CASE WHEN ISNULL(ID_Camp_Actual,-1) <> ISNULL(ID_Camp_Calc,-1) THEN 1 ELSE 0 END) AS Filas_Cambiarian,
    SUM(CASE WHEN ID_Camp_Calc IS NULL THEN 1 ELSE 0 END) AS Filas_Quedarian_NULL,
    COUNT(*) AS Total_Filas
  FROM Proyeccion;

;WITH Proyeccion AS (
    SELECT
        MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)) AS ID_Camp_Calc
      FROM Silver.Fact_Evaluacion_Vegetativa f
)
SELECT
    p.ID_Camp_Calc,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*) AS Filas_Tras_Backfill
  FROM Proyeccion p
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = p.ID_Camp_Calc
 GROUP BY p.ID_Camp_Calc, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY dc.Anio_Cosecha;
GO

PRINT 'fase48a: funcion creada + dry-run impreso. NO se modifico la fact.';
PRINT 'Si la distribucion proyectada se ve correcta, ejecutar fase48b para aplicar UPDATE.';
GO
