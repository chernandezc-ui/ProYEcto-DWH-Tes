/* ============================================================================
   FASE 40 — Cuarentena estricta para Dims (Geografia, Variedad, Personal)
   ============================================================================

   Objetivo: convertir las Dims en fuente de verdad y reemplazar el auto-create
   silente del MDM por un flujo de "cuarentena -> revision humana -> promocion".

   Activable por flag Config.Parametros_Pipeline.MDM_MODO_ESTRICTO = 'ON'
   (default OFF para no romper produccion).

   Artefactos creados:
   - MDM.Cuarentena_Geografia (tupla completa, estado, aprobacion)
   - MDM.Cuarentena_Variedad
   - MDM.Cuarentena_Personal
   - SP MDM.usp_Aprobar_Geografia
   - SP MDM.usp_Aprobar_Variedad
   - SP MDM.usp_Aprobar_Personal
   - Vista MDM.vw_Cuarentena_Pendiente
   - Parametro Config: MDM_MODO_ESTRICTO

   Idempotente: usa IF NOT EXISTS / OR ALTER. Re-ejecutable sin error.
   ============================================================================ */

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- ===========================================================================
-- 1. MDM.Cuarentena_Geografia
-- ===========================================================================
IF OBJECT_ID(N'MDM.Cuarentena_Geografia', N'U') IS NULL
BEGIN
    CREATE TABLE MDM.Cuarentena_Geografia (
        ID_Cuarentena_Geo   BIGINT          IDENTITY(1,1) PRIMARY KEY,
        Fundo               NVARCHAR(100)   NULL,
        Sector              NVARCHAR(100)   NULL,
        Modulo              NVARCHAR(50)    NULL,
        Turno               NVARCHAR(50)    NULL,
        Valvula             NVARCHAR(50)    NULL,
        Cama                NVARCHAR(50)    NULL,
        Origen_Tabla        NVARCHAR(100)   NOT NULL,
        Origen_Archivo      NVARCHAR(300)   NULL,
        Veces_Visto         INT             NOT NULL DEFAULT 1,
        Fecha_Primera_Vez   DATETIME2       NOT NULL DEFAULT GETDATE(),
        Fecha_Ultima_Vez    DATETIME2       NOT NULL DEFAULT GETDATE(),
        -- Workflow de aprobacion
        Estado              NVARCHAR(20)    NOT NULL DEFAULT 'PENDIENTE',
            -- PENDIENTE / APROBADO / RECHAZADO / FUSIONADO
        ID_Geografia_Sugerido INT           NULL,
            -- Si Estado=FUSIONADO, apunta al ID_Geografia que el aprobador eligio
        Aprobado_Por        NVARCHAR(50)    NULL,
        Fecha_Resolucion    DATETIME2       NULL,
        Nota_Aprobador      NVARCHAR(500)   NULL
    );

    CREATE UNIQUE INDEX UX_Cuarentena_Geo_Tupla
        ON MDM.Cuarentena_Geografia (
            Fundo, Sector, Modulo, Turno, Valvula, Cama
        )
        WHERE Estado = 'PENDIENTE';

    CREATE INDEX IX_Cuarentena_Geo_Estado
        ON MDM.Cuarentena_Geografia (Estado, Fecha_Ultima_Vez DESC);
END
GO


-- ===========================================================================
-- 2. MDM.Cuarentena_Variedad
-- ===========================================================================
IF OBJECT_ID(N'MDM.Cuarentena_Variedad', N'U') IS NULL
BEGIN
    CREATE TABLE MDM.Cuarentena_Variedad (
        ID_Cuarentena_Var   BIGINT          IDENTITY(1,1) PRIMARY KEY,
        Nombre_Recibido     NVARCHAR(200)   NOT NULL,
        Nombre_Normalizado  NVARCHAR(200)   NULL,
        Origen_Tabla        NVARCHAR(100)   NOT NULL,
        Origen_Archivo      NVARCHAR(300)   NULL,
        Veces_Visto         INT             NOT NULL DEFAULT 1,
        Fecha_Primera_Vez   DATETIME2       NOT NULL DEFAULT GETDATE(),
        Fecha_Ultima_Vez    DATETIME2       NOT NULL DEFAULT GETDATE(),
        -- Workflow
        Estado              NVARCHAR(20)    NOT NULL DEFAULT 'PENDIENTE',
        ID_Variedad_Sugerido INT            NULL,
        Score_Levenshtein   DECIMAL(5,4)    NULL,
        Aprobado_Por        NVARCHAR(50)    NULL,
        Fecha_Resolucion    DATETIME2       NULL,
        Nota_Aprobador      NVARCHAR(500)   NULL
    );

    CREATE UNIQUE INDEX UX_Cuarentena_Var_Nombre
        ON MDM.Cuarentena_Variedad (Nombre_Normalizado)
        WHERE Estado = 'PENDIENTE';

    CREATE INDEX IX_Cuarentena_Var_Estado
        ON MDM.Cuarentena_Variedad (Estado, Fecha_Ultima_Vez DESC);
