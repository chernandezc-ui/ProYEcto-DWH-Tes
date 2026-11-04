-- =============================================================================
-- fase56b_poblar_bridge_geo_campana_evaluacion_pesos.sql
-- =============================================================================
-- Pobla Silver.Bridge_Geografia_Campana desde Silver.Fact_Evaluacion_Pesos
-- usando el resolver oficial. Reutiliza la MISMA tabla bridge global
-- (sin condicion): Vegetativa + Conteo_Fenologico + Evaluacion_Pesos + ...
--
-- Pre-requisitos:
--   - fase48a (resolver) aplicado.
--   - fase48b (tabla Bridge_Geografia_Campana) aplicado.
--   - fase56a (backfill ID_Campana en el fact) aplicado.
--
-- Idempotente via MERGE sobre Hash_Llave = SHA2_256(Geo|Camp).
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID('MDM.fn_Resolver_ID_Campana_Por_Fecha', 'FN') IS NULL
BEGIN
    RAISERROR('MDM.fn_Resolver_ID_Campana_Por_Fecha no existe. Ejecutar fase48a antes.', 16, 1);
    RETURN;
END;
IF OBJECT_ID('Silver.Bridge_Geografia_Campana', 'U') IS NULL
BEGIN
    RAISERROR('Silver.Bridge_Geografia_Campana no existe. Ejecutar fase48b antes.', 16, 1);
    RETURN;
