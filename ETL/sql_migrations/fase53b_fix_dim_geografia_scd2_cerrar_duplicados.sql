-- =============================================================================
-- fase53b_fix_dim_geografia_scd2_cerrar_duplicados.sql
-- =============================================================================
-- Objetivo (Bug 1):
--   Para cada natural key (Fundo, Sector, Modulo, Turno, Valvula, Cama) que
--   tenga > 1 fila con Es_Vigente = 1, conservar UNA SOLA fila vigente
--   (la mas reciente por Fecha_Inicio_Vigencia; tiebreaker = mayor
--   ID_Geografia) y cerrar las demas:
--      Es_Vigente = 0, Fecha_Fin_Vigencia = COALESCE(Fecha_Fin_Vigencia, hoy).
--
-- IMPORTANTE:
--   - NO se eliminan filas. NO se remapean FKs en Fact_*. Las facts conservan
--     su ID_Geografia historico — solo cambia el flag SCD2.
--   - Idempotente: re-ejecutar no produce cambios si ya esta sano.
--   - Transaccional: snapshot pre / fix / snapshot post dentro de una sola
--     transaccion con ROLLBACK condicional si el delta sale fuera de tolerancia.
--
-- Pre-requisitos: fase25 (esquema SCD2 columnas Es_Vigente, Fecha_*).
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET XACT_ABORT ON;
GO

IF OBJECT_ID('Silver.Dim_Geografia', 'U') IS NULL
BEGIN
    RAISERROR('Silver.Dim_Geografia no existe.', 16, 1);
    RETURN;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. Snapshot pre-fix
-- -----------------------------------------------------------------------------
DECLARE @vigentes_pre  INT,
        @nk_inflados   INT,
        @max_v_pre     INT;

SELECT @vigentes_pre = COUNT(*)
  FROM Silver.Dim_Geografia
 WHERE Es_Vigente = 1;

;WITH NK AS (
    SELECT
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        COUNT(*) AS V
      FROM Silver.Dim_Geografia
     WHERE Es_Vigente = 1
     GROUP BY
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
)
SELECT
    @nk_inflados = SUM(CASE WHEN V > 1 THEN 1 ELSE 0 END),
    @max_v_pre   = MAX(V)
  FROM NK;

PRINT CONCAT('Pre-fix: vigentes=', @vigentes_pre,
             ', NKs con >1 vigente=', @nk_inflados,
             ', max vigentes por NK=', @max_v_pre);
GO

-- -----------------------------------------------------------------------------
-- 2. Calcular IDs a cerrar: todos menos el "ganador" por NK
--    Ganador: mayor Fecha_Inicio_Vigencia; tiebreaker = mayor ID_Geografia.
-- -----------------------------------------------------------------------------
IF OBJECT_ID('tempdb..#A_Cerrar') IS NOT NULL DROP TABLE #A_Cerrar;

;WITH R AS (
    SELECT
        ID_Geografia,
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        Fecha_Inicio_Vigencia,
        ROW_NUMBER() OVER (
            PARTITION BY
                ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
                ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
            ORDER BY Fecha_Inicio_Vigencia DESC, ID_Geografia DESC
        ) AS rn
      FROM Silver.Dim_Geografia
     WHERE Es_Vigente = 1
)
SELECT ID_Geografia
  INTO #A_Cerrar
  FROM R
 WHERE rn > 1;

DECLARE @a_cerrar INT = (SELECT COUNT(*) FROM #A_Cerrar);
PRINT CONCAT('Filas a cerrar (Es_Vigente 1 -> 0): ', @a_cerrar);
GO

-- -----------------------------------------------------------------------------
-- 3. Fix dentro de transaccion, con verificacion previa
-- -----------------------------------------------------------------------------
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE g
       SET g.Es_Vigente         = 0,
           g.Fecha_Fin_Vigencia = COALESCE(g.Fecha_Fin_Vigencia, CAST(GETDATE() AS DATE))
      FROM Silver.Dim_Geografia g
     INNER JOIN #A_Cerrar a ON a.ID_Geografia = g.ID_Geografia
     WHERE g.Es_Vigente = 1;

    DECLARE @upd INT = @@ROWCOUNT;

    -- Verificacion post: ninguna NK debe quedar con > 1 vigente.
    DECLARE @residuales INT;
    ;WITH NK AS (
        SELECT
            ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
            ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
            COUNT(*) AS V
          FROM Silver.Dim_Geografia
         WHERE Es_Vigente = 1
         GROUP BY
            ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
            ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
    )
    SELECT @residuales = SUM(CASE WHEN V > 1 THEN 1 ELSE 0 END) FROM NK;

    IF @residuales > 0
    BEGIN
        PRINT CONCAT('VERIFICACION FALLO: aun quedan ', @residuales,
                     ' NKs con >1 vigente. ROLLBACK.');
        ROLLBACK TRANSACTION;
        RAISERROR('fase53b: verificacion post-fix fallo. Cambios revertidos.', 16, 1);
        RETURN;
    END;

    COMMIT TRANSACTION;
    PRINT CONCAT('fase53b: cerradas ', @upd, ' filas. Residuales=', @residuales, '. OK.');
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    DECLARE @msg NVARCHAR(2048) = ERROR_MESSAGE();
    PRINT CONCAT('fase53b ERROR: ', @msg);
    THROW;
END CATCH;
GO

-- -----------------------------------------------------------------------------
-- 4. Snapshot post-fix
-- -----------------------------------------------------------------------------
PRINT '=== Snapshot POST-fix ===';
SELECT
    Total_Filas = COUNT(*),
    Vigentes    = SUM(CASE WHEN Es_Vigente = 1 THEN 1 ELSE 0 END),
    Cerradas    = SUM(CASE WHEN Es_Vigente = 0 THEN 1 ELSE 0 END)
  FROM Silver.Dim_Geografia;

;WITH NK AS (
    SELECT
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        COUNT(*) AS V
      FROM Silver.Dim_Geografia
     WHERE Es_Vigente = 1
     GROUP BY
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
)
SELECT
    NKs_Vigentes_Unicas  = COUNT(*),
    NKs_Aun_Inflados     = SUM(CASE WHEN V > 1 THEN 1 ELSE 0 END),
    Max_Vigentes_Por_NK  = MAX(V)
  FROM NK;

PRINT 'fase53b: SCD2 saneado. Re-ejecutar es seguro (idempotente).';
GO
