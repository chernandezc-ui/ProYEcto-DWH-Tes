-- =============================================================================
-- fase54_backfill_fundo_fact_cosecha_sap.sql  (v3 - sin filtro Es_Vigente)
-- =============================================================================
-- Objetivo (Bug 3):
--   ~35,708 de 125,486 filas en Silver.Fact_Cosecha_SAP apuntan a
--   Dim_Geografia con Fundo = SIN_FUNDO. El procesador historico paso
--   None como Fundo_Raw al momento de la carga.
--
-- Causa del Fact_SIN_FUNDO_Restantes sin cambio en v2:
--   Las filas del Fact referencian ID_Geografia que fueron cerrados por el
--   fix SCD2 (fase53b -> Es_Vigente=0). v2 solo actualizaba Es_Vigente=1.
--   v3 actualiza TODAS las filas de Dim_Geografia con SIN_FUNDO (sin
--   importar Es_Vigente) que tengan un mapeo MTV -> Fundo unico. Esto es
--   correcto: el atributo Fundo es un hecho del campo, no del SCD2.
--
-- Estrategia:
--   Mapeo (Modulo_Cat, Turno_Cat, Valvula_Cat) -> ID_Fundo_Catalogo
--   derivado de las filas con Fundo CONOCIDO (cualquier Es_Vigente).
--   Solo se resuelven NKs con un unico fundo posible.
--
-- Columnas reales (fase25 DDL):
--   Dim_Fundo_Catalogo.Fundo  |  Dim_Modulo_Catalogo.Modulo
--   Dim_Turno_Catalogo.Turno  |  Dim_Valvula_Catalogo.Valvula
--
-- Idempotente: re-ejecutar es no-op si ya esta resuelto.
-- Pre-requisito: fase53b aplicado.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET XACT_ABORT ON;
GO

IF OBJECT_ID('Silver.Dim_Fundo_Catalogo', 'U') IS NULL
    OR OBJECT_ID('Silver.Dim_Geografia', 'U') IS NULL
BEGIN
    RAISERROR('Silver.Dim_Fundo_Catalogo o Dim_Geografia no existen.', 16, 1);
    RETURN;
END;
GO

-- =============================================================================
-- A. Diagnostico pre-fix
-- =============================================================================
PRINT '=== A. Estado pre-fix: Dim_Geografia y Fact_Cosecha_SAP con SIN_FUNDO ===';
;WITH SIN_F AS (
    SELECT ID_Fundo_Catalogo
      FROM Silver.Dim_Fundo_Catalogo
     WHERE UPPER(LTRIM(RTRIM(Fundo))) IN ('SIN_FUNDO','SIN FUNDO','N/A','DESCONOCIDO','')
)
SELECT
    Geo_Total              = (SELECT COUNT(*) FROM Silver.Dim_Geografia),
    Geo_Vigentes           = (SELECT COUNT(*) FROM Silver.Dim_Geografia WHERE Es_Vigente = 1),
    Geo_SIN_FUNDO_Total    = (SELECT COUNT(*) FROM Silver.Dim_Geografia
                               WHERE ID_Fundo_Catalogo IN (SELECT ID_Fundo_Catalogo FROM SIN_F)),
    Geo_SIN_FUNDO_Vigente  = (SELECT COUNT(*) FROM Silver.Dim_Geografia
                               WHERE ID_Fundo_Catalogo IN (SELECT ID_Fundo_Catalogo FROM SIN_F)
                                 AND Es_Vigente = 1),
    Geo_SIN_FUNDO_Cerrada  = (SELECT COUNT(*) FROM Silver.Dim_Geografia
                               WHERE ID_Fundo_Catalogo IN (SELECT ID_Fundo_Catalogo FROM SIN_F)
                                 AND Es_Vigente = 0),
    Filas_Fact_Total       = (SELECT COUNT(*) FROM Silver.Fact_Cosecha_SAP),
    Filas_Fact_SIN_FUNDO   = ISNULL((
        SELECT COUNT(*) FROM Silver.Fact_Cosecha_SAP f
         WHERE EXISTS (
            SELECT 1 FROM Silver.Dim_Geografia g
              JOIN SIN_F sf ON sf.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
             WHERE g.ID_Geografia = f.ID_Geografia
         )
    ), 0);
GO

-- =============================================================================
-- B. Mapeo MTV -> Fundo unico desde CUALQUIER fila Dim_Geografia (v3: sin Es_Vigente)
-- =============================================================================
PRINT '=== B. Construyendo mapeo MTV -> Fundo (todas las versiones SCD2) ===';

IF OBJECT_ID('tempdb..#Mapeo_MTV_Fundo') IS NOT NULL DROP TABLE #Mapeo_MTV_Fundo;
IF OBJECT_ID('tempdb..#A_Resolver')      IS NOT NULL DROP TABLE #A_Resolver;
IF OBJECT_ID('tempdb..#AGG_Temp')        IS NOT NULL DROP TABLE #AGG_Temp;

