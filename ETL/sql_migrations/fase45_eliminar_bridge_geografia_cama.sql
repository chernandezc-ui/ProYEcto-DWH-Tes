-- =============================================================================
-- FASE 45: Eliminar Silver.Bridge_Geografia_Cama y Actualizar SPs
--
-- PROPÓSITO: Elimina la tabla redundante Bridge_Geografia_Cama y actualiza
-- los stored procedures para que operen directamente sobre la dimensión
-- Silver.Dim_Geografia a granularidad de Cama.
--
-- Script IDEMPOTENTE: se puede correr varias veces de forma segura.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Modificar Silver.sp_Resolver_Geografia_Cama
-- ─────────────────────────────────────────────────────────────────────────────
PRINT 'Actualizando Silver.sp_Resolver_Geografia_Cama...';
GO
CREATE OR ALTER PROCEDURE Silver.sp_Resolver_Geografia_Cama
    @Modulo_Raw NVARCHAR(100) = NULL,
    @Turno_Raw NVARCHAR(100) = NULL,
    @Valvula_Raw NVARCHAR(100) = NULL,
    @Cama_Raw NVARCHAR(100) = NULL,
    @Cama_Min_Permitida INT = 1,
    @Cama_Max_Permitida INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE
        @Modulo_Token NVARCHAR(50),
        @Turno_Token NVARCHAR(50),
        @Valvula_Token NVARCHAR(50),
        @Cama_Token NVARCHAR(50),
        @Modulo_Int INT = NULL,
        @SubModulo_Int INT = NULL,
        @Turno_Int INT = NULL,
        @Cama_Int INT = NULL,
        @Es_Modulo_Especial BIT = 0,
        @Es_Test_Block_Regla BIT = 0,
        @Coincidencias_Geo INT = 0,
        @ID_Geografia INT = NULL,
        @ID_Cama_Catalogo INT = 0, -- Por defecto 0 (Sin Cama)
        @Estado_Resolucion NVARCHAR(50),
        @Detalle NVARCHAR(300),
        @Tipo_Conduccion_Regla NVARCHAR(50) = NULL,
        @Prioridad_Regla INT = NULL;

    SELECT
        @Modulo_Token = NULLIF(LTRIM(RTRIM(@Modulo_Raw)), ''),
        @Turno_Token = NULLIF(LTRIM(RTRIM(@Turno_Raw)), ''),
        @Valvula_Token = NULLIF(LTRIM(RTRIM(@Valvula_Raw)), ''),
        @Cama_Token = NULLIF(LTRIM(RTRIM(@Cama_Raw)), '');

    IF @Modulo_Token IS NOT NULL AND @Modulo_Token NOT LIKE '%[^0-9]%'
        SET @Modulo_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Modulo_Token));

    IF @Turno_Token IS NOT NULL AND @Turno_Token NOT LIKE '%[^0-9]%'
        SET @Turno_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Turno_Token));

    IF @Valvula_Token IS NOT NULL AND @Valvula_Token NOT LIKE '%[^0-9]%'
        SET @Valvula_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Valvula_Token));

    IF @Cama_Token IS NOT NULL AND @Cama_Token NOT LIKE '%[^0-9]%'
        SET @Cama_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Cama_Token));

    IF @Turno_Token IS NOT NULL AND @Turno_Token NOT LIKE '%[^0-9]%'
        SET @Turno_Int = CONVERT(INT, @Turno_Token);

    IF @Cama_Token IS NOT NULL AND @Cama_Token NOT LIKE '%[^0-9]%'
        SET @Cama_Int = CONVERT(INT, @Cama_Token);

    IF OBJECT_ID('MDM.Regla_Modulo_Raw', 'U') IS NOT NULL
       AND @Modulo_Token IS NOT NULL
    BEGIN
        SELECT TOP (1)
            @Modulo_Int = r.Modulo_Int,
            @SubModulo_Int = r.SubModulo_Int,
            @Es_Test_Block_Regla = ISNULL(r.Es_Test_Block, 0),
            @Tipo_Conduccion_Regla = r.Tipo_Conduccion
        FROM MDM.Regla_Modulo_Raw r
        WHERE r.Es_Activa = 1
          AND UPPER(LTRIM(RTRIM(r.Modulo_Raw))) = UPPER(@Modulo_Token);
    END;

    IF @Modulo_Int IS NULL
       AND OBJECT_ID('MDM.Regla_Modulo_Turno_SubModulo', 'U') IS NOT NULL
       AND @Modulo_Token IS NOT NULL
       AND @Turno_Int IS NOT NULL
    BEGIN
        SELECT TOP (1)
            @Modulo_Int = r.Modulo_Int,
            @SubModulo_Int = r.SubModulo_Int,
            @Es_Test_Block_Regla = ISNULL(r.Es_Test_Block, 0),
            @Tipo_Conduccion_Regla = r.Tipo_Conduccion,
            @Prioridad_Regla = r.Prioridad
        FROM MDM.Regla_Modulo_Turno_SubModulo r
        WHERE r.Es_Activa = 1
          AND UPPER(LTRIM(RTRIM(r.Modulo_Raw_Base))) = UPPER(@Modulo_Token)
          AND @Turno_Int BETWEEN r.Turno_Desde AND r.Turno_Hasta
        ORDER BY r.Prioridad ASC, r.Turno_Desde ASC, r.ID_Regla_Modulo_Turno ASC;
    END;

    IF @Modulo_Int IS NULL
       AND @Modulo_Token IS NOT NULL
       AND @Modulo_Token NOT LIKE '%[^0-9]%'
    BEGIN
        SET @Modulo_Int = CONVERT(INT, @Modulo_Token);
    END;

    IF @Es_Test_Block_Regla = 1
    BEGIN
        IF @Turno_Int IS NULL OR @Valvula_Token IS NULL
        BEGIN
            SET @Estado_Resolucion = 'CLAVE_GEOGRAFICA_INCOMPLETA';
            SET @Detalle = 'Test block sin turno o valvula.';
        END
        ELSE
        BEGIN
            ;WITH GeoTB AS (
                SELECT g.ID_Geografia
                FROM Silver.Dim_Geografia g
                JOIN Silver.Dim_Turno_Catalogo tc ON tc.ID_Turno_Catalogo = g.ID_Turno_Catalogo
                JOIN Silver.Dim_Valvula_Catalogo vc ON vc.ID_Valvula_Catalogo = g.ID_Valvula_Catalogo
                WHERE ISNULL(g.Es_Vigente, 1) = 1
                  AND ISNULL(g.Es_Test_Block, 0) = 1
                  AND tc.Turno = @Turno_Int
                  AND (
                        CASE
                            WHEN vc.Valvula IS NULL THEN NULL
                            WHEN LTRIM(RTRIM(vc.Valvula)) = '' THEN NULL
                            WHEN LTRIM(RTRIM(vc.Valvula)) NOT LIKE '%[^0-9]%'
                                THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(vc.Valvula))))
                            ELSE LTRIM(RTRIM(vc.Valvula))
                        END
                      ) = @Valvula_Token
            )
            SELECT
                @Coincidencias_Geo = COUNT(*),
                @ID_Geografia = MIN(ID_Geografia)
            FROM GeoTB;

            IF @Coincidencias_Geo = 1
            BEGIN
                SET @Estado_Resolucion = 'RESUELTA_TEST_BLOCK';
                SET @Detalle = 'Test block resuelto por Turno/Valvula.';
            END
            ELSE IF @Coincidencias_Geo = 0
            BEGIN
                SET @Estado_Resolucion = 'TEST_BLOCK_NO_MAPEADO';
                SET @Detalle = 'No existe geografia test block para Turno/Valvula.';
                SET @ID_Geografia = NULL;
            END
            ELSE
            BEGIN
                SET @Estado_Resolucion = 'TEST_BLOCK_AMBIGUO';
                SET @Detalle = 'Mas de una geografia test block para Turno/Valvula.';
                SET @ID_Geografia = NULL;
            END
        END;

        SELECT
            @Modulo_Token AS Modulo_Token,
            @Turno_Token AS Turno_Token,
            @Valvula_Token AS Valvula_Token,
            @Cama_Token AS Cama_Token,
            @Modulo_Int AS Modulo_Int,
            @SubModulo_Int AS SubModulo_Int,
            @Turno_Int AS Turno_Int,
            @Cama_Int AS Cama_Int,
            @ID_Geografia AS ID_Geografia,
            @ID_Cama_Catalogo AS ID_Cama_Catalogo,
            @Estado_Resolucion AS Estado_Resolucion,
            @Detalle AS Detalle;

        RETURN;
    END;

    IF @Modulo_Int IS NULL
        SET @Es_Modulo_Especial = 1;

    IF @Es_Modulo_Especial = 1
    BEGIN
        SET @Estado_Resolucion = 'CASO_ESPECIAL_MODULO';
        SET @Detalle = 'Modulo especial (sin regla operativa).';
    END
    ELSE IF @Turno_Int IS NULL OR @Valvula_Token IS NULL
    BEGIN
        SET @Estado_Resolucion = 'CLAVE_GEOGRAFICA_INCOMPLETA';
        SET @Detalle = 'Falta turno o valvula.';
    END
    ELSE
    BEGIN
        -- Resolver ID_Cama_Catalogo si se especificó cama válida
        IF @Cama_Token IS NOT NULL AND @Cama_Token <> '0'
        BEGIN
            IF @Cama_Int IS NULL OR @Cama_Int < @Cama_Min_Permitida OR @Cama_Int > @Cama_Max_Permitida
            BEGIN
                SET @Estado_Resolucion = 'CAMA_NO_VALIDA';
                SET @Detalle = 'Cama fuera de rango permitido.';
            END
            ELSE
            BEGIN
                SELECT TOP 1
                    @ID_Cama_Catalogo = c.ID_Cama_Catalogo
                FROM Silver.Dim_Cama_Catalogo c
                WHERE c.Es_Activa = 1
                  AND c.Cama_Normalizada = CONVERT(NVARCHAR(50), @Cama_Int);

                IF @ID_Cama_Catalogo IS NULL
                BEGIN
                    SET @Estado_Resolucion = 'CAMA_NO_CATALOGO';
                    SET @Detalle = 'Cama valida, pero no existe en catalogo.';
                END
            END
        END;

        -- Si no hay problemas con la validación de la cama, buscar en la dimensión
        IF @Estado_Resolucion IS NULL
        BEGIN
            ;WITH Geo AS (
                SELECT g.ID_Geografia
                FROM Silver.Dim_Geografia g
                JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
                JOIN Silver.Dim_Turno_Catalogo tc ON tc.ID_Turno_Catalogo = g.ID_Turno_Catalogo
                JOIN Silver.Dim_Valvula_Catalogo vc ON vc.ID_Valvula_Catalogo = g.ID_Valvula_Catalogo
                WHERE ISNULL(g.Es_Vigente, 1) = 1
                  AND ISNULL(g.Es_Test_Block, 0) = 0
                  AND mc.Modulo = @Modulo_Int
                  AND ISNULL(mc.SubModulo, -1) = ISNULL(@SubModulo_Int, -1)
                  AND tc.Turno = @Turno_Int
                  AND g.ID_Cama_Catalogo = @ID_Cama_Catalogo
                  AND (
                        CASE
                            WHEN vc.Valvula IS NULL THEN NULL
                            WHEN LTRIM(RTRIM(vc.Valvula)) = '' THEN NULL
                            WHEN LTRIM(RTRIM(vc.Valvula)) NOT LIKE '%[^0-9]%'
                                THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(vc.Valvula))))
                            ELSE LTRIM(RTRIM(vc.Valvula))
                        END
                      ) = @Valvula_Token
            )
            SELECT
                @Coincidencias_Geo = COUNT(*),
                @ID_Geografia = MIN(ID_Geografia)
            FROM Geo;

            IF @Coincidencias_Geo = 1
            BEGIN
                IF @ID_Cama_Catalogo = 0
                BEGIN
                    SET @Estado_Resolucion = 'RESUELTA_BASE_SIN_CAMA';
                    SET @Detalle = 'Geografia resuelta sin cama especifica.';
                END
                ELSE
                BEGIN
                    SET @Estado_Resolucion = 'RESUELTA_BASE_Y_CAMA';
                    SET @Detalle = 'Geografia y cama resueltas.';
                END
            END
            ELSE IF @Coincidencias_Geo = 0
            BEGIN
                SET @Estado_Resolucion = 'GEOGRAFIA_NO_ENCONTRADA';
                SET @Detalle = 'No existe combinacion vigente para modulo/submodulo/turno/valvula/cama.';
            END
            ELSE
            BEGIN
                SET @Estado_Resolucion = 'GEOGRAFIA_AMBIGUA';
                SET @Detalle = 'Existe mas de una combinacion vigente para modulo/submodulo/turno/valvula/cama.';
                SET @ID_Geografia = NULL;
            END
        END
    END

    SELECT
        @Modulo_Token AS Modulo_Token,
        @Turno_Token AS Turno_Token,
        @Valvula_Token AS Valvula_Token,
        @Cama_Token AS Cama_Token,
        @Modulo_Int AS Modulo_Int,
        @SubModulo_Int AS SubModulo_Int,
        @Turno_Int AS Turno_Int,
        @Cama_Int AS Cama_Int,
        @ID_Geografia AS ID_Geografia,
        @ID_Cama_Catalogo AS ID_Cama_Catalogo,
        @Estado_Resolucion AS Estado_Resolucion,
        @Detalle AS Detalle;