END
GO


-- ===========================================================================
-- 3. MDM.Cuarentena_Personal
-- ===========================================================================
IF OBJECT_ID(N'MDM.Cuarentena_Personal', N'U') IS NULL
BEGIN
    CREATE TABLE MDM.Cuarentena_Personal (
        ID_Cuarentena_Per   BIGINT          IDENTITY(1,1) PRIMARY KEY,
        DNI_Recibido        NVARCHAR(20)    NOT NULL,
        Nombre_Recibido     NVARCHAR(200)   NULL,
        Rol_Recibido        NVARCHAR(100)   NULL,
        Origen_Tabla        NVARCHAR(100)   NOT NULL,
        Origen_Archivo      NVARCHAR(300)   NULL,
        Veces_Visto         INT             NOT NULL DEFAULT 1,
        Fecha_Primera_Vez   DATETIME2       NOT NULL DEFAULT GETDATE(),
        Fecha_Ultima_Vez    DATETIME2       NOT NULL DEFAULT GETDATE(),
        -- Workflow
        Estado              NVARCHAR(20)    NOT NULL DEFAULT 'PENDIENTE',
        ID_Personal_Sugerido INT            NULL,
        Aprobado_Por        NVARCHAR(50)    NULL,
        Fecha_Resolucion    DATETIME2       NULL,
        Nota_Aprobador      NVARCHAR(500)   NULL
    );

    CREATE UNIQUE INDEX UX_Cuarentena_Per_DNI
        ON MDM.Cuarentena_Personal (DNI_Recibido)
        WHERE Estado = 'PENDIENTE';

    CREATE INDEX IX_Cuarentena_Per_Estado
        ON MDM.Cuarentena_Personal (Estado, Fecha_Ultima_Vez DESC);
END
GO


-- ===========================================================================
-- 4. Vista de consulta unificada para el equipo MDM
-- ===========================================================================
CREATE OR ALTER VIEW MDM.vw_Cuarentena_Pendiente AS
SELECT
    'GEOGRAFIA'  AS Dominio,
    ID_Cuarentena_Geo AS ID,
    CONCAT_WS(' | ', Fundo, Sector, 'M='+Modulo, 'T='+Turno, 'V='+Valvula, 'C='+Cama) AS Descripcion,
    Origen_Tabla, Origen_Archivo, Veces_Visto,
    Fecha_Primera_Vez, Fecha_Ultima_Vez
FROM MDM.Cuarentena_Geografia
WHERE Estado = 'PENDIENTE'
UNION ALL
SELECT
    'VARIEDAD',
    ID_Cuarentena_Var,
    CONCAT(Nombre_Recibido, ' -> ', Nombre_Normalizado),
    Origen_Tabla, Origen_Archivo, Veces_Visto,
    Fecha_Primera_Vez, Fecha_Ultima_Vez
FROM MDM.Cuarentena_Variedad
WHERE Estado = 'PENDIENTE'
UNION ALL
SELECT
    'PERSONAL',
    ID_Cuarentena_Per,
    CONCAT(DNI_Recibido, ' - ', Nombre_Recibido),
    Origen_Tabla, Origen_Archivo, Veces_Visto,
    Fecha_Primera_Vez, Fecha_Ultima_Vez
FROM MDM.Cuarentena_Personal
WHERE Estado = 'PENDIENTE';
GO


