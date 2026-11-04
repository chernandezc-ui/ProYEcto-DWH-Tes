-- =============================================================================
-- fase38_bridge_geo_campana_condicion.sql
-- =============================================================================
-- Objetivo: Bridge GLOBAL Geografia x Campana x Condicion.
--   - Tabla Silver.Bridge_Geografia_Campana_Condicion (materializada)
--   - SP MDM.usp_Popular_Bridge_Geo_Campana_Condicion (idempotente, MERGE)
--
-- Fuente: Silver.Fact_Tasa_Crecimiento_Brotes (ID_Geografia ya resuelto por el
-- loader Python; Campana / Condicion como texto crudo en la fact).
--
-- Convencion respetada: Bridge_<dimensiones> + usp_Popular_<tabla>.
-- =============================================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- -----------------------------------------------------------------------------
-- 1. Tabla bridge
-- -----------------------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Bridge_Geografia_Campana_Condicion'
)
BEGIN
    CREATE TABLE Silver.Bridge_Geografia_Campana_Condicion (
        ID_Bridge           BIGINT       IDENTITY(1,1) NOT NULL,
        ID_Geografia        INT          NOT NULL,
        ID_Campana          INT          NOT NULL,
        ID_Condicion        INT          NOT NULL,
        Vigencia_Inicio     DATE         NOT NULL,
        Vigencia_Fin        DATE         NULL,
        Es_Activa           BIT          NOT NULL CONSTRAINT DF_Bridge_GCC_Activa  DEFAULT 1,
        Hash_Llave          BINARY(32)   NOT NULL,
        Fecha_Carga         DATETIME2    NOT NULL CONSTRAINT DF_Bridge_GCC_Fecha   DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_Bridge_GCC PRIMARY KEY CLUSTERED (ID_Bridge),
        CONSTRAINT UQ_Bridge_GCC_Hash UNIQUE (Hash_Llave),
        CONSTRAINT FK_Bridge_GCC_Geo  FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia        (ID_Geografia),
        CONSTRAINT FK_Bridge_GCC_Cmp  FOREIGN KEY (ID_Campana)   REFERENCES Silver.Dim_Campana          (ID_Campana),
        CONSTRAINT FK_Bridge_GCC_Cnd  FOREIGN KEY (ID_Condicion) REFERENCES Silver.Dim_Condicion_Cultivo(ID_Condicion)
    );

    CREATE INDEX IX_Bridge_GCC_Geo_Vigencia
        ON Silver.Bridge_Geografia_Campana_Condicion (ID_Geografia, Vigencia_Inicio, Vigencia_Fin)
        INCLUDE (ID_Campana, ID_Condicion);
END;
GO

-- -----------------------------------------------------------------------------
-- 2. SP populador (idempotente)
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE MDM.usp_Popular_Bridge_Geo_Campana_Condicion
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ins INT = 0, @upd INT = 0, @cuar INT = 0;

    IF OBJECT_ID('tempdb..#Acciones') IS NOT NULL DROP TABLE #Acciones;
    CREATE TABLE #Acciones (accion NVARCHAR(10));

    IF OBJECT_ID('tempdb..#Resueltas') IS NOT NULL DROP TABLE #Resueltas;

    -- Combinaciones distintas observadas en el fact (Geografia ya resuelta).
    -- Campana y Condicion vienen como texto; se resuelven contra sus Dim.
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
        -- Campana: match por Nombre_Campana exacto, o por anio (4 digitos) -> Anio_Cosecha.
        COALESCE(
            (SELECT TOP 1 dc.ID_Campana FROM Silver.Dim_Campana dc
              WHERE UPPER(dc.Nombre_Campana) = c.Campana_Raw),
            (SELECT TOP 1 dc.ID_Campana FROM Silver.Dim_Campana dc
              WHERE TRY_CAST(
                      SUBSTRING(c.Campana_Raw, PATINDEX('%[0-9][0-9][0-9][0-9]%', c.Campana_Raw), 4)
                      AS INT) = dc.Anio_Cosecha)
        ) AS ID_Campana,
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

    -- Cuarentena: filas con cualquier FK no resuelta.
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
            HASHBYTES(
                'SHA2_256',
                CONCAT(r.ID_Geografia, '|', r.ID_Campana, '|', r.ID_Condicion, '|',
                       CONVERT(VARCHAR(10), r.Vigencia_Inicio, 23))
            ) AS Hash_Llave
        FROM #Resueltas r
        WHERE r.ID_Campana   IS NOT NULL
          AND r.ID_Condicion IS NOT NULL
    )
    MERGE Silver.Bridge_Geografia_Campana_Condicion AS dst
    USING Validas AS src
       ON dst.Hash_Llave = src.Hash_Llave
    WHEN MATCHED AND (
            ISNULL(dst.Vigencia_Fin, '9999-12-31') <> ISNULL(src.Vigencia_Fin, '9999-12-31')
         OR dst.Es_Activa = 0
        )
        THEN UPDATE SET
            dst.Vigencia_Fin = src.Vigencia_Fin,
            dst.Es_Activa    = 1
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
-- 3. Migracion de Silver.Fact_Tasa_Crecimiento_Brotes: FKs ID_Campana / ID_Condicion
-- -----------------------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes')
      AND name = 'ID_Campana'
)
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD ID_Campana INT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Silver.Fact_Tasa_Crecimiento_Brotes')
      AND name = 'ID_Condicion'
)
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD ID_Condicion INT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Fact_TasaCrec_Campana'
)
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes
        ADD CONSTRAINT FK_Fact_TasaCrec_Campana
        FOREIGN KEY (ID_Campana) REFERENCES Silver.Dim_Campana(ID_Campana);
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Fact_TasaCrec_Condicion'
)
BEGIN
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes
        ADD CONSTRAINT FK_Fact_TasaCrec_Condicion
        FOREIGN KEY (ID_Condicion) REFERENCES Silver.Dim_Condicion_Cultivo(ID_Condicion);
END;
GO

-- -----------------------------------------------------------------------------
-- 4. SP de backfill: rellena ID_Campana / ID_Condicion en la fact desde el bridge
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE MDM.usp_Backfill_FK_Fact_Tasa_Crecimiento
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE f
       SET f.ID_Campana   = b.ID_Campana,
           f.ID_Condicion = b.ID_Condicion
      FROM Silver.Fact_Tasa_Crecimiento_Brotes f
      JOIN Silver.Bridge_Geografia_Campana_Condicion b
        ON  b.ID_Geografia    = f.ID_Geografia
        AND b.Es_Activa       = 1
        AND f.Fecha_Evento BETWEEN b.Vigencia_Inicio AND ISNULL(b.Vigencia_Fin, '9999-12-31')
     WHERE f.Estado_DQ = 'OK'
       AND (f.ID_Campana IS NULL OR f.ID_Condicion IS NULL);

    SELECT Filas_Backfill = @@ROWCOUNT;
END;
GO

