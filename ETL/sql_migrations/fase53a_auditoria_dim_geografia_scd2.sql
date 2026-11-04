-- =============================================================================
-- fase53a_auditoria_dim_geografia_scd2.sql
-- =============================================================================
-- Objetivo:
--   Auditar el estado SCD2 de Silver.Dim_Geografia. Bug 1 reportado:
--   1,371 combinaciones (Modulo, Turno, Valvula) tienen Es_Vigente = 1
--   simultaneamente; algunas con hasta 100 versiones activas.
--
-- Acciones (READ-ONLY):
--   1. Total de filas en Dim_Geografia y distribucion por Es_Vigente.
--   2. Conteo de naturales con multiples vigentes (la "evidencia del bug").
--   3. Distribucion del numero de vigentes por natural key.
--   4. Top 30 naturales con mas vigentes (caso peor).
--   5. Impacto en el bridge: cuantos ID_Geografia distintos referencia el
--      bridge por natural key.
--
-- Pre-requisito: ninguno.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID('Silver.Dim_Geografia', 'U') IS NULL
BEGIN
    RAISERROR('Silver.Dim_Geografia no existe.', 16, 1);
    RETURN;
END;
GO

PRINT '=== 1. Total filas y distribucion por Es_Vigente ===';
SELECT
    Total_Filas      = COUNT(*),
    Vigentes         = SUM(CASE WHEN Es_Vigente = 1 THEN 1 ELSE 0 END),
    No_Vigentes      = SUM(CASE WHEN Es_Vigente = 0 THEN 1 ELSE 0 END),
    Test_Block       = SUM(CASE WHEN Es_Test_Block = 1 THEN 1 ELSE 0 END)
  FROM Silver.Dim_Geografia;
GO

PRINT '=== 2. Naturales con > 1 vigentes (evidencia del Bug 1) ===';
;WITH NK AS (
    SELECT
        ID_Fundo_Catalogo,
        ID_Sector_Catalogo,
        ID_Modulo_Catalogo,
        ID_Turno_Catalogo,
        ID_Valvula_Catalogo,
        ID_Cama_Catalogo,
        COUNT(*) AS Vigentes
      FROM Silver.Dim_Geografia
     WHERE Es_Vigente = 1
     GROUP BY
        ID_Fundo_Catalogo,
        ID_Sector_Catalogo,
        ID_Modulo_Catalogo,
        ID_Turno_Catalogo,
        ID_Valvula_Catalogo,
        ID_Cama_Catalogo
)
SELECT
    Naturales_Unicas             = COUNT(*),
    Naturales_OK_1_Vigente       = SUM(CASE WHEN Vigentes = 1 THEN 1 ELSE 0 END),
    Naturales_BUG_Mas_De_Uno     = SUM(CASE WHEN Vigentes > 1 THEN 1 ELSE 0 END),
    Filas_Vigentes_Extras_A_Cerrar = SUM(CASE WHEN Vigentes > 1 THEN Vigentes - 1 ELSE 0 END),
    Max_Vigentes_Para_Una_NK     = MAX(Vigentes)
  FROM NK;
GO

PRINT '=== 3. Distribucion de # vigentes por NK ===';
;WITH NK AS (
    SELECT
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        COUNT(*) AS Vigentes
      FROM Silver.Dim_Geografia
     WHERE Es_Vigente = 1
     GROUP BY
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
)
SELECT Vigentes_Por_NK = Vigentes, Conteo = COUNT(*)
  FROM NK
 GROUP BY Vigentes
 ORDER BY Vigentes_Por_NK DESC;
GO

PRINT '=== 4. Top 30 NKs peores (mas vigentes simultaneos) ===';
;WITH NK AS (
    SELECT
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        COUNT(*) AS Vigentes,
        MIN(ID_Geografia) AS Min_ID,
        MAX(ID_Geografia) AS Max_ID,
        MIN(Fecha_Inicio_Vigencia) AS Min_Inicio,
        MAX(Fecha_Inicio_Vigencia) AS Max_Inicio
      FROM Silver.Dim_Geografia
     WHERE Es_Vigente = 1
     GROUP BY
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
    HAVING COUNT(*) > 1
)
SELECT TOP 30
    nk.Vigentes,
    f.Fundo, s.Sector, m.Modulo,
    t.Turno, v.Valvula, c.Cama_Normalizada,
    nk.Min_ID, nk.Max_ID, nk.Min_Inicio, nk.Max_Inicio
  FROM NK nk
  LEFT JOIN Silver.Dim_Fundo_Catalogo   f ON f.ID_Fundo_Catalogo   = nk.ID_Fundo_Catalogo
  LEFT JOIN Silver.Dim_Sector_Catalogo  s ON s.ID_Sector_Catalogo  = nk.ID_Sector_Catalogo
  LEFT JOIN Silver.Dim_Modulo_Catalogo  m ON m.ID_Modulo_Catalogo  = nk.ID_Modulo_Catalogo
  LEFT JOIN Silver.Dim_Turno_Catalogo   t ON t.ID_Turno_Catalogo   = nk.ID_Turno_Catalogo
  LEFT JOIN Silver.Dim_Valvula_Catalogo v ON v.ID_Valvula_Catalogo = nk.ID_Valvula_Catalogo
  LEFT JOIN Silver.Dim_Cama_Catalogo    c ON c.ID_Cama_Catalogo    = nk.ID_Cama_Catalogo
 ORDER BY nk.Vigentes DESC;
GO

PRINT '=== 5. Impacto en bridges (ID_Geografia duplicados via NK) ===';
;WITH NK AS (
    SELECT
        ID_Geografia,
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        Es_Vigente
      FROM Silver.Dim_Geografia
), AGG AS (
    SELECT
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
        COUNT(*)                                                AS Total_Versiones,
        SUM(CASE WHEN Es_Vigente = 1 THEN 1 ELSE 0 END)         AS Vigentes
      FROM NK
     GROUP BY
        ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
        ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo
)
SELECT
    NKs_Totales        = COUNT(*),
    Promedio_Versiones = AVG(CAST(Total_Versiones AS FLOAT)),
    Max_Versiones      = MAX(Total_Versiones),
    NKs_Inflados       = SUM(CASE WHEN Vigentes > 1 THEN 1 ELSE 0 END)
  FROM AGG;
GO

PRINT 'fase53a: auditoria SCD2 completada (read-only).';
GO