-- ===========================================================================
-- 5. SP: aprobar item de cuarentena geografia (promueve a Dim_Geografia)
--    Comportamiento:
--    - Si @ID_Geografia_Destino se proporciona: FUSIONA (no crea nuevo)
--    - Si NO: crea nueva combinacion en Dim_Geografia con catalogos
-- ===========================================================================
CREATE OR ALTER PROCEDURE MDM.usp_Aprobar_Geografia
    @ID_Cuarentena          BIGINT,
    @Aprobado_Por           NVARCHAR(50),
    @ID_Geografia_Destino   INT             = NULL,
    @Nota                   NVARCHAR(500)   = NULL,
    @ID_Geografia_Salida    INT             OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Estado NVARCHAR(20), @F NVARCHAR(100), @S NVARCHAR(100),
            @M NVARCHAR(50), @T NVARCHAR(50), @V NVARCHAR(50), @C NVARCHAR(50);
    DECLARE @TempGeo TABLE (ID_Geografia INT);

    SELECT @Estado = Estado,
           @F = Fundo, @S = Sector, @M = Modulo,
           @T = Turno, @V = Valvula, @C = Cama
    FROM MDM.Cuarentena_Geografia
    WHERE ID_Cuarentena_Geo = @ID_Cuarentena;

    IF @Estado IS NULL
    BEGIN
        RAISERROR('Cuarentena Geografia %I64d no encontrada.', 16, 1, @ID_Cuarentena);
        RETURN;
    END
    IF @Estado <> 'PENDIENTE'
    BEGIN
        RAISERROR('Cuarentena %I64d ya resuelta (estado=%s).', 16, 1, @ID_Cuarentena, @Estado);
        RETURN;
    END

    BEGIN TRY
        BEGIN TRAN;

        IF @ID_Geografia_Destino IS NOT NULL
        BEGIN
            -- Fusion: solo marca y referencia
            IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Geografia WHERE ID_Geografia = @ID_Geografia_Destino)
            BEGIN
                RAISERROR('ID_Geografia %d destino no existe.', 16, 1, @ID_Geografia_Destino);
                ROLLBACK; RETURN;
            END
            SET @ID_Geografia_Salida = @ID_Geografia_Destino;

            UPDATE MDM.Cuarentena_Geografia
            SET Estado = 'FUSIONADO',
                ID_Geografia_Sugerido = @ID_Geografia_Destino,
                Aprobado_Por = @Aprobado_Por,
                Fecha_Resolucion = GETDATE(),
                Nota_Aprobador = @Nota
            WHERE ID_Cuarentena_Geo = @ID_Cuarentena;
        END
        ELSE
        BEGIN
            -- Resolver IDs de catalogos (o crear si faltan)
            DECLARE @id_f INT = 0, @id_s INT = 0, @id_m INT = 0,
                    @id_t INT = 0, @id_v INT = 0, @id_c INT = 0;

            IF @F IS NOT NULL
            BEGIN
                SELECT @id_f = ID_Fundo_Catalogo FROM Silver.Dim_Fundo_Catalogo WHERE Fundo = @F;
                IF @id_f IS NULL OR @id_f = 0
                BEGIN
                    INSERT INTO Silver.Dim_Fundo_Catalogo (Fundo) VALUES (@F);
                    SET @id_f = SCOPE_IDENTITY();
                END
            END

            IF @S IS NOT NULL
            BEGIN
                SELECT @id_s = ID_Sector_Catalogo FROM Silver.Dim_Sector_Catalogo WHERE Sector = @S;
                IF @id_s IS NULL OR @id_s = 0
                BEGIN
                    INSERT INTO Silver.Dim_Sector_Catalogo (Sector) VALUES (@S);
                    SET @id_s = SCOPE_IDENTITY();
                END
            END

            IF @M IS NOT NULL
            BEGIN
                SELECT @id_m = ID_Modulo_Catalogo FROM Silver.Dim_Modulo_Catalogo WHERE Modulo = TRY_CAST(@M AS INT);
                IF @id_m IS NULL OR @id_m = 0
                BEGIN
                    INSERT INTO Silver.Dim_Modulo_Catalogo (Modulo) VALUES (TRY_CAST(@M AS INT));
                    SET @id_m = SCOPE_IDENTITY();
                END
            END

            IF @T IS NOT NULL
            BEGIN
                SELECT @id_t = ID_Turno_Catalogo FROM Silver.Dim_Turno_Catalogo WHERE Turno = TRY_CAST(@T AS INT);
                IF @id_t IS NULL OR @id_t = 0
                BEGIN
                    INSERT INTO Silver.Dim_Turno_Catalogo (Turno) VALUES (TRY_CAST(@T AS INT));
                    SET @id_t = SCOPE_IDENTITY();
                END
            END

            IF @V IS NOT NULL
            BEGIN
                SELECT @id_v = ID_Valvula_Catalogo FROM Silver.Dim_Valvula_Catalogo WHERE Valvula = @V;
                IF @id_v IS NULL OR @id_v = 0
                BEGIN
                    INSERT INTO Silver.Dim_Valvula_Catalogo (Valvula) VALUES (@V);
                    SET @id_v = SCOPE_IDENTITY();
                END
            END

            -- Insertar combinacion final
            INSERT INTO Silver.Dim_Geografia (
                ID_Fundo_Catalogo, ID_Sector_Catalogo, ID_Modulo_Catalogo,
                ID_Turno_Catalogo, ID_Valvula_Catalogo, ID_Cama_Catalogo,
                Es_Test_Block, Nivel_Granularidad, Fecha_Inicio_Vigencia, Es_Vigente
            )
            OUTPUT INSERTED.ID_Geografia INTO @TempGeo
            VALUES (@id_f, @id_s, @id_m, @id_t, @id_v, ISNULL(@id_c, 0),
                    0, 'APROBADO_MDM', GETDATE(), 1);

            SELECT @ID_Geografia_Salida = ID_Geografia FROM @TempGeo;

            UPDATE MDM.Cuarentena_Geografia
            SET Estado = 'APROBADO',
                ID_Geografia_Sugerido = @ID_Geografia_Salida,
                Aprobado_Por = @Aprobado_Por,
                Fecha_Resolucion = GETDATE(),
                Nota_Aprobador = @Nota
            WHERE ID_Cuarentena_Geo = @ID_Cuarentena;
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END
GO


