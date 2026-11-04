-- =============================================================================
-- FASE 25: Versionado DDL — Arquitectura de Catálogos Geográficos
-- Captura el esquema que ya existe en producción/dev.
-- Este script es IDEMPOTENTE: usa IF NOT EXISTS en cada objeto.
-- NO modifica datos ni renombra tablas existentes.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Catálogo de Fundos
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Fundo_Catalogo'
)
BEGIN
    CREATE TABLE Silver.Dim_Fundo_Catalogo (
        ID_Fundo_Catalogo   INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        Fundo               NVARCHAR(200) NOT NULL,
        Es_Activa           BIT           NOT NULL DEFAULT 1,
        Fecha_Creacion      DATETIME2     NULL     DEFAULT SYSDATETIME(),
        Fecha_Modificacion  DATETIME2     NULL
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Catálogo de Sectores
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Sector_Catalogo'
)
BEGIN
    CREATE TABLE Silver.Dim_Sector_Catalogo (
        ID_Sector_Catalogo  INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        Sector              NVARCHAR(200) NOT NULL,
        Es_Activa           BIT           NOT NULL DEFAULT 1,
        Fecha_Creacion      DATETIME2     NULL     DEFAULT SYSDATETIME(),
        Fecha_Modificacion  DATETIME2     NULL
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Catálogo de Módulos (absorbe SubModulo y Tipo_Conduccion como columnas)
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Modulo_Catalogo'
)
BEGIN
    CREATE TABLE Silver.Dim_Modulo_Catalogo (
        ID_Modulo_Catalogo  INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        Modulo              INT           NOT NULL,
        SubModulo           INT           NULL,
        Tipo_Conduccion     NVARCHAR(100) NULL,
        Es_Activa           BIT           NOT NULL DEFAULT 1,
        Fecha_Creacion      DATETIME2     NULL     DEFAULT SYSDATETIME(),
        Fecha_Modificacion  DATETIME2     NULL
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Catálogo de Turnos
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Turno_Catalogo'
)
BEGIN
    CREATE TABLE Silver.Dim_Turno_Catalogo (
        ID_Turno_Catalogo   INT  NOT NULL IDENTITY(1,1) PRIMARY KEY,
        Turno               INT  NOT NULL,
        Es_Activa           BIT  NOT NULL DEFAULT 1,
        Fecha_Creacion      DATETIME2 NULL DEFAULT SYSDATETIME(),
        Fecha_Modificacion  DATETIME2 NULL
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Catálogo de Válvulas
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Valvula_Catalogo'
)
BEGIN
    CREATE TABLE Silver.Dim_Valvula_Catalogo (
        ID_Valvula_Catalogo INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        Valvula             NVARCHAR(100) NOT NULL,
        Es_Activa           BIT           NOT NULL DEFAULT 1,
        Fecha_Creacion      DATETIME2     NULL     DEFAULT SYSDATETIME(),
        Fecha_Modificacion  DATETIME2     NULL
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Catálogo de Camas (Cama_Normalizada es el texto canónico, p.ej. '7')
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Cama_Catalogo'
)
BEGIN
    CREATE TABLE Silver.Dim_Cama_Catalogo (
        ID_Cama_Catalogo    INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        Cama_Normalizada    NVARCHAR(100) NOT NULL,
        Es_Activa           BIT           NOT NULL DEFAULT 1,
        Fecha_Creacion      DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
        Fecha_Modificacion  DATETIME2     NULL
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Dimensión principal normalizada (Junk Dimension con FKs a catálogos)
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Dim_Geografia_Nueva'
)
BEGIN
    CREATE TABLE Silver.Dim_Geografia_Nueva (
        ID_Geografia         INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        ID_Fundo_Catalogo    INT           NOT NULL,
        ID_Sector_Catalogo   INT           NOT NULL,
        ID_Modulo_Catalogo   INT           NOT NULL,
        ID_Turno_Catalogo    INT           NOT NULL,
        ID_Valvula_Catalogo  INT           NOT NULL,
        ID_Cama_Catalogo     INT           NOT NULL,
        Es_Test_Block        BIT           NOT NULL DEFAULT 0,
        Codigo_SAP_Campo     NVARCHAR(100) NULL,
        Nivel_Granularidad   VARCHAR(50)   NOT NULL,
        Fecha_Inicio_Vigencia DATE          NOT NULL,
        Fecha_Fin_Vigencia   DATE          NULL,
        Es_Vigente           BIT           NOT NULL DEFAULT 1,

        CONSTRAINT FK_DimGeoNueva_Fundo
            FOREIGN KEY (ID_Fundo_Catalogo)   REFERENCES Silver.Dim_Fundo_Catalogo   (ID_Fundo_Catalogo),
        CONSTRAINT FK_DimGeoNueva_Sector
            FOREIGN KEY (ID_Sector_Catalogo)  REFERENCES Silver.Dim_Sector_Catalogo  (ID_Sector_Catalogo),
        CONSTRAINT FK_DimGeoNueva_Modulo
            FOREIGN KEY (ID_Modulo_Catalogo)  REFERENCES Silver.Dim_Modulo_Catalogo  (ID_Modulo_Catalogo),
        CONSTRAINT FK_DimGeoNueva_Turno
            FOREIGN KEY (ID_Turno_Catalogo)   REFERENCES Silver.Dim_Turno_Catalogo   (ID_Turno_Catalogo),
        CONSTRAINT FK_DimGeoNueva_Valvula
            FOREIGN KEY (ID_Valvula_Catalogo) REFERENCES Silver.Dim_Valvula_Catalogo (ID_Valvula_Catalogo),
        CONSTRAINT FK_DimGeoNueva_Cama
            FOREIGN KEY (ID_Cama_Catalogo)    REFERENCES Silver.Dim_Cama_Catalogo    (ID_Cama_Catalogo)
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. Bridge Geografía–Cama (relación N:M vigente entre geografía y camas)
--    Columnas inferidas del uso en sp_Resolver_Geografia_Cama.
--    COMPLETAR con las columnas reales una vez ejecutada la Query 3 del plan.
-- ─────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Bridge_Geografia_Cama'
)
BEGIN
    CREATE TABLE Silver.Bridge_Geografia_Cama (
        ID_Bridge_Geografia_Cama BIGINT        NOT NULL IDENTITY(1,1) PRIMARY KEY,
        ID_Geografia             INT           NOT NULL,
        ID_Cama_Catalogo         INT           NOT NULL,
        Fecha_Inicio_Vigencia    DATE          NOT NULL,
        Fecha_Fin_Vigencia       DATE          NULL,
        Es_Vigente               BIT           NOT NULL DEFAULT 1,
        Fuente_Registro          NVARCHAR(100) NOT NULL,
        Observacion              NVARCHAR(600) NULL,

        CONSTRAINT FK_BridgeGeoCama_Geo
            FOREIGN KEY (ID_Geografia)     REFERENCES Silver.Dim_Geografia_Nueva (ID_Geografia),
        CONSTRAINT FK_BridgeGeoCama_Cama
            FOREIGN KEY (ID_Cama_Catalogo) REFERENCES Silver.Dim_Cama_Catalogo   (ID_Cama_Catalogo)
    );
