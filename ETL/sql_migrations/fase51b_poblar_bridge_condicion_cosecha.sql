-- =============================================================================
-- fase51b_poblar_bridge_condicion_cosecha.sql
-- =============================================================================
-- Pobla Silver.Bridge_Geografia_Campana_Condicion para Cosecha_SAP usando el
-- resolver `MDM.fn_Resolver_ID_Campana_Por_Fecha` (single source of truth),
-- a partir de los 125,486 filas YA cargadas en Silver.Fact_Cosecha_SAP.
--
-- Hallazgos del fase51a que motivan este SP:
--   - Fact_Cosecha_SAP: 125K filas, 11 campanas resueltas (2016-2026).
--   - Bridge_Geografia_Campana_Condicion: VACIO (0 filas).
--   - 152 geografias aparecen en 8+ campanas distintas.
--
-- Patron: identico al de `usp_Popular_Bridge_Geografia_Campana_Vegetativa`
-- (fase48b) pero apuntando al bridge con Condicion y usando Cosecha como fuente.
--
-- Idempotente via MERGE sobre Hash_Llave = SHA2_256(Geo|Camp|Cond).
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
-- 1. SP populador desde Fact_Cosecha_SAP
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geo_Campana_Condicion_Cosecha
AS
BEGIN
    SET NOCOUNT ON;

    -- Combinaciones distintas (Geografia, Campana_resuelta, Condicion) con
    -- ventana de vigencia derivada de las fechas observadas en el fact.
    IF OBJECT_ID('tempdb..#Combinaciones_Cosecha') IS NOT NULL DROP TABLE #Combinaciones_Cosecha;

    SELECT
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(f.Fecha_Evento), 0) AS ID_Campana,
        f.ID_Condicion_Cultivo                                         AS ID_Condicion,
        MIN(f.Fecha_Evento)                                            AS Vigencia_Inicio,
        MAX(f.Fecha_Evento)                                            AS Vigencia_Fin,
        COUNT(*)                                                       AS Filas_Fact
    INTO #Combinaciones_Cosecha
      FROM Silver.Fact_Cosecha_SAP f
     WHERE f.Estado_DQ = 'OK'
       AND f.ID_Geografia IS NOT NULL
       AND f.ID_Condicion_Cultivo IS NOT NULL
       AND f.Fecha_Evento IS NOT NULL
     GROUP BY
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(f.Fecha_Evento), 0),
        f.ID_Condicion_Cultivo;

    -- Validacion: pares (Geo, Camp, Cond) deben referenciar dimensiones existentes
    -- (FKs del bridge). Si alguno no existe, lo mandamos a una cuarentena visible.
    IF OBJECT_ID('tempdb..#Cuarentena_FK') IS NOT NULL DROP TABLE #Cuarentena_FK;
    SELECT
        c.ID_Geografia,
        c.ID_Campana,
        c.ID_Condicion,
        c.Filas_Fact,
        Motivo = CASE
            WHEN g.ID_Geografia IS NULL THEN 'GEO_INVALIDA'
            WHEN dc.ID_Campana IS NULL THEN 'CAMPANA_INVALIDA'
            WHEN dcond.ID_Condicion IS NULL THEN 'CONDICION_INVALIDA'
        END
    INTO #Cuarentena_FK
      FROM #Combinaciones_Cosecha c
      LEFT JOIN Silver.Dim_Geografia         g     ON g.ID_Geografia    = c.ID_Geografia
      LEFT JOIN Silver.Dim_Campana           dc    ON dc.ID_Campana     = c.ID_Campana
      LEFT JOIN Silver.Dim_Condicion_Cultivo dcond ON dcond.ID_Condicion = c.ID_Condicion
     WHERE g.ID_Geografia IS NULL
        OR dc.ID_Campana IS NULL
        OR dcond.ID_Condicion IS NULL;

    DECLARE @cuar INT = (SELECT COUNT(*) FROM #Cuarentena_FK);
    IF @cuar > 0
    BEGIN
        PRINT CONCAT('Cuarentena FK inválida: ', @cuar, ' combinaciones (ver #Cuarentena_FK).');
        SELECT TOP 20 * FROM #Cuarentena_FK ORDER BY Filas_Fact DESC;
    END;

    -- MERGE con hash determinista (Geo|Camp|Cond) — idempotente.
    DECLARE @ins INT = 0, @upd INT = 0;
    MERGE Silver.Bridge_Geografia_Campana_Condicion AS dst
    USING (
        SELECT
            c.ID_Geografia,
            c.ID_Campana,
            c.ID_Condicion,
            c.Vigencia_Inicio,
            c.Vigencia_Fin,
            HASHBYTES('SHA2_256',
                CONCAT(CAST(c.ID_Geografia AS NVARCHAR(20)), '|',
                       CAST(c.ID_Campana   AS NVARCHAR(20)), '|',
                       CAST(c.ID_Condicion AS NVARCHAR(20)))
            ) AS Hash_Llave
          FROM #Combinaciones_Cosecha c
         INNER JOIN Silver.Dim_Geografia         g     ON g.ID_Geografia    = c.ID_Geografia
         INNER JOIN Silver.Dim_Campana           dc    ON dc.ID_Campana     = c.ID_Campana
         INNER JOIN Silver.Dim_Condicion_Cultivo dcond ON dcond.ID_Condicion = c.ID_Condicion
    ) AS src
        ON dst.Hash_Llave = src.Hash_Llave
    WHEN MATCHED AND (
            dst.Vigencia_Inicio <> src.Vigencia_Inicio
         OR ISNULL(dst.Vigencia_Fin, '9999-12-31') <> ISNULL(src.Vigencia_Fin, '9999-12-31')
        ) THEN UPDATE SET
            Vigencia_Inicio = src.Vigencia_Inicio,
            Vigencia_Fin    = src.Vigencia_Fin,
            Es_Activa       = 1
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (ID_Geografia, ID_Campana, ID_Condicion, Vigencia_Inicio, Vigencia_Fin, Es_Activa, Hash_Llave)
        VALUES (src.ID_Geografia, src.ID_Campana, src.ID_Condicion, src.Vigencia_Inicio, src.Vigencia_Fin, 1, src.Hash_Llave);

    SET @ins = (SELECT COUNT(*) FROM Silver.Bridge_Geografia_Campana_Condicion);
    PRINT CONCAT('Bridge_GCC (Cosecha): total filas = ', @ins, ', cuarentena FK = ', @cuar);
END;
GO

-- -----------------------------------------------------------------------------
-- 2. Ejecutar el SP
-- -----------------------------------------------------------------------------
EXEC MDM.usp_Popular_Bridge_Geo_Campana_Condicion_Cosecha;
GO

-- -----------------------------------------------------------------------------
-- 3. Auditoria post-poblamiento
-- -----------------------------------------------------------------------------
PRINT '=== A. Total bridge ===';
SELECT
    Filas_Bridge       = COUNT(*),
    Geografias_Unicas  = COUNT(DISTINCT ID_Geografia),
    Campanas_Distintas = COUNT(DISTINCT ID_Campana),
    Condiciones        = COUNT(DISTINCT ID_Condicion),
    Pares_Distintos    = COUNT(DISTINCT CONCAT(ID_Geografia,'|',ID_Campana,'|',ID_Condicion))
  FROM Silver.Bridge_Geografia_Campana_Condicion;

PRINT '=== B. Distribucion por campana ===';
SELECT
    b.ID_Campana,
    dc.Anio_Cosecha,
    dc.Nombre_Campana,
    COUNT(*) AS Entradas_Bridge,
    COUNT(DISTINCT b.ID_Geografia) AS Geografias_Unicas,
    MIN(b.Vigencia_Inicio) AS Min_Fecha,
    MAX(b.Vigencia_Fin)    AS Max_Fecha
  FROM Silver.Bridge_Geografia_Campana_Condicion b
  LEFT JOIN Silver.Dim_Campana dc ON dc.ID_Campana = b.ID_Campana
 GROUP BY b.ID_Campana, dc.Anio_Cosecha, dc.Nombre_Campana
 ORDER BY b.ID_Campana;

PRINT '=== C. Geografias en N campanas (la promesa Snowflake) ===';
;WITH G AS (
    SELECT ID_Geografia, COUNT(DISTINCT ID_Campana) AS n_campanas
      FROM Silver.Bridge_Geografia_Campana_Condicion
     GROUP BY ID_Geografia
)
SELECT n_campanas, COUNT(*) AS Geografias
  FROM G
 GROUP BY n_campanas
 ORDER BY n_campanas DESC;

PRINT '=== D. Sanity: TODOS los pares (Geo, Camp) del Fact estan en el Bridge? ===';
;WITH F AS (
    SELECT DISTINCT
        f.ID_Geografia,
        ISNULL(MDM.fn_Resolver_ID_Campana_Por_Fecha(f.Fecha_Evento),0) AS ID_Campana,
        f.ID_Condicion_Cultivo                                         AS ID_Condicion
      FROM Silver.Fact_Cosecha_SAP f
     WHERE f.Estado_DQ = 'OK'
       AND f.ID_Geografia IS NOT NULL
)
SELECT
    Pares_En_Fact       = COUNT(*),
    Pares_En_Bridge     = SUM(CASE WHEN b.ID_Bridge IS NOT NULL THEN 1 ELSE 0 END),
    Pares_Sin_Bridge    = SUM(CASE WHEN b.ID_Bridge IS NULL     THEN 1 ELSE 0 END),
    Pct_Cobertura       = CAST(100.0 * SUM(CASE WHEN b.ID_Bridge IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,2))
  FROM F
  LEFT JOIN Silver.Bridge_Geografia_Campana_Condicion b
       ON b.ID_Geografia = F.ID_Geografia
      AND b.ID_Campana   = F.ID_Campana
      AND b.ID_Condicion = F.ID_Condicion;

PRINT 'fase51b: Bridge_GCC poblado desde Cosecha_SAP.';
GO
