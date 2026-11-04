-- =============================================================================
-- fase47_bridge_geo_campana_resolver.sql
-- =============================================================================
-- Objetivo (quirurgico):
--   Reescribir MDM.usp_Popular_Bridge_Geo_Campana_Condicion arreglando 2 bugs:
--     1. Hash_Llave incluia Vigencia_Inicio  -> al cambiar MIN(Fecha_Evento)
--        entre corridas, el MERGE INSERTABA filas nuevas en vez de actualizar.
--        Fix: Hash_Llave = SHA2_256(Geo|Camp|Cond), sin fecha.
--     2. Resolucion de Campana hardcoded inline (2 subqueries).
--        Fix: delegar a MDM.fn_Resolver_ID_Campana (creada en fase46).
--
-- NO toca la tabla bridge (estructura, FKs, indices). El UNIQUE sobre
-- Hash_Llave sigue valido: con el nuevo hash equivale a UNIQUE(Geo,Camp,Cond).
--
-- Sigue ligado a Fact_Tasa_Crecimiento_Brotes (la unica fact que poblaba el
-- bridge hoy). La generalizacion a otras facts -> fase48 (Evaluacion Vegetativa).
--
-- Pre-requisito: fase46 ejecutada (funcion resolver existe).
-- Pre-condicion: bridge esta vacio (validado: 0 filas al momento de redactar).
--   Si por alguna razon no esta vacio, el SP recomputara hashes en proxima
--   corrida; el MERGE consolidara duplicados latentes via UNIQUE.
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- -----------------------------------------------------------------------------
-- 0. Defensa: el resolver de fase46 debe existir.
-- -----------------------------------------------------------------------------
IF OBJECT_ID('MDM.fn_Resolver_ID_Campana', 'FN') IS NULL
BEGIN
    RAISERROR('MDM.fn_Resolver_ID_Campana no existe. Ejecutar fase46 antes.', 16, 1);
    RETURN;
END;
GO

-- -----------------------------------------------------------------------------
-- 1. SP populador reescrito (idempotente, MERGE).
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geo_Campana_Condicion
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ins INT = 0, @upd INT = 0, @cuar INT = 0;

    IF OBJECT_ID('tempdb..#Acciones') IS NOT NULL DROP TABLE #Acciones;
    CREATE TABLE #Acciones (accion NVARCHAR(10));

    IF OBJECT_ID('tempdb..#Resueltas') IS NOT NULL DROP TABLE #Resueltas;

    -- Combinaciones distintas observadas en la fact (Geografia ya resuelta por
    -- el loader Python; Campana / Condicion como texto crudo).
    ;WITH Combinaciones AS (
        SELECT
            f.ID_Geografia,
            LTRIM(RTRIM(UPPER(f.Campana)))   AS Campana_Raw,
            LTRIM(RTRIM(UPPER(f.Condicion))) AS Condicion_Raw,
            MIN(f.Fecha_Evento) AS Vigencia_Inicio,
            MAX(f.Fecha_Evento) AS Vigencia_Fin
        FROM Silver.Fact_Tasa_Crecimiento_Brotes f
        WHERE f.Estado_DQ = 'OK'
          AND f.ID_Geografia IS NOT NULL
        GROUP BY
            f.ID_Geografia,
            LTRIM(RTRIM(UPPER(f.Campana))),
            LTRIM(RTRIM(UPPER(f.Condicion)))
    )
    SELECT
        c.ID_Geografia,
        c.Campana_Raw,
        c.Condicion_Raw,
        c.Vigencia_Inicio,
        c.Vigencia_Fin,
        -- Resolver Campana via funcion centralizada (fase46).
        MDM.fn_Resolver_ID_Campana(c.Campana_Raw) AS ID_Campana,
        -- Condicion: split por '/' -> (Sustrato, Certificacion) -> Dim.
        (SELECT TOP 1 dcc.ID_Condicion
           FROM Silver.Dim_Condicion_Cultivo dcc
          WHERE UPPER(dcc.Sustrato)      = LEFT(c.Condicion_Raw,
                                                NULLIF(CHARINDEX('/', c.Condicion_Raw) - 1, -1))
            AND UPPER(dcc.Certificacion) = SUBSTRING(c.Condicion_Raw,
                                                     CHARINDEX('/', c.Condicion_Raw) + 1, 200)
        ) AS ID_Condicion
    INTO #Resueltas
    FROM Combinaciones c;

    -- Cuarentena: filas con FK no resuelta.
    INSERT INTO MDM.Cuarentena (Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, Tipo_Regla)
    SELECT
        'Silver.Fact_Tasa_Crecimiento_Brotes',
        'Bridge_GCC',
        LEFT(CONCAT('Geo=', r.ID_Geografia, ' | Campana=', r.Campana_Raw, ' | Condicion=', r.Condicion_Raw), 500),
        LEFT(CONCAT(
            CASE WHEN r.ID_Campana   IS NULL THEN 'CAMPANA_NO_RESUELTA;'   ELSE '' END,
            CASE WHEN r.ID_Condicion IS NULL THEN 'CONDICION_NO_RESUELTA;' ELSE '' END
        ), 200),
        'CATALOGO'
    FROM #Resueltas r
    WHERE r.ID_Campana IS NULL OR r.ID_Condicion IS NULL;

    SET @cuar = @@ROWCOUNT;

    ;WITH Validas AS (
        SELECT
            r.ID_Geografia,
            r.ID_Campana,
            r.ID_Condicion,
            r.Vigencia_Inicio,
            r.Vigencia_Fin,
            -- HASH SIN FECHA: la llave logica es (Geo, Camp, Cond).
            -- La vigencia es un atributo mutable, no parte de la identidad.
            HASHBYTES(
                'SHA2_256',
                CONCAT(r.ID_Geografia, '|', r.ID_Campana, '|', r.ID_Condicion)
            ) AS Hash_Llave
        FROM #Resueltas r
        WHERE r.ID_Campana   IS NOT NULL
          AND r.ID_Condicion IS NOT NULL
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
            -- Vigencia_Inicio puede retroceder si llega un evento mas antiguo (carga historica).
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

    DROP TABLE #Resueltas;
    DROP TABLE #Acciones;

    SELECT
        Filas_Insertadas   = ISNULL(@ins, 0),
        Filas_Actualizadas = ISNULL(@upd, 0),
        Filas_Cuarentena   = @cuar;
END;
GO

-- -----------------------------------------------------------------------------
-- 2. Sanity check: el SP compila y el OBJECT_ID existe.
-- -----------------------------------------------------------------------------
IF OBJECT_ID('MDM.usp_Popular_Bridge_Geo_Campana_Condicion', 'P') IS NULL
BEGIN
    RAISERROR('SP MDM.usp_Popular_Bridge_Geo_Campana_Condicion no se creo. Revisar.', 16, 1);
END
ELSE
BEGIN
    PRINT 'fase47: MDM.usp_Popular_Bridge_Geo_Campana_Condicion reescrito OK.';
END;
GO
