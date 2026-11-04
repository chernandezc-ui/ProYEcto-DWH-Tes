-- =============================================================================
-- fase59c_poblar_bridge_geo_campana_tasa_crecimiento.sql
-- =============================================================================
-- Objetivo:
--   Crear MDM.usp_Popular_Bridge_Geografia_Campana_Tasa_Crecimiento.
--   Pobla Silver.Bridge_Geografia_Campana (sin condicion) desde Fact_Tasa_Crecimiento_Brotes.
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geografia_Campana_Tasa_Crecimiento
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ins INT = 0, @upd INT = 0, @cuar INT = 0;

    IF OBJECT_ID('tempdb..#Acciones_GC') IS NOT NULL DROP TABLE #Acciones_GC;
    CREATE TABLE #Acciones_GC (accion NVARCHAR(10));

    IF OBJECT_ID('tempdb..#Combinaciones_GC') IS NOT NULL DROP TABLE #Combinaciones_GC;

    SELECT
        f.ID_Geografia,
        f.ID_Campana,
        MIN(CAST(f.Fecha_Evento AS DATE)) AS Vigencia_Inicio,
        MAX(CAST(f.Fecha_Evento AS DATE)) AS Vigencia_Fin
      INTO #Combinaciones_GC
      FROM Silver.Fact_Tasa_Crecimiento_Brotes f
     WHERE f.Estado_DQ    = 'OK'
       AND f.ID_Geografia IS NOT NULL
       AND f.ID_Campana   IS NOT NULL
     GROUP BY f.ID_Geografia, f.ID_Campana;

    -- Cuarentena: filas con FK faltante.
    INSERT INTO MDM.Cuarentena (Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, Tipo_Regla)
    SELECT DISTINCT
        'Silver.Fact_Tasa_Crecimiento_Brotes',
        'Bridge_GC',
        LEFT(CONCAT(
            'Geo=',  ISNULL(CAST(f.ID_Geografia AS VARCHAR(20)), 'NULL'),
            ' | Camp=', ISNULL(CAST(f.ID_Campana AS VARCHAR(20)), 'NULL')
        ), 500),
        LEFT(CONCAT(
            CASE WHEN f.ID_Geografia IS NULL THEN 'GEOGRAFIA_NULL;' ELSE '' END,
            CASE WHEN f.ID_Campana   IS NULL THEN 'CAMPANA_NULL;'   ELSE '' END
        ), 200),
        'FK_FALTANTE'
      FROM Silver.Fact_Tasa_Crecimiento_Brotes f
     WHERE f.Estado_DQ = 'OK'
       AND (f.ID_Geografia IS NULL OR f.ID_Campana IS NULL);

    SET @cuar = @@ROWCOUNT;

    ;WITH Validas AS (
        SELECT
            c.ID_Geografia,
            c.ID_Campana,
            c.Vigencia_Inicio,
            c.Vigencia_Fin,
            HASHBYTES('SHA2_256',
                CONCAT(c.ID_Geografia, '|', c.ID_Campana)
            ) AS Hash_Llave
          FROM #Combinaciones_GC c
    )
    MERGE Silver.Bridge_Geografia_Campana AS dst
    USING Validas AS src
       ON dst.Hash_Llave = src.Hash_Llave
    WHEN MATCHED AND (
            ISNULL(dst.Vigencia_Inicio, '1900-01-01') <> ISNULL(src.Vigencia_Inicio, '1900-01-01')
         OR ISNULL(dst.Vigencia_Fin,    '9999-12-31') <> ISNULL(src.Vigencia_Fin,    '9999-12-31')
         OR dst.Es_Activa = 0
        )
        THEN UPDATE SET
            dst.Vigencia_Inicio = CASE WHEN src.Vigencia_Inicio < dst.Vigencia_Inicio
                                       THEN src.Vigencia_Inicio ELSE dst.Vigencia_Inicio END,
            dst.Vigencia_Fin    = CASE WHEN src.Vigencia_Fin    > ISNULL(dst.Vigencia_Fin, '1900-01-01')
                                       THEN src.Vigencia_Fin    ELSE dst.Vigencia_Fin END,
            dst.Es_Activa       = 1
    WHEN NOT MATCHED BY TARGET
        THEN INSERT (ID_Geografia, ID_Campana, Vigencia_Inicio, Vigencia_Fin, Es_Activa, Hash_Llave)
             VALUES (src.ID_Geografia, src.ID_Campana, src.Vigencia_Inicio, src.Vigencia_Fin, 1, src.Hash_Llave)
    OUTPUT $action INTO #Acciones_GC(accion);

    SELECT @ins = SUM(CASE WHEN accion = 'INSERT' THEN 1 ELSE 0 END),
           @upd = SUM(CASE WHEN accion = 'UPDATE' THEN 1 ELSE 0 END)
      FROM #Acciones_GC;

    DROP TABLE #Acciones_GC;
    DROP TABLE #Combinaciones_GC;

    SELECT
        Filas_Insertadas   = ISNULL(@ins, 0),
        Filas_Actualizadas = ISNULL(@upd, 0),
        Filas_Cuarentena   = @cuar;
END;
GO