END;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. SP: sp_Resolver_Geografia_Cama
--    Se crea solo si no existe; el cuerpo completo está abajo.
--    Si ya existe en la DB, este bloque es NO-OP.
-- ─────────────────────────────────────────────────────────────────────────────
IF OBJECT_ID('Silver.sp_Resolver_Geografia_Cama', 'P') IS NULL
BEGIN
    EXEC(N'
CREATE PROCEDURE Silver.sp_Resolver_Geografia_Cama
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
        @ID_Cama_Catalogo INT = NULL,
        @Estado_Resolucion NVARCHAR(50),
        @Detalle NVARCHAR(300),
        @Tipo_Conduccion_Regla NVARCHAR(50) = NULL,
        @Prioridad_Regla INT = NULL;

    SELECT
        @Modulo_Token = NULLIF(LTRIM(RTRIM(@Modulo_Raw)), ''''),
        @Turno_Token = NULLIF(LTRIM(RTRIM(@Turno_Raw)), ''''),
        @Valvula_Token = NULLIF(LTRIM(RTRIM(@Valvula_Raw)), ''''),
        @Cama_Token = NULLIF(LTRIM(RTRIM(@Cama_Raw)), '''');

    IF @Modulo_Token IS NOT NULL AND @Modulo_Token NOT LIKE ''%[^0-9]%''
        SET @Modulo_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Modulo_Token));

    IF @Turno_Token IS NOT NULL AND @Turno_Token NOT LIKE ''%[^0-9]%''
        SET @Turno_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Turno_Token));

    IF @Valvula_Token IS NOT NULL AND @Valvula_Token NOT LIKE ''%[^0-9]%''
        SET @Valvula_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Valvula_Token));

    IF @Cama_Token IS NOT NULL AND @Cama_Token NOT LIKE ''%[^0-9]%''
        SET @Cama_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Cama_Token));

    IF @Turno_Token IS NOT NULL AND @Turno_Token NOT LIKE ''%[^0-9]%''
        SET @Turno_Int = CONVERT(INT, @Turno_Token);

    IF @Cama_Token IS NOT NULL AND @Cama_Token NOT LIKE ''%[^0-9]%''
        SET @Cama_Int = CONVERT(INT, @Cama_Token);

    IF OBJECT_ID(''MDM.Regla_Modulo_Raw'', ''U'') IS NOT NULL
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
       AND OBJECT_ID(''MDM.Regla_Modulo_Turno_SubModulo'', ''U'') IS NOT NULL
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
       AND @Modulo_Token NOT LIKE ''%[^0-9]%''
    BEGIN
        SET @Modulo_Int = CONVERT(INT, @Modulo_Token);
    END;

    IF @Es_Test_Block_Regla = 1
    BEGIN
        IF @Turno_Int IS NULL OR @Valvula_Token IS NULL
        BEGIN
            SET @Estado_Resolucion = ''CLAVE_GEOGRAFICA_INCOMPLETA'';
            SET @Detalle = ''Test block sin turno o valvula.'';
        END
        ELSE
        BEGIN
            ;WITH GeoTB AS (
                SELECT g.ID_Geografia
                FROM Silver.Dim_Geografia g
                WHERE ISNULL(g.Es_Vigente, 1) = 1
                  AND ISNULL(g.Es_Test_Block, 0) = 1
                  AND g.Turno = @Turno_Int
                  AND (
                        CASE
                            WHEN g.Valvula IS NULL THEN NULL
                            WHEN LTRIM(RTRIM(g.Valvula)) = '''' THEN NULL
                            WHEN LTRIM(RTRIM(g.Valvula)) NOT LIKE ''%[^0-9]%''
                                THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(g.Valvula))))
                            ELSE LTRIM(RTRIM(g.Valvula))
                        END
                      ) = @Valvula_Token
            )
            SELECT
                @Coincidencias_Geo = COUNT(*),
                @ID_Geografia = MIN(ID_Geografia)
            FROM GeoTB;

            IF @Coincidencias_Geo = 1
            BEGIN
                SET @Estado_Resolucion = ''RESUELTA_TEST_BLOCK'';
                SET @Detalle = ''Test block resuelto por Turno/Valvula.'';
            END
            ELSE IF @Coincidencias_Geo = 0
            BEGIN
                SET @Estado_Resolucion = ''TEST_BLOCK_NO_MAPEADO'';
                SET @Detalle = ''No existe geografia test block para Turno/Valvula.'';
                SET @ID_Geografia = NULL;
            END
            ELSE
            BEGIN
                SET @Estado_Resolucion = ''TEST_BLOCK_AMBIGUO'';
                SET @Detalle = ''Mas de una geografia test block para Turno/Valvula.'';
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
        SET @Estado_Resolucion = ''CASO_ESPECIAL_MODULO'';
        SET @Detalle = ''Modulo especial (sin regla operativa).'';
    END
    ELSE IF @Turno_Int IS NULL OR @Valvula_Token IS NULL
    BEGIN
        SET @Estado_Resolucion = ''CLAVE_GEOGRAFICA_INCOMPLETA'';
        SET @Detalle = ''Falta turno o valvula.'';
    END
    ELSE
    BEGIN
        ;WITH Geo AS (
            SELECT g.ID_Geografia
            FROM Silver.Dim_Geografia g
            WHERE ISNULL(g.Es_Vigente, 1) = 1
              AND ISNULL(g.Es_Test_Block, 0) = 0
              AND g.Modulo = @Modulo_Int
              AND ISNULL(g.SubModulo, -1) = ISNULL(@SubModulo_Int, -1)
              AND g.Turno = @Turno_Int
              AND (
                    CASE
                        WHEN g.Valvula IS NULL THEN NULL
                        WHEN LTRIM(RTRIM(g.Valvula)) = '''' THEN NULL
                        WHEN LTRIM(RTRIM(g.Valvula)) NOT LIKE ''%[^0-9]%''
                            THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(g.Valvula))))
                        ELSE LTRIM(RTRIM(g.Valvula))
                    END
                  ) = @Valvula_Token
        )
        SELECT
            @Coincidencias_Geo = COUNT(*),
            @ID_Geografia = MIN(ID_Geografia)
        FROM Geo;

        IF @Coincidencias_Geo = 0
        BEGIN
            SET @Estado_Resolucion = ''GEOGRAFIA_NO_ENCONTRADA'';
            SET @Detalle = ''No existe geografia vigente para modulo/submodulo/turno/valvula.'';
        END
        ELSE IF @Coincidencias_Geo > 1
        BEGIN
            SET @Estado_Resolucion = ''GEOGRAFIA_AMBIGUA'';
            SET @Detalle = ''Existe mas de una geografia vigente para modulo/submodulo/turno/valvula.'';
            SET @ID_Geografia = NULL;
        END
        ELSE
        BEGIN
            IF @Cama_Token IS NULL OR @Cama_Token = ''0''
            BEGIN
                SET @Estado_Resolucion = ''RESUELTA_BASE_SIN_CAMA'';
                SET @Detalle = ''Geografia resuelta sin cama especifica.'';
            END
            ELSE IF @Cama_Int IS NULL OR @Cama_Int < @Cama_Min_Permitida OR @Cama_Int > @Cama_Max_Permitida
            BEGIN
                SET @Estado_Resolucion = ''CAMA_NO_VALIDA'';
                SET @Detalle = ''Cama fuera de rango permitido.'';
            END
            ELSE
            BEGIN
                SELECT
                    @ID_Cama_Catalogo = c.ID_Cama_Catalogo
                FROM Silver.Dim_Cama_Catalogo c
                WHERE c.Es_Activa = 1
                  AND c.Cama_Normalizada = CONVERT(NVARCHAR(50), @Cama_Int);

                IF @ID_Cama_Catalogo IS NULL
                BEGIN
                    SET @Estado_Resolucion = ''CAMA_NO_CATALOGO'';
                    SET @Detalle = ''Cama valida, pero no existe en catalogo.'';
                END
                ELSE IF EXISTS (
                    SELECT 1
                    FROM Silver.Bridge_Geografia_Cama b
                    WHERE b.ID_Geografia = @ID_Geografia
                      AND b.ID_Cama_Catalogo = @ID_Cama_Catalogo
                      AND b.Es_Vigente = 1
                      AND b.Fecha_Fin_Vigencia IS NULL
                )
                BEGIN
                    SET @Estado_Resolucion = ''RESUELTA_BASE_Y_CAMA'';
                    SET @Detalle = ''Geografia y cama resueltas.'';
                END
                ELSE
                BEGIN
                    SET @Estado_Resolucion = ''CAMA_NO_RELACION'';
                    SET @Detalle = ''Cama existe en catalogo, pero no esta relacionada a la geografia.'';
                END
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
');
END;
