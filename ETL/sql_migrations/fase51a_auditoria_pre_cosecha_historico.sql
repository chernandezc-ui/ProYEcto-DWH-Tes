-- =============================================================================
-- fase51a_auditoria_pre_cosecha_historico.sql
-- =============================================================================
-- Read-only. Antes de migrar el ecosistema Geografia-Campana al fact Cosecha_SAP
-- (157,921 filas historicas, 10 campanas 2016-2025), inspeccionamos:
--   1. Estado actual de Silver.Fact_Cosecha_SAP (125,486 filas conocidas).
--   2. Bronce.Cosecha_SAP: distinct Sector_Raw, distribucion por campana.
--   3. Mapeo Sector_Raw vs Dim_Fundo_Catalogo (cuantos hacen match?).
--   4. Estado del Bridge_Geografia_Campana_Condicion para Cosecha.
--   5. Distribucion campana en Fact actual (consistencia con resolver).
--
-- NO modifica ningun dato. Solo SELECTs.
-- =============================================================================
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

PRINT '=== 1. Snapshot Silver.Fact_Cosecha_SAP ===';
SELECT
    Filas_Fact         = COUNT(*),
    Geografias_Unicas  = COUNT(DISTINCT ID_Geografia),
    Variedades_Unicas  = COUNT(DISTINCT ID_Variedad),
    Tiempos_Unicos     = COUNT(DISTINCT ID_Tiempo),
    Min_Fecha          = MIN(Fecha_Evento),
    Max_Fecha          = MAX(Fecha_Evento),
    Con_Condicion_1    = SUM(CASE WHEN ID_Condicion_Cultivo = 1 THEN 1 ELSE 0 END),
    Con_Condicion_2    = SUM(CASE WHEN ID_Condicion_Cultivo = 2 THEN 1 ELSE 0 END),
    Sin_Condicion      = SUM(CASE WHEN ID_Condicion_Cultivo IS NULL THEN 1 ELSE 0 END)
  FROM Silver.Fact_Cosecha_SAP;
GO

PRINT '=== 2. Distribucion del Fact por campana RESUELTA (con resolver) ===';
;WITH F AS (
    SELECT
        f.ID_Geografia,
        f.Fecha_Evento,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(f.Fecha_Evento), 0) AS ID_Campana_Calc
      FROM Silver.Fact_Cosecha_SAP f
)
SELECT
    F.ID_Campana_Calc,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*)                          AS Filas,
    COUNT(DISTINCT F.ID_Geografia)    AS Geografias,
    MIN(F.Fecha_Evento)               AS Min_Fecha,
    MAX(F.Fecha_Evento)               AS Max_Fecha
  FROM F
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = F.ID_Campana_Calc
 GROUP BY F.ID_Campana_Calc, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY F.ID_Campana_Calc;
GO

PRINT '=== 3. Estado Bronce.Cosecha_SAP (input historico) ===';
SELECT
    Filas_Bronce       = COUNT(*),
    Con_Sector         = SUM(CASE WHEN Sector_Raw IS NOT NULL AND LTRIM(RTRIM(Sector_Raw)) <> '' THEN 1 ELSE 0 END),
    Sin_Sector         = SUM(CASE WHEN Sector_Raw IS NULL OR LTRIM(RTRIM(Sector_Raw)) = '' THEN 1 ELSE 0 END),
    Campanas_Distintas = COUNT(DISTINCT Campana_Raw),
    Sectores_Distintos = COUNT(DISTINCT Sector_Raw),
    Estado_CARGADO     = SUM(CASE WHEN Estado_Carga = 'CARGADO' THEN 1 ELSE 0 END)
  FROM Bronce.Cosecha_SAP;
GO

PRINT '=== 4. Sectores distinct (Bronce) y match con Dim_Fundo_Catalogo ===';
;WITH S AS (
    SELECT
        UPPER(LTRIM(RTRIM(Sector_Raw))) AS Sector_Norm,
        COUNT(*)                        AS n
      FROM Bronce.Cosecha_SAP
     WHERE Sector_Raw IS NOT NULL AND LTRIM(RTRIM(Sector_Raw)) <> ''
     GROUP BY UPPER(LTRIM(RTRIM(Sector_Raw)))
)
SELECT
    S.Sector_Norm,
    S.n                                AS Filas_Bronce,
    df.ID_Fundo_Catalogo               AS Match_Fundo_ID,
    df.Fundo                           AS Match_Fundo_Nombre,
    CASE WHEN df.ID_Fundo_Catalogo IS NULL THEN 'SIN_MATCH' ELSE 'OK' END AS Estado_Match
  FROM S
  LEFT JOIN Silver.Dim_Fundo_Catalogo df ON UPPER(df.Fundo) = S.Sector_Norm
 ORDER BY S.n DESC;
GO

PRINT '=== 5. Distribucion campana en Bronce.Cosecha_SAP (raw) ===';
SELECT
    Campana_Raw,
    COUNT(*) AS Filas,
    MIN(Fecha_Raw) AS Min_Fecha_Raw,
    MAX(Fecha_Raw) AS Max_Fecha_Raw,
    COUNT(DISTINCT Sector_Raw) AS Sectores_En_Campana
  FROM Bronce.Cosecha_SAP
 WHERE Estado_Carga = 'CARGADO'
 GROUP BY Campana_Raw
 ORDER BY Campana_Raw;
GO

PRINT '=== 6. Distribucion del Fact por Fundo actual ===';
SELECT TOP 30
    ISNULL(df.Fundo, 'SIN_FUNDO') AS Fundo,
    COUNT(*) AS Filas
  FROM Silver.Fact_Cosecha_SAP f
  LEFT JOIN Silver.Dim_Geografia g       ON g.ID_Geografia       = f.ID_Geografia
  LEFT JOIN Silver.Dim_Fundo_Catalogo df ON df.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
 GROUP BY df.Fundo
 ORDER BY COUNT(*) DESC;
GO

PRINT '=== 7. Estado Bridge_Geografia_Campana_Condicion para Cosecha ===';
SELECT
    Filas_Bridge       = COUNT(*),
    Pares_Distintos    = COUNT(DISTINCT CONCAT(ID_Geografia,'|',ID_Campana,'|',ID_Condicion)),
    Campanas_Distintas = COUNT(DISTINCT ID_Campana),
    Geografias_Unicas  = COUNT(DISTINCT ID_Geografia)
  FROM Silver.Bridge_Geografia_Campana_Condicion;
GO

PRINT '=== 8. Geografias compartidas entre 2+ campanas (esperado: muchas con historia larga) ===';
;WITH F AS (
    SELECT
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(f.Fecha_Evento), 0) AS ID_Campana_Calc
      FROM Silver.Fact_Cosecha_SAP f
), Geo_Cnt AS (
    SELECT ID_Geografia, COUNT(DISTINCT ID_Campana_Calc) AS n_campanas
      FROM F GROUP BY ID_Geografia
)
SELECT
    n_campanas,
    COUNT(*) AS Geografias
  FROM Geo_Cnt
 GROUP BY n_campanas
 ORDER BY n_campanas DESC;
GO

PRINT 'fase51a: auditoria completa. Revisar resultados antes de fase51b.';
GO
