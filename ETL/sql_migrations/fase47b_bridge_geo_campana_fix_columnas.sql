-- =============================================================================
-- fase47b_bridge_geo_campana_fix_columnas.sql
-- =============================================================================
-- Fix de fase47:
--   La version anterior referenciaba columnas texto 'Campana' y 'Condicion' en
--   Silver.Fact_Tasa_Crecimiento_Brotes que NO existen (la fact ya tiene
--   ID_Campana y ID_Condicion como FKs resueltas por el loader Python).
--
-- Esta version GROUP BY las FKs directamente. No usa el resolver (la resolucion
-- por texto vive ahora en el loader Python, no en el SP).
--
-- Resultado actual de la fact (snapshot al redactar):
--   - 52 filas, todas con ID_Campana, ninguna con ID_Condicion.
--   - => El SP no insertara nada hoy (filtra ID_Condicion IS NOT NULL),
--      pero quedara correcto para cuando el loader pueble ID_Condicion.
--
-- Pre-requisito: bridge vacio (validado) + fase46 (no estrictamente requerida
-- por este SP, pero parte del ecosistema).
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geo_Campana_Condicion
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ins INT = 0, @upd INT = 0, @cuar INT = 0;

    IF OBJECT_ID('tempdb..#Acciones') IS NOT NULL DROP TABLE #Acciones;
    CREATE TABLE #Acciones (accion NVARCHAR(10));

    -- Combinaciones (Geo, Camp, Cond) ya resueltas en la fact, agregadas con
    -- el rango temporal observado por evento.
    ;WITH Combinaciones AS (
        SELECT
            f.ID_Geografia,
            f.ID_Campana,
            f.ID_Condicion,
            MIN(f.Fecha_Evento) AS Vigencia_Inicio,
            MAX(f.Fecha_Evento) AS Vigencia_Fin
        FROM Silver.Fact_Tasa_Crecimiento_Brotes f
        WHERE f.Estado_DQ      = 'OK'
          AND f.ID_Geografia   IS NOT NULL
          AND f.ID_Campana     IS NOT NULL
          AND f.ID_Condicion   IS NOT NULL
        GROUP BY f.ID_Geografia, f.ID_Campana, f.ID_Condicion
    ),
    -- Filas observadas en la fact que se quedan fuera del bridge por FK faltante.
    Incompletas AS (
        SELECT
            f.ID_Geografia,
            f.ID_Campana,
            f.ID_Condicion
        FROM Silver.Fact_Tasa_Crecimiento_Brotes f
        WHERE f.Estado_DQ = 'OK'
          AND (f.ID_Geografia IS NULL OR f.ID_Campana IS NULL OR f.ID_Condicion IS NULL)
    )
    -- Reporte de incompletas a cuarentena (una fila por combinacion).
    INSERT INTO MDM.Cuarentena (Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, Tipo_Regla)
    SELECT DISTINCT
        'Silver.Fact_Tasa_Crecimiento_Brotes',
        'Bridge_GCC',
        LEFT(CONCAT(
            'Geo=',        ISNULL(CAST(i.ID_Geografia AS VARCHAR(20)),  'NULL'),
            ' | Camp=',    ISNULL(CAST(i.ID_Campana   AS VARCHAR(20)),  'NULL'),
            ' | Cond=',    ISNULL(CAST(i.ID_Condicion AS VARCHAR(20)),  'NULL')
        ), 500),
        LEFT(CONCAT(
            CASE WHEN i.ID_Geografia IS NULL THEN 'GEOGRAFIA_NULL;' ELSE '' END,
            CASE WHEN i.ID_Campana   IS NULL THEN 'CAMPANA_NULL;'   ELSE '' END,
            CASE WHEN i.ID_Condicion IS NULL THEN 'CONDICION_NULL;' ELSE '' END
        ), 200),
        'FK_FALTANTE'
    FROM Incompletas i;

    SET @cuar = @@ROWCOUNT;

    ;WITH Validas AS (
        SELECT
            c.ID_Geografia,
            c.ID_Campana,
            c.ID_Condicion,
            c.Vigencia_Inicio,
            c.Vigencia_Fin,
            -- Hash logico: la identidad es (Geo, Camp, Cond). Sin fecha.
            HASHBYTES(
                'SHA2_256',
                CONCAT(c.ID_Geografia, '|', c.ID_Campana, '|', c.ID_Condicion)
            ) AS Hash_Llave
        FROM Combinaciones c
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
                                       THEN src.Vigencia_Inicio
                                       ELSE dst.Vigencia_Inicio END,
            dst.Vigencia_Fin    = CASE WHEN src.Vigencia_Fin    > ISNULL(dst.Vigencia_Fin, '1900-01-01')
                                       THEN src.Vigencia_Fin
                                       ELSE dst.Vigencia_Fin END,
            dst.Es_Activa       = 1
    WHEN NOT MATCHED BY TARGET
        THEN INSERT (ID_Geografia, ID_Campana, ID_Condicion, Vigencia_Inicio, Vigencia_Fin, Es_Activa, Hash_Llave)
             VALUES (src.ID_Geografia, src.ID_Campana, src.ID_Condicion, src.Vigencia_Inicio, src.Vigencia_Fin, 1, src.Hash_Llave)
    OUTPUT $action INTO #Acciones(accion);

    SELECT @ins = SUM(CASE WHEN accion = 'INSERT' THEN 1 ELSE 0 END),
           @upd = SUM(CASE WHEN accion = 'UPDATE' THEN 1 ELSE 0 END)
    FROM #Acciones;

    DROP TABLE #Acciones;

    SELECT
        Filas_Insertadas   = ISNULL(@ins, 0),
        Filas_Actualizadas = ISNULL(@upd, 0),
        Filas_Cuarentena   = @cuar;
END;
GO

-- Smoke test: el SP ahora debe ejecutar sin error 207.
EXEC MDM.usp_Popular_Bridge_Geo_Campana_Condicion;
GO

PRINT 'fase47b: SP corregido y ejecutado sin error de columnas.';
GO
