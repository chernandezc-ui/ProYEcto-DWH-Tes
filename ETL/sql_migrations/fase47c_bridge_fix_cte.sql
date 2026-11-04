-- fase47c: fix del CTE (Combinaciones se usaba fuera de su statement).
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geo_Campana_Condicion
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ins INT = 0, @upd INT = 0, @cuar INT = 0;

    IF OBJECT_ID('tempdb..#Acciones')      IS NOT NULL DROP TABLE #Acciones;
    IF OBJECT_ID('tempdb..#Combinaciones') IS NOT NULL DROP TABLE #Combinaciones;

    CREATE TABLE #Acciones (accion NVARCHAR(10));

    -- Combinaciones validas (las 3 FKs presentes) con rango temporal observado.
    SELECT
        f.ID_Geografia,
        f.ID_Campana,
        f.ID_Condicion,
        MIN(f.Fecha_Evento) AS Vigencia_Inicio,
        MAX(f.Fecha_Evento) AS Vigencia_Fin
    INTO #Combinaciones
    FROM Silver.Fact_Tasa_Crecimiento_Brotes f
    WHERE f.Estado_DQ    = 'OK'
      AND f.ID_Geografia IS NOT NULL
      AND f.ID_Campana   IS NOT NULL
      AND f.ID_Condicion IS NOT NULL
    GROUP BY f.ID_Geografia, f.ID_Campana, f.ID_Condicion;

    -- Cuarentena: filas con alguna FK faltante (no entran al bridge).
    INSERT INTO MDM.Cuarentena (Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, Tipo_Regla)
    SELECT DISTINCT
        'Silver.Fact_Tasa_Crecimiento_Brotes',
        'Bridge_GCC',
        LEFT(CONCAT(
            'Geo=',  ISNULL(CAST(f.ID_Geografia AS VARCHAR(20)), 'NULL'),
            ' | Camp=', ISNULL(CAST(f.ID_Campana   AS VARCHAR(20)), 'NULL'),
            ' | Cond=', ISNULL(CAST(f.ID_Condicion AS VARCHAR(20)), 'NULL')
        ), 500),
        LEFT(CONCAT(
            CASE WHEN f.ID_Geografia IS NULL THEN 'GEOGRAFIA_NULL;' ELSE '' END,
            CASE WHEN f.ID_Campana   IS NULL THEN 'CAMPANA_NULL;'   ELSE '' END,
            CASE WHEN f.ID_Condicion IS NULL THEN 'CONDICION_NULL;' ELSE '' END
        ), 200),
        'FK_FALTANTE'
    FROM Silver.Fact_Tasa_Crecimiento_Brotes f
    WHERE f.Estado_DQ = 'OK'
      AND (f.ID_Geografia IS NULL OR f.ID_Campana IS NULL OR f.ID_Condicion IS NULL);

    SET @cuar = @@ROWCOUNT;

    -- MERGE al bridge (hash sin fecha).
    ;WITH Validas AS (
        SELECT
            c.ID_Geografia,
            c.ID_Campana,
            c.ID_Condicion,
            c.Vigencia_Inicio,
            c.Vigencia_Fin,
            HASHBYTES('SHA2_256',
                CONCAT(c.ID_Geografia, '|', c.ID_Campana, '|', c.ID_Condicion)
            ) AS Hash_Llave
        FROM #Combinaciones c
    )
    MERGE Silver.Bridge_Geografia_Campana_Condicion AS dst
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
        THEN INSERT (ID_Geografia, ID_Campana, ID_Condicion, Vigencia_Inicio, Vigencia_Fin, Es_Activa, Hash_Llave)
             VALUES (src.ID_Geografia, src.ID_Campana, src.ID_Condicion, src.Vigencia_Inicio, src.Vigencia_Fin, 1, src.Hash_Llave)
    OUTPUT $action INTO #Acciones(accion);

    SELECT @ins = SUM(CASE WHEN accion = 'INSERT' THEN 1 ELSE 0 END),
           @upd = SUM(CASE WHEN accion = 'UPDATE' THEN 1 ELSE 0 END)
      FROM #Acciones;

    DROP TABLE #Acciones;
    DROP TABLE #Combinaciones;

    SELECT
        Filas_Insertadas   = ISNULL(@ins, 0),
        Filas_Actualizadas = ISNULL(@upd, 0),
        Filas_Cuarentena   = @cuar;
END;
GO

EXEC MDM.usp_Popular_Bridge_Geo_Campana_Condicion;
GO
PRINT 'fase47c: SP ejecutado OK.';
GO