-- ===========================================================================
-- 6. SP: aprobar variedad
-- ===========================================================================
CREATE OR ALTER PROCEDURE MDM.usp_Aprobar_Variedad
    @ID_Cuarentena          BIGINT,
    @Aprobado_Por           NVARCHAR(50),
    @ID_Variedad_Destino    INT             = NULL,
    @Nombre_Canonico        NVARCHAR(200)   = NULL,
    @Nota                   NVARCHAR(500)   = NULL,
    @ID_Variedad_Salida     INT             OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Estado NVARCHAR(20), @NombreRec NVARCHAR(200), @NombreNorm NVARCHAR(200);
    SELECT @Estado = Estado, @NombreRec = Nombre_Recibido, @NombreNorm = Nombre_Normalizado
    FROM MDM.Cuarentena_Variedad
    WHERE ID_Cuarentena_Var = @ID_Cuarentena;

    IF @Estado IS NULL
    BEGIN
        RAISERROR('Cuarentena Variedad %I64d no encontrada.', 16, 1, @ID_Cuarentena);
        RETURN;
    END
    IF @Estado <> 'PENDIENTE'
    BEGIN
        RAISERROR('Cuarentena %I64d ya resuelta (estado=%s).', 16, 1, @ID_Cuarentena, @Estado);
        RETURN;
    END

    BEGIN TRY
        BEGIN TRAN;

        IF @ID_Variedad_Destino IS NOT NULL
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Variedad WHERE ID_Variedad = @ID_Variedad_Destino)
            BEGIN
                RAISERROR('ID_Variedad %d destino no existe.', 16, 1, @ID_Variedad_Destino);
                ROLLBACK; RETURN;
            END
            SET @ID_Variedad_Salida = @ID_Variedad_Destino;

            UPDATE MDM.Cuarentena_Variedad
            SET Estado = 'FUSIONADO', ID_Variedad_Sugerido = @ID_Variedad_Destino,
                Aprobado_Por = @Aprobado_Por, Fecha_Resolucion = GETDATE(),
                Nota_Aprobador = @Nota
            WHERE ID_Cuarentena_Var = @ID_Cuarentena;
        END
        ELSE
        BEGIN
            DECLARE @NombreFinal NVARCHAR(200) = ISNULL(@Nombre_Canonico, @NombreRec);

            -- Si ya existe por nombre, reusar
            SELECT @ID_Variedad_Salida = ID_Variedad
            FROM Silver.Dim_Variedad
            WHERE Nombre_Variedad = @NombreFinal;

            IF @ID_Variedad_Salida IS NULL
            BEGIN
                INSERT INTO Silver.Dim_Variedad (Nombre_Variedad, Es_Activa)
                VALUES (@NombreFinal, 1);
                SET @ID_Variedad_Salida = SCOPE_IDENTITY();
            END

            UPDATE MDM.Cuarentena_Variedad
            SET Estado = 'APROBADO', ID_Variedad_Sugerido = @ID_Variedad_Salida,
                Aprobado_Por = @Aprobado_Por, Fecha_Resolucion = GETDATE(),
                Nota_Aprobador = @Nota
            WHERE ID_Cuarentena_Var = @ID_Cuarentena;
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END
GO


