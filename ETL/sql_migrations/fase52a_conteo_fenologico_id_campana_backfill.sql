-- =============================================================================
-- fase52a_conteo_fenologico_id_campana_backfill.sql
-- =============================================================================
-- Objetivo:
--   Llevar Silver.Fact_Conteo_Fenologico al ecosistema Geografia-Campana.
--   La columna ID_Campana ya existe (DDL v3) pero esta NULL para todas las
--   filas existentes porque el loader Python no la pueblan.
--
-- Acciones:
--   1. Auditoria pre-backfill (cuantas filas hay, cuantas con NULL).
--   2. Backfill: poblar ID_Campana usando MDM.fn_Resolver_ID_Campana_Por_Fecha
--      (la misma funcion que usa el ETL + Dim_Tiempo + bridges).
--   3. Auditoria post (cobertura, distribucion por campana).
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
GO

-- -----------------------------------------------------------------------------
-- 1. Auditoria pre-backfill
-- -----------------------------------------------------------------------------
PRINT '=== 1. Estado pre-backfill de Silver.Fact_Conteo_Fenologico ===';
SELECT
    Filas_Total            = COUNT(*),
    Con_ID_Campana         = SUM(CASE WHEN ID_Campana IS NOT NULL THEN 1 ELSE 0 END),
    Sin_ID_Campana_NULL    = SUM(CASE WHEN ID_Campana IS NULL THEN 1 ELSE 0 END),
    Geografias_Unicas      = COUNT(DISTINCT ID_Geografia),
    Variedades_Unicas      = COUNT(DISTINCT ID_Variedad),
    Estados_Unicos         = COUNT(DISTINCT ID_Estado_Fenologico),
    Min_Fecha              = MIN(Fecha_Evento),
    Max_Fecha              = MAX(Fecha_Evento)
  FROM Silver.Fact_Conteo_Fenologico;
GO

PRINT '=== 2. Que campanas se resolverian (preview, sin escribir aun) ===';
;WITH F AS (
    SELECT
        f.ID_Conteo_Fenologico,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0) AS ID_Campana_Calc,
        f.Fecha_Evento
      FROM Silver.Fact_Conteo_Fenologico f
     WHERE f.Estado_DQ = 'OK'
)
SELECT
    F.ID_Campana_Calc,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*) AS Filas,
    MIN(F.Fecha_Evento) AS Min_Fecha,
    MAX(F.Fecha_Evento) AS Max_Fecha
  FROM F
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = F.ID_Campana_Calc
 GROUP BY F.ID_Campana_Calc, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY F.ID_Campana_Calc;
GO

-- -----------------------------------------------------------------------------
-- 3. Backfill (idempotente: solo actualiza filas donde el valor calculado
--    difiere del actual; NULL -> ID se cuenta como cambio).
-- -----------------------------------------------------------------------------
UPDATE f
   SET f.ID_Campana = ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0)
  FROM Silver.Fact_Conteo_Fenologico f
 WHERE ISNULL(f.ID_Campana, -1)
     <> ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0);

DECLARE @upd INT = @@ROWCOUNT;
PRINT CONCAT('fase52a: filas actualizadas = ', @upd);
GO

-- -----------------------------------------------------------------------------
-- 4. Auditoria post-backfill
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
  FROM Silver.Fact_Conteo_Fenologico f
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = f.ID_Campana
 GROUP BY f.ID_Campana, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY f.ID_Campana;
GO

PRINT '=== 5. Verificacion: ningun fila con ID_Campana NULL debe quedar ===';
SELECT
    NULLs_Restantes = SUM(CASE WHEN ID_Campana IS NULL THEN 1 ELSE 0 END),
    Sentinel_0      = SUM(CASE WHEN ID_Campana = 0 THEN 1 ELSE 0 END),
    Total           = COUNT(*),
    Resultado       = CASE
        WHEN SUM(CASE WHEN ID_Campana IS NULL THEN 1 ELSE 0 END) = 0
            THEN 'OK: backfill completo'
        ELSE 'FAIL: aun hay NULLs'
    END
  FROM Silver.Fact_Conteo_Fenologico;
GO

PRINT 'fase52a: backfill ID_Campana en Fact_Conteo_Fenologico completado.';
GO