END;
IF OBJECT_ID('Silver.Fact_Evaluacion_Pesos', 'U') IS NULL
BEGIN
    RAISERROR('Silver.Fact_Evaluacion_Pesos no existe.', 16, 1);
    RETURN;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. SP populador (idempotente)
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geografia_Campana_Evaluacion_Pesos
AS
BEGIN
    SET NOCOUNT ON;

    IF OBJECT_ID('tempdb..#Combinaciones_EvalPesos') IS NOT NULL DROP TABLE #Combinaciones_EvalPesos;

    SELECT
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0) AS ID_Campana,
        MIN(CAST(f.Fecha_Evento AS DATE))                                              AS Vigencia_Inicio,
        MAX(CAST(f.Fecha_Evento AS DATE))                                              AS Vigencia_Fin,
        COUNT(*)                                                                       AS Filas_Fact
    INTO #Combinaciones_EvalPesos
      FROM Silver.Fact_Evaluacion_Pesos f
     WHERE f.Estado_DQ = 'OK'
       AND f.ID_Geografia IS NOT NULL
       AND f.Fecha_Evento IS NOT NULL
     GROUP BY
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0);

    -- Cuarentena FK
    IF OBJECT_ID('tempdb..#Cuarentena_FK_EvalPesos') IS NOT NULL DROP TABLE #Cuarentena_FK_EvalPesos;
    SELECT
        c.ID_Geografia,
        c.ID_Campana,
        c.Filas_Fact,
        Motivo = CASE
            WHEN g.ID_Geografia IS NULL  THEN 'GEO_INVALIDA'
            WHEN dc.ID_Campana IS NULL   THEN 'CAMPANA_INVALIDA'
        END
    INTO #Cuarentena_FK_EvalPesos
      FROM #Combinaciones_EvalPesos c
      LEFT JOIN Silver.Dim_Geografia g  ON g.ID_Geografia = c.ID_Geografia
      LEFT JOIN Silver.Dim_Campana   dc ON dc.ID_Campana  = c.ID_Campana
     WHERE g.ID_Geografia IS NULL OR dc.ID_Campana IS NULL;

    DECLARE @cuar INT = (SELECT COUNT(*) FROM #Cuarentena_FK_EvalPesos);
    IF @cuar > 0
    BEGIN
        PRINT CONCAT('Cuarentena FK invalida: ', @cuar, ' combinaciones (ver #Cuarentena_FK_EvalPesos).');
        SELECT TOP 20 * FROM #Cuarentena_FK_EvalPesos ORDER BY Filas_Fact DESC;
    END;

    -- MERGE con hash determinista
    MERGE Silver.Bridge_Geografia_Campana AS dst
    USING (
        SELECT
            c.ID_Geografia,
            c.ID_Campana,
            c.Vigencia_Inicio,
            c.Vigencia_Fin,
            HASHBYTES('SHA2_256',
                CONCAT(CAST(c.ID_Geografia AS NVARCHAR(20)), '|',
                       CAST(c.ID_Campana   AS NVARCHAR(20)))
            ) AS Hash_Llave
          FROM #Combinaciones_EvalPesos c
         INNER JOIN Silver.Dim_Geografia g  ON g.ID_Geografia = c.ID_Geografia
         INNER JOIN Silver.Dim_Campana   dc ON dc.ID_Campana  = c.ID_Campana
    ) AS src
        ON dst.Hash_Llave = src.Hash_Llave
    WHEN MATCHED AND (
            dst.Vigencia_Inicio > src.Vigencia_Inicio
         OR ISNULL(dst.Vigencia_Fin, '1900-01-01') < ISNULL(src.Vigencia_Fin, '9999-12-31')
        ) THEN UPDATE SET
            Vigencia_Inicio = CASE WHEN dst.Vigencia_Inicio > src.Vigencia_Inicio THEN src.Vigencia_Inicio ELSE dst.Vigencia_Inicio END,
            Vigencia_Fin    = CASE
                WHEN ISNULL(dst.Vigencia_Fin, '1900-01-01') < ISNULL(src.Vigencia_Fin, '9999-12-31')
                THEN src.Vigencia_Fin
                ELSE dst.Vigencia_Fin
            END,
            Es_Activa       = 1
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (ID_Geografia, ID_Campana, Vigencia_Inicio, Vigencia_Fin, Es_Activa, Hash_Llave)
        VALUES (src.ID_Geografia, src.ID_Campana, src.Vigencia_Inicio, src.Vigencia_Fin, 1, src.Hash_Llave);

    DECLARE @total_bridge INT = (SELECT COUNT(*) FROM Silver.Bridge_Geografia_Campana);
    PRINT CONCAT('Bridge_GC (Evaluacion_Pesos): total filas bridge = ',
                 @total_bridge, ', cuarentena FK = ', @cuar);
END;
GO

-- -----------------------------------------------------------------------------
-- 2. Ejecutar el SP
-- -----------------------------------------------------------------------------
EXEC MDM.usp_Popular_Bridge_Geografia_Campana_Evaluacion_Pesos;
GO

-- -----------------------------------------------------------------------------
-- 3. Auditoria post-poblamiento
-- -----------------------------------------------------------------------------
PRINT '=== A. Total bridge GLOBAL ===';
SELECT
    Filas_Bridge       = COUNT(*),
    Geografias_Unicas  = COUNT(DISTINCT ID_Geografia),
    Campanas_Distintas = COUNT(DISTINCT ID_Campana)
  FROM Silver.Bridge_Geografia_Campana;

PRINT '=== B. Distribucion por campana en el bridge ===';
SELECT
    b.ID_Campana,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*) AS Entradas_Bridge,
    COUNT(DISTINCT b.ID_Geografia) AS Geografias_Unicas
  FROM Silver.Bridge_Geografia_Campana b
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = b.ID_Campana
 GROUP BY b.ID_Campana, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY b.ID_Campana;

PRINT '=== C. Cobertura de Fact_Evaluacion_Pesos ===';
;WITH F AS (
    SELECT DISTINCT
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(CAST(f.Fecha_Evento AS DATE)), 0) AS ID_Campana
      FROM Silver.Fact_Evaluacion_Pesos f
     WHERE f.Estado_DQ = 'OK'
       AND f.ID_Geografia IS NOT NULL
)
SELECT
    Pares_En_Fact    = COUNT(*),
    Pares_En_Bridge  = SUM(CASE WHEN b.ID_Bridge IS NOT NULL THEN 1 ELSE 0 END),
    Pares_Sin_Bridge = SUM(CASE WHEN b.ID_Bridge IS NULL     THEN 1 ELSE 0 END),
    Pct_Cobertura    = CAST(100.0 * SUM(CASE WHEN b.ID_Bridge IS NOT NULL THEN 1 ELSE 0 END)
                            / NULLIF(COUNT(*), 0) AS DECIMAL(5,2))
  FROM F
  LEFT JOIN Silver.Bridge_Geografia_Campana b
       ON b.ID_Geografia = F.ID_Geografia
      AND b.ID_Campana   = F.ID_Campana;

PRINT 'fase56b: Bridge_GC poblado desde Evaluacion_Pesos.';
GO