-- FIX (v4): NO poner Fundos_Distintos en #Mapeo_MTV_Fundo.
-- SQL Server valida columnas de temp tables entre GO-batches en runtime y da
-- error 207 si el alias calculado no existe como columna real.
-- Solucion: usar tabla intermedia #AGG_Temp (con Fundos_Distintos) dentro del
-- mismo batch, filtrar aqui, e insertar solo columnas limpias en #Mapeo_MTV_Fundo.

;WITH SIN_F2 AS (
    SELECT ID_Fundo_Catalogo
      FROM Silver.Dim_Fundo_Catalogo
     WHERE UPPER(LTRIM(RTRIM(Fundo))) IN ('SIN_FUNDO','SIN FUNDO','N/A','DESCONOCIDO','')
), CONOCIDOS2 AS (
    SELECT
        g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo,
        g.ID_Fundo_Catalogo
      FROM Silver.Dim_Geografia g
     WHERE g.ID_Fundo_Catalogo NOT IN (SELECT ID_Fundo_Catalogo FROM SIN_F2)
     GROUP BY g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo, g.ID_Fundo_Catalogo
)
SELECT
    ID_Modulo_Catalogo, ID_Turno_Catalogo, ID_Valvula_Catalogo,
    COUNT(DISTINCT ID_Fundo_Catalogo) AS Fundos_Distintos,
    MIN(ID_Fundo_Catalogo)            AS ID_Fundo_Resuelto
  INTO #AGG_Temp
  FROM CONOCIDOS2
 GROUP BY ID_Modulo_Catalogo, ID_Turno_Catalogo, ID_Valvula_Catalogo;

