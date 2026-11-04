-- =============================================================================
-- fase56a_evaluacion_pesos_id_campana_backfill.sql
-- =============================================================================
-- Objetivo:
--   Llevar Silver.Fact_Evaluacion_Pesos al ecosistema Geografia-Campana.
--   La columna ID_Campana ya existe pero esta NULL para filas historicas
--   porque el loader Python aun no la puebla (Task #15 pendiente).
--
-- Acciones:
--   1. Auditoria pre-backfill.
--   2. Preview de campanas que se resolverian.
--   3. Backfill: poblar ID_Campana usando MDM.fn_Resolver_ID_Campana_Por_Fecha.
--   4. Auditoria post-backfill.
--   5. Verificacion de NULLs restantes.
--
-- Idempotente: solo actualiza filas donde ID_Campana cambia.
-- Pre-requisito: fase48a (resolver) aplicado.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- 0. Defensa: el resolver debe existir.
IF OBJECT_ID('MDM.fn_Resolver_ID_Campana_Por_Fecha', 'FN') IS NULL
BEGIN
    RAISERROR('MDM.fn_Resolver_ID_Campana_Por_Fecha no existe. Ejecutar fase48a antes.', 16, 1);
    RETURN;
END;
IF OBJECT_ID('Silver.Fact_Evaluacion_Pesos', 'U') IS NULL
BEGIN
    RAISERROR('Silver.Fact_Evaluacion_Pesos no existe.', 16, 1);
    RETURN;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. Auditoria pre-backfill
-- -----------------------------------------------------------------------------
PRINT '=== 1. Estado pre-backfill de Silver.Fact_Evaluacion_Pesos ===';
SELECT
    Filas_Total            = COUNT(*),
    Con_ID_Campana         = SUM(CASE WHEN ID_Campana IS NOT NULL THEN 1 ELSE 0 END),
    Sin_ID_Campana_NULL    = SUM(CASE WHEN ID_Campana IS NULL THEN 1 ELSE 0 END),
    Geografias_Unicas      = COUNT(DISTINCT ID_Geografia),
    Variedades_Unicas      = COUNT(DISTINCT ID_Variedad),
    Min_Fecha              = MIN(Fecha_Evento),
    Max_Fecha              = MAX(Fecha_Evento)
  FROM Silver.Fact_Evaluacion_Pesos;
GO

-- -----------------------------------------------------------------------------
-- 2. Preview de campanas a resolver (sin escribir aun)
-- -----------------------------------------------------------------------------
PRINT '=== 2. Campanas que se resolverian (preview) ===';
;WITH F AS (
    SELECT
        f.ID_Evaluacion_Pesos,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0) AS ID_Campana_Calc,
        f.Fecha_Evento
      FROM Silver.Fact_Evaluacion_Pesos f
     WHERE f.Estado_DQ = 'OK'
)
SELECT
    F.ID_Campana_Calc,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*)           AS Filas,
    MIN(F.Fecha_Evento) AS Min_Fecha,
    MAX(F.Fecha_Evento) AS Max_Fecha
  FROM F
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = F.ID_Campana_Calc
 GROUP BY F.ID_Campana_Calc, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY F.ID_Campana_Calc;
GO

-- -----------------------------------------------------------------------------
-- 3. Backfill (idempotente)
-- -----------------------------------------------------------------------------
PRINT '=== 3. Ejecutando backfill ID_Campana ===';
UPDATE f
   SET f.ID_Campana = ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0)
  FROM Silver.Fact_Evaluacion_Pesos f
 WHERE ISNULL(f.ID_Campana, -1)
     <> ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0);

DECLARE @upd INT = @@ROWCOUNT;
PRINT CONCAT('fase56a: filas actualizadas = ', @upd);
GO

-- -----------------------------------------------------------------------------
-- 4. Distribucion final por campana
-- -----------------------------------------------------------------------------
PRINT '=== 4. Distribucion final por campana ===';
SELECT
    f.ID_Campana,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*)                       AS Filas,
    COUNT(DISTINCT f.ID_Geografia) AS Geografias_Unicas,
    MIN(f.Fecha_Evento)            AS Min_Fecha,
    MAX(f.Fecha_Evento)            AS Max_Fecha
  FROM Silver.Fact_Evaluacion_Pesos f
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = f.ID_Campana
 GROUP BY f.ID_Campana, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY f.ID_Campana;
GO

-- -----------------------------------------------------------------------------
-- 5. Verificacion: ningun fila con ID_Campana NULL debe quedar
-- -----------------------------------------------------------------------------
PRINT '=== 5. Verificacion de cobertura ===';
SELECT
    NULLs_Restantes = SUM(CASE WHEN ID_Campana IS NULL THEN 1 ELSE 0 END),
    Sentinel_0      = SUM(CASE WHEN ID_Campana = 0    THEN 1 ELSE 0 END),
    Total           = COUNT(*),
    Resultado       = CASE
        WHEN SUM(CASE WHEN ID_Campana IS NULL THEN 1 ELSE 0 END) = 0
            THEN 'OK: backfill completo'
        ELSE 'FAIL: aun hay NULLs'
    END
  FROM Silver.Fact_Evaluacion_Pesos;
GO

PRINT 'fase56a: backfill ID_Campana en Fact_Evaluacion_Pesos completado.';
GO