END;
GO

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Modificar Silver.sp_Upsert_Cama_Desde_Bronce
-- ─────────────────────────────────────────────────────────────────────────────
PRINT 'Actualizando Silver.sp_Upsert_Cama_Desde_Bronce...';
GO
CREATE OR ALTER PROCEDURE Silver.sp_Upsert_Cama_Desde_Bronce
    @Modo_Aplicar       BIT = 0,
    @Cama_Min_Permitida INT = 1,
    @Cama_Max_Permitida INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    IF OBJECT_ID('Silver.Dim_Cama_Catalogo', 'U') IS NULL
    BEGIN
        RAISERROR('No existe Silver.Dim_Cama_Catalogo.', 16, 1);
        RETURN;
    END;

    IF OBJECT_ID('Bronce.Evaluacion_Pesos', 'U') IS NULL
       OR OBJECT_ID('Bronce.Evaluacion_Vegetativa', 'U') IS NULL
    BEGIN
        RAISERROR('No existen tablas Bronce requeridas.', 16, 1);
        RETURN;
    END;

    IF OBJECT_ID('tempdb..#BronceRaw') IS NOT NULL DROP TABLE #BronceRaw;
    IF OBJECT_ID('tempdb..#Eval')      IS NOT NULL DROP TABLE #Eval;
    IF OBJECT_ID('tempdb..#Aptos')     IS NOT NULL DROP TABLE #Aptos;

    -- ── 1. Leer último lote de cada fuente Bronce ─────────────────────────────
    CREATE TABLE #BronceRaw (
        Tabla_Origen NVARCHAR(50)  NOT NULL,
        Modulo_Raw   NVARCHAR(100) NULL,
        Turno_Raw    NVARCHAR(100) NULL,
        Valvula_Raw  NVARCHAR(100) NULL,
        Cama_Raw     NVARCHAR(100) NULL
    );

    ;WITH LotePesos AS (
        SELECT TOP (1) Fecha_Sistema, Nombre_Archivo
        FROM Bronce.Evaluacion_Pesos
        ORDER BY Fecha_Sistema DESC, ID_Evaluacion_Pesos DESC
    )
    INSERT INTO #BronceRaw (Tabla_Origen, Modulo_Raw, Turno_Raw, Valvula_Raw, Cama_Raw)
    SELECT 'Bronce.Evaluacion_Pesos', p.Modulo_Raw, p.Turno_Raw, p.Valvula_Raw, p.Cama_Raw
    FROM Bronce.Evaluacion_Pesos p
    INNER JOIN LotePesos l ON p.Fecha_Sistema = l.Fecha_Sistema
                          AND p.Nombre_Archivo = l.Nombre_Archivo;

    ;WITH LoteVeg AS (
        SELECT TOP (1) Fecha_Sistema, Nombre_Archivo
        FROM Bronce.Evaluacion_Vegetativa
        ORDER BY Fecha_Sistema DESC, ID_Evaluacion_Veg DESC
    )
    INSERT INTO #BronceRaw (Tabla_Origen, Modulo_Raw, Turno_Raw, Valvula_Raw, Cama_Raw)
    SELECT 'Bronce.Evaluacion_Vegetativa', v.Modulo_Raw, v.Turno_Raw, v.Valvula_Raw, v.Cama_Raw
    FROM Bronce.Evaluacion_Vegetativa v
    INNER JOIN LoteVeg l ON v.Fecha_Sistema = l.Fecha_Sistema
                        AND v.Nombre_Archivo = l.Nombre_Archivo;

    -- ── 2. Resolver geografía por fila ────────────────────────────────────────
    CREATE TABLE #Eval (
        Estado_Resolucion NVARCHAR(50) NOT NULL,
        ID_Geografia      INT          NULL,
        Cama_Int          INT          NULL
    );

    INSERT INTO #Eval (Estado_Resolucion, ID_Geografia, Cama_Int)
    SELECT
        CASE
            WHEN x.Es_Modulo_Especial = 1                                                        THEN 'CASO_ESPECIAL_MODULO'
            WHEN x.Modulo_Int IS NULL OR x.Turno_Int IS NULL OR x.Valvula_Token IS NULL          THEN 'CLAVE_GEOGRAFICA_INCOMPLETA'
            WHEN x.Cama_Int IS NULL
              OR x.Cama_Int < @Cama_Min_Permitida
              OR x.Cama_Int > @Cama_Max_Permitida                                                THEN 'CAMA_NO_VALIDA'
            WHEN x.Coincidencias_Geo = 0                                                         THEN 'GEOGRAFIA_NO_ENCONTRADA'
            WHEN x.Coincidencias_Geo > 1                                                         THEN 'GEOGRAFIA_AMBIGUA'
            ELSE 'APTO_PARA_INSERT'
        END AS Estado_Resolucion,
        CASE WHEN x.Coincidencias_Geo = 1 THEN x.ID_Geografia_Unica ELSE NULL END AS ID_Geografia,
        x.Cama_Int
    FROM (
        SELECT
            t.Modulo_Int,
            t.SubModulo_Int,
            t.Turno_Int,
            t.Valvula_Token,
            t.Cama_Int,
            t.Es_Modulo_Especial,
            g.Coincidencias_Geo,
            g.ID_Geografia_Unica
        FROM #BronceRaw r
        CROSS APPLY (
            SELECT
                NULLIF(LTRIM(RTRIM(r.Modulo_Raw)),  '') AS Modulo_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Turno_Raw)),   '') AS Turno_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Valvula_Raw)), '') AS Valvula_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Cama_Raw)),    '') AS Cama_Token_Raw
        ) raw
        OUTER APPLY (
            SELECT TOP (1)
                rr.Modulo_Int,
                rr.SubModulo_Int,
                ISNULL(rr.Es_Test_Block, 0) AS Es_Test_Block_Regla
            FROM MDM.Regla_Modulo_Raw rr
            WHERE rr.Es_Activa = 1
              AND raw.Modulo_Token_Raw IS NOT NULL
              AND UPPER(LTRIM(RTRIM(rr.Modulo_Raw))) = UPPER(raw.Modulo_Token_Raw)
        ) regla
        CROSS APPLY (
            SELECT
                CASE WHEN raw.Turno_Token_Raw IS NULL   THEN NULL
                     WHEN raw.Turno_Token_Raw   NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Turno_Token_Raw)
                     ELSE NULL END AS Turno_Int,
                CASE WHEN raw.Valvula_Token_Raw IS NULL THEN NULL
                     WHEN raw.Valvula_Token_Raw NOT LIKE '%[^0-9]%' THEN CONVERT(NVARCHAR(50), CONVERT(INT, raw.Valvula_Token_Raw))
                     ELSE raw.Valvula_Token_Raw END AS Valvula_Token,
                CASE WHEN raw.Cama_Token_Raw IS NULL    THEN NULL
                     WHEN raw.Cama_Token_Raw    NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Cama_Token_Raw)
                     ELSE NULL END AS Cama_Int,
                CASE WHEN raw.Modulo_Token_Raw IS NOT NULL
                      AND raw.Modulo_Token_Raw NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Modulo_Token_Raw)
                     ELSE NULL END AS Modulo_Int_Raw
        ) base
        CROSS APPLY (
            SELECT
                COALESCE(regla.Modulo_Int, base.Modulo_Int_Raw)   AS Modulo_Int,
                regla.SubModulo_Int                                AS SubModulo_Int,
                CASE
                    WHEN ISNULL(regla.Es_Test_Block_Regla, 0) = 1           THEN 1
                    WHEN COALESCE(regla.Modulo_Int, base.Modulo_Int_Raw) IS NULL THEN 1
                    ELSE 0
                END AS Es_Modulo_Especial,
                base.Turno_Int,
                base.Valvula_Token,
                base.Cama_Int
        ) t
        OUTER APPLY (
            SELECT
                COUNT(*)          AS Coincidencias_Geo,
                MIN(gv.ID_Geografia) AS ID_Geografia_Unica
            FROM Silver.Dim_Geografia      gv
            JOIN Silver.Dim_Modulo_Catalogo  mc ON mc.ID_Modulo_Catalogo  = gv.ID_Modulo_Catalogo
            JOIN Silver.Dim_Turno_Catalogo   tc ON tc.ID_Turno_Catalogo   = gv.ID_Turno_Catalogo
            JOIN Silver.Dim_Valvula_Catalogo vc ON vc.ID_Valvula_Catalogo = gv.ID_Valvula_Catalogo
            WHERE ISNULL(gv.Es_Vigente,    1) = 1
              AND ISNULL(gv.Es_Test_Block,  0) = 0
              -- Filtramos por el registro base de la válvula (Cama = 0)
              AND gv.ID_Cama_Catalogo            = 0
              AND mc.Modulo                      = t.Modulo_Int
              AND ISNULL(mc.SubModulo, -1)       = ISNULL(t.SubModulo_Int, -1)
              AND tc.Turno                       = t.Turno_Int
              AND (
                    CASE
                        WHEN LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula))) = ''   THEN NULL
                        WHEN LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula))) NOT LIKE '%[^0-9]%'
                            THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula)))))
                        ELSE LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula)))
                    END
                  ) = t.Valvula_Token
        ) g
    ) x;

    -- ── 3. Filtrar aptos ──────────────────────────────────────────────────────
    CREATE TABLE #Aptos (
        ID_Geografia    INT          NOT NULL,
        Cama_Normalizada NVARCHAR(50) NOT NULL,
        CONSTRAINT PK_Aptos PRIMARY KEY (ID_Geografia, Cama_Normalizada)
    );

    INSERT INTO #Aptos (ID_Geografia, Cama_Normalizada)
    SELECT DISTINCT
        e.ID_Geografia,
        CONVERT(NVARCHAR(50), e.Cama_Int)
    FROM #Eval e
    WHERE e.Estado_Resolucion = 'APTO_PARA_INSERT'
      AND e.ID_Geografia IS NOT NULL
      AND e.Cama_Int BETWEEN @Cama_Min_Permitida AND @Cama_Max_Permitida;

    -- ── 4. Aplicar (solo si @Modo_Aplicar = 1) ────────────────────────────────
    DECLARE
        @Insert_Catalogo_Real INT = 0,
        @Insert_Bridge_Real   INT = 0; -- Mantenemos por compatibilidad de firma de salida

    IF @Modo_Aplicar = 1
    BEGIN
        BEGIN TRANSACTION;

        -- A. Sincronizar catálogo de camas
        INSERT INTO Silver.Dim_Cama_Catalogo (Cama_Normalizada)
        SELECT DISTINCT a.Cama_Normalizada
        FROM #Aptos a
        WHERE NOT EXISTS (
            SELECT 1 FROM Silver.Dim_Cama_Catalogo c
            WHERE c.Cama_Normalizada = a.Cama_Normalizada
        );
        SET @Insert_Catalogo_Real = @@ROWCOUNT;

        -- B. Crear combinaciones de granularidad de cama directo en Dim_Geografia
        INSERT INTO Silver.Dim_Geografia (
            ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
            ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
            Es_Test_Block, Nivel_Granularidad, Fecha_Inicio_Vigencia, Es_Vigente
        )
        SELECT DISTINCT
            gv.ID_Fundo_Catalogo, gv.ID_Sector_Catalogo, gv.ID_Modulo_Catalogo,
            gv.ID_Turno_Catalogo, gv.ID_Valvula_Catalogo, c.ID_Cama_Catalogo,
            gv.Es_Test_Block, 'AUTO_SP_CAMA', CAST(GETDATE() AS DATE), 1
        FROM #Aptos a
        INNER JOIN Silver.Dim_Geografia gv ON gv.ID_Geografia = a.ID_Geografia
        INNER JOIN Silver.Dim_Cama_Catalogo c ON c.Cama_Normalizada = a.Cama_Normalizada
        WHERE NOT EXISTS (
            SELECT 1 FROM Silver.Dim_Geografia g2
            WHERE g2.ID_Fundo_Catalogo   = gv.ID_Fundo_Catalogo
              AND g2.ID_Sector_Catalogo  = gv.ID_Sector_Catalogo
              AND g2.ID_Modulo_Catalogo  = gv.ID_Modulo_Catalogo
              AND g2.ID_Turno_Catalogo   = gv.ID_Turno_Catalogo
              AND g2.ID_Valvula_Catalogo = gv.ID_Valvula_Catalogo
              AND g2.ID_Cama_Catalogo    = c.ID_Cama_Catalogo
              AND g2.Es_Vigente          = 1
        );
        SET @Insert_Bridge_Real = @@ROWCOUNT; -- Reutilizamos esta métrica para reportar inserciones en Dim_Geografia

        COMMIT TRANSACTION;
    END;

    -- ── 5. Resultados ─────────────────────────────────────────────────────────
    SELECT
        @Modo_Aplicar                           AS Modo_Aplicar,
        (SELECT COUNT(*) FROM #BronceRaw)       AS Filas_Bronce_Leidas,
        (SELECT COUNT(*) FROM #Eval)            AS Filas_Evaluadas,
        (SELECT COUNT(*) FROM #Aptos)           AS Combinaciones_Aptas_Distintas,
        @Insert_Catalogo_Real                   AS Insert_Catalogo_Real,
        @Insert_Bridge_Real                     AS Insert_Bridge_Real; -- Representa filas insertadas en Dim_Geografia

    SELECT Estado_Resolucion, COUNT(*) AS Filas
    FROM #Eval
    GROUP BY Estado_Resolucion
    ORDER BY COUNT(*) DESC;
END;
GO

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Modificar Silver.sp_Validar_Calidad_Camas
-- ─────────────────────────────────────────────────────────────────────────────
PRINT 'Actualizando Silver.sp_Validar_Calidad_Camas...';
GO
CREATE OR ALTER PROCEDURE Silver.sp_Validar_Calidad_Camas
    @Cama_Max_Permitida INT = 100,
    @Max_Camas_Por_Geografia INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    -- 1. Regla 1: Camas fuera de rango (ej. Cama 150)
    DECLARE @Cama_Fuera_Regla INT = 0;
    
    SELECT @Cama_Fuera_Regla = COUNT(DISTINCT g.ID_Cama_Catalogo)
    FROM Silver.Dim_Geografia g
    INNER JOIN Silver.Dim_Cama_Catalogo c ON g.ID_Cama_Catalogo = c.ID_Cama_Catalogo
    WHERE g.Es_Vigente = 1
      AND g.ID_Cama_Catalogo <> 0
      AND (
            CASE WHEN c.Cama_Normalizada NOT LIKE '%[^0-9]%' 
                 THEN CONVERT(INT, c.Cama_Normalizada)
                 ELSE 9999 -- Ignorar no numéricas para esta regla
            END
          ) > @Cama_Max_Permitida;

    -- 2. Regla 2: Saturación (más de N camas en una sola válvula/geología)
    DECLARE @Geografias_Saturadas INT = 0;
    
    SELECT @Geografias_Saturadas = COUNT(*)
    FROM (
        SELECT g.ID_Fundo_Catalogo, g.ID_Sector_Catalogo, g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo, COUNT(DISTINCT g.ID_Cama_Catalogo) as Cantidad_Camas
        FROM Silver.Dim_Geografia g
        WHERE g.Es_Vigente = 1
          AND g.ID_Cama_Catalogo <> 0
        GROUP BY g.ID_Fundo_Catalogo, g.ID_Sector_Catalogo, g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo
        HAVING COUNT(DISTINCT g.ID_Cama_Catalogo) > @Max_Camas_Por_Geografia
    ) Sat;

    -- 3. Calcular Estado final
    DECLARE @Estado NVARCHAR(50) = 'APROBADO';
    IF @Cama_Fuera_Regla > 0 OR @Geografias_Saturadas > 0
    BEGIN
        SET @Estado = 'RIESGO_CONTAMINACION';
    END;

    -- Retornar resultado como una única fila
    SELECT 
        @Cama_Fuera_Regla AS Cama_Fuera_Regla,
        @Geografias_Saturadas AS Geografias_Saturadas,
        @Estado AS Estado_Calidad_Cama;
END;
GO

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Eliminar Silver.Bridge_Geografia_Cama
-- ─────────────────────────────────────────────────────────────────────────────
PRINT 'Eliminando Silver.Bridge_Geografia_Cama...';
GO
IF OBJECT_ID('Silver.Bridge_Geografia_Cama', 'U') IS NOT NULL
BEGIN
    DROP TABLE Silver.Bridge_Geografia_Cama;
    PRINT 'Tabla Silver.Bridge_Geografia_Cama eliminada exitosamente.';
END
ELSE
BEGIN
    PRINT 'La tabla Silver.Bridge_Geografia_Cama ya no existe.';
END
GO