DECLARE @map_unico INT = (SELECT COUNT(*) FROM #AGG_Temp WHERE Fundos_Distintos = 1);
DECLARE @map_ambig INT = (SELECT COUNT(*) FROM #AGG_Temp WHERE Fundos_Distintos > 1);
PRINT CONCAT('  Mapeo unico (resoluble): ', @map_unico, '   |   Ambiguos (sin resolver): ', @map_ambig);

-- Solo mapeos UNICOS entran en #Mapeo_MTV_Fundo (sin columna Fundos_Distintos)
SELECT ID_Modulo_Catalogo, ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Fundo_Resuelto
  INTO #Mapeo_MTV_Fundo
  FROM #AGG_Temp
 WHERE Fundos_Distintos = 1;

DROP TABLE #AGG_Temp;
GO

-- =============================================================================
-- C. Candidatos: TODAS las Dim_Geografia SIN_FUNDO con mapeo unico
-- =============================================================================
PRINT '=== C. Identificando candidatos (Es_Vigente 0 y 1) ===';

;WITH SIN_F AS (
    SELECT ID_Fundo_Catalogo
      FROM Silver.Dim_Fundo_Catalogo
     WHERE UPPER(LTRIM(RTRIM(Fundo))) IN ('SIN_FUNDO','SIN FUNDO','N/A','DESCONOCIDO','')
)
SELECT
    g.ID_Geografia,
    g.Es_Vigente,
    g.ID_Fundo_Catalogo AS Fundo_Actual,
    m.ID_Fundo_Resuelto AS Fundo_Nuevo
  INTO #A_Resolver
  FROM Silver.Dim_Geografia g
 INNER JOIN #Mapeo_MTV_Fundo m
         ON m.ID_Modulo_Catalogo  = g.ID_Modulo_Catalogo
        AND m.ID_Turno_Catalogo   = g.ID_Turno_Catalogo
        AND m.ID_Valvula_Catalogo = g.ID_Valvula_Catalogo
 WHERE g.ID_Fundo_Catalogo IN (SELECT ID_Fundo_Catalogo FROM SIN_F)
   AND m.ID_Fundo_Resuelto NOT IN (SELECT ID_Fundo_Catalogo FROM SIN_F);
   -- m.Fundos_Distintos ya no existe en #Mapeo_MTV_Fundo: la tabla solo
   -- contiene mapeos unicos (filtrado en batch B). No necesita la condicion.

DECLARE @total_cand INT = (SELECT COUNT(*) FROM #A_Resolver);
DECLARE @cand_vig   INT = (SELECT COUNT(*) FROM #A_Resolver WHERE Es_Vigente = 1);
DECLARE @cand_cerr  INT = (SELECT COUNT(*) FROM #A_Resolver WHERE Es_Vigente = 0);
PRINT CONCAT('  Candidatos totales: ', @total_cand,
             '  (vigentes=', @cand_vig, ', cerradas=', @cand_cerr, ')');

-- Muestra top 20
SELECT TOP 20
    ar.ID_Geografia, ar.Es_Vigente,
    Fundo_Actual = fa.Fundo,
    Fundo_Nuevo  = fn.Fundo
  FROM #A_Resolver ar
  LEFT JOIN Silver.Dim_Fundo_Catalogo fa ON fa.ID_Fundo_Catalogo = ar.Fundo_Actual
  LEFT JOIN Silver.Dim_Fundo_Catalogo fn ON fn.ID_Fundo_Catalogo = ar.Fundo_Nuevo;
GO

-- =============================================================================
-- D. Fix transaccional
-- =============================================================================
PRINT '=== D. Aplicando UPDATE en Dim_Geografia ===';

BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE g
       SET g.ID_Fundo_Catalogo = ar.Fundo_Nuevo
      FROM Silver.Dim_Geografia g
     INNER JOIN #A_Resolver ar ON ar.ID_Geografia = g.ID_Geografia
     WHERE g.ID_Fundo_Catalogo = ar.Fundo_Actual;

    DECLARE @upd INT = @@ROWCOUNT;
    DECLARE @esperados INT = (SELECT COUNT(*) FROM #A_Resolver);

    IF @upd <> @esperados
    BEGIN
        ROLLBACK TRANSACTION;
        RAISERROR(
            'fase54 v3: verificacion fallo (%d actualizadas vs %d esperadas). ROLLBACK.',
            16, 1, @upd, @esperados
        );
        RETURN;
    END;

    COMMIT TRANSACTION;
    PRINT CONCAT('  OK: ', @upd, ' filas de Dim_Geografia actualizadas.');
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT CONCAT('  ERROR: ', ERROR_MESSAGE());
    THROW;
END CATCH;
GO

-- =============================================================================
-- E. Snapshot POST
-- =============================================================================
PRINT '=== E. Snapshot POST-fix ===';
;WITH SIN_F AS (
    SELECT ID_Fundo_Catalogo
      FROM Silver.Dim_Fundo_Catalogo
     WHERE UPPER(LTRIM(RTRIM(Fundo))) IN ('SIN_FUNDO','SIN FUNDO','N/A','DESCONOCIDO','')
)
SELECT
    Geo_SIN_FUNDO_Total_Restante   = (SELECT COUNT(*) FROM Silver.Dim_Geografia
                                       WHERE ID_Fundo_Catalogo IN (SELECT ID_Fundo_Catalogo FROM SIN_F)),
    Geo_SIN_FUNDO_Vigente_Restante = (SELECT COUNT(*) FROM Silver.Dim_Geografia
                                       WHERE ID_Fundo_Catalogo IN (SELECT ID_Fundo_Catalogo FROM SIN_F)
                                         AND Es_Vigente = 1),
    Filas_Fact_SIN_FUNDO_Restante  = ISNULL((
        SELECT COUNT(*) FROM Silver.Fact_Cosecha_SAP f
         WHERE EXISTS (
            SELECT 1 FROM Silver.Dim_Geografia g
              JOIN SIN_F sf ON sf.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
             WHERE g.ID_Geografia = f.ID_Geografia
         )
    ), 0),
    Filas_Fact_Total               = (SELECT COUNT(*) FROM Silver.Fact_Cosecha_SAP);
GO

-- =============================================================================
-- F. NKs ambiguas para revision humana
-- =============================================================================
PRINT '=== F. NKs ambiguas (2+ fundos posibles - sin resolver) ===';
;WITH SIN_F AS (
    SELECT ID_Fundo_Catalogo
      FROM Silver.Dim_Fundo_Catalogo
     WHERE UPPER(LTRIM(RTRIM(Fundo))) IN ('SIN_FUNDO','SIN FUNDO','N/A','DESCONOCIDO','')
), CONOCIDOS AS (
    SELECT
        g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo,
        g.ID_Fundo_Catalogo
      FROM Silver.Dim_Geografia g
     WHERE g.ID_Fundo_Catalogo NOT IN (SELECT ID_Fundo_Catalogo FROM SIN_F)
     GROUP BY g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo, g.ID_Fundo_Catalogo
)
SELECT TOP 20
    m.Modulo, t.Turno, v.Valvula,
    Fundos_Distintos = COUNT(DISTINCT c.ID_Fundo_Catalogo),
    Fundos = STRING_AGG(f.Fundo, ' / ')
  FROM CONOCIDOS c
  LEFT JOIN Silver.Dim_Modulo_Catalogo  m ON m.ID_Modulo_Catalogo  = c.ID_Modulo_Catalogo
  LEFT JOIN Silver.Dim_Turno_Catalogo   t ON t.ID_Turno_Catalogo   = c.ID_Turno_Catalogo
  LEFT JOIN Silver.Dim_Valvula_Catalogo v ON v.ID_Valvula_Catalogo = c.ID_Valvula_Catalogo
  LEFT JOIN Silver.Dim_Fundo_Catalogo   f ON f.ID_Fundo_Catalogo   = c.ID_Fundo_Catalogo
 GROUP BY m.Modulo, t.Turno, v.Valvula, c.ID_Modulo_Catalogo, c.ID_Turno_Catalogo, c.ID_Valvula_Catalogo
HAVING COUNT(DISTINCT c.ID_Fundo_Catalogo) > 1
 ORDER BY COUNT(DISTINCT c.ID_Fundo_Catalogo) DESC;
GO

PRINT 'fase54 v4: backfill Fundo completado (todas las versiones SCD2, fix error 207).';
GO