-- ===========================================================================
-- 7. SP: aprobar personal
-- ===========================================================================
CREATE OR ALTER PROCEDURE MDM.usp_Aprobar_Personal
    @ID_Cuarentena          BIGINT,
    @Aprobado_Por           NVARCHAR(50),
    @Nombre_Final           NVARCHAR(200)   = NULL,
    @Rol_Final              NVARCHAR(100)   = 'Evaluador',
    @Nota                   NVARCHAR(500)   = NULL,
    @ID_Personal_Salida     INT             OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Estado NVARCHAR(20), @DNI NVARCHAR(20), @Nombre NVARCHAR(200);
    SELECT @Estado = Estado, @DNI = DNI_Recibido, @Nombre = Nombre_Recibido
    FROM MDM.Cuarentena_Personal
    WHERE ID_Cuarentena_Per = @ID_Cuarentena;

    IF @Estado IS NULL
    BEGIN
        RAISERROR('Cuarentena Personal %I64d no encontrada.', 16, 1, @ID_Cuarentena);
        RETURN;
    END
    IF @Estado <> 'PENDIENTE'
    BEGIN
        RAISERROR('Cuarentena %I64d ya resuelta (estado=%s).', 16, 1, @ID_Cuarentena, @Estado);
        RETURN;
    END

    BEGIN TRY
        BEGIN TRAN;

        DECLARE @NombreFinal NVARCHAR(200) = ISNULL(@Nombre_Final, @Nombre);

        SELECT @ID_Personal_Salida = ID_Personal FROM Silver.Dim_Personal WHERE DNI = @DNI;

        IF @ID_Personal_Salida IS NULL
        BEGIN
            INSERT INTO Silver.Dim_Personal (DNI, Nombre_Completo, Rol)
            VALUES (@DNI, @NombreFinal, @Rol_Final);
            SET @ID_Personal_Salida = SCOPE_IDENTITY();
        END

        UPDATE MDM.Cuarentena_Personal
        SET Estado = 'APROBADO', ID_Personal_Sugerido = @ID_Personal_Salida,
            Aprobado_Por = @Aprobado_Por, Fecha_Resolucion = GETDATE(),
            Nota_Aprobador = @Nota
        WHERE ID_Cuarentena_Per = @ID_Cuarentena;

        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END
GO


-- ===========================================================================
-- 8. Variable de tabla auxiliar para Geografia (necesaria al inicio del SP)
--    NOTA: las @table vars son locales al SP, declararlas dentro del SP
--    arriba si se necesita. Aqui solo dejamos los SP completos.
-- ===========================================================================


-- ===========================================================================
-- 9. Flag de configuracion: MDM_MODO_ESTRICTO
--    OFF (default) -> comportamiento actual (auto-create silente).
--    ON            -> auto-create deshabilitado; combinaciones nuevas a cuarentena.
-- ===========================================================================
IF NOT EXISTS (
    SELECT 1 FROM Config.Parametros_Pipeline
    WHERE Nombre_Parametro = 'MDM_MODO_ESTRICTO'
)
BEGIN
    INSERT INTO Config.Parametros_Pipeline (Nombre_Parametro, Valor, Descripcion)
    VALUES (
        'MDM_MODO_ESTRICTO',
        'OFF',
        'OFF: auto-create en Dim_Geografia/Variedad/Personal (legacy). '
        + 'ON: combinaciones nuevas van a MDM.Cuarentena_* y NO se crean automaticamente. '
        + 'Activar cuando el catalogo maestro este curado con el equipo.'
    );
END
GO

PRINT 'fase40_cuarentena_estricta_dims.sql aplicada OK.';
GO
