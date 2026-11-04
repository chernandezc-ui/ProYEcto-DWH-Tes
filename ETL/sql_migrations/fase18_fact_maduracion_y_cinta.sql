SET NOCOUNT ON;

DECLARE @tabla_conteo NVARCHAR(256) = N'Silver.Fact_Conteo_Fenologico';
DECLARE @tabla_maduracion NVARCHAR(256) = N'Silver.Fact_Maduracion';

IF COL_LENGTH(@tabla_conteo, 'ID_Cinta') IS NOT NULL
BEGIN
    DECLARE @fk_cinta SYSNAME;

    SELECT TOP (1)
        @fk_cinta = fk.name
    FROM sys.foreign_keys fk
    JOIN sys.foreign_key_columns fkc
        ON fk.object_id = fkc.constraint_object_id
    JOIN sys.tables t
        ON t.object_id = fk.parent_object_id
    JOIN sys.schemas s
        ON s.schema_id = t.schema_id
    JOIN sys.columns c
        ON c.object_id = t.object_id
       AND c.column_id = fkc.parent_column_id
    WHERE s.name = N'Silver'
      AND t.name = N'Fact_Conteo_Fenologico'
      AND c.name = N'ID_Cinta';

    IF @fk_cinta IS NOT NULL
    BEGIN
        DECLARE @sql_drop_fk NVARCHAR(MAX);
        SET @sql_drop_fk = N'ALTER TABLE ' + @tabla_conteo + N' DROP CONSTRAINT ' + QUOTENAME(@fk_cinta) + N';';
        EXEC sys.sp_executesql @sql_drop_fk;
    END;

    ALTER TABLE Silver.Fact_Conteo_Fenologico
    DROP COLUMN ID_Cinta;
END;

IF OBJECT_ID(@tabla_maduracion, 'U') IS NULL
BEGIN
    CREATE TABLE Silver.Fact_Maduracion (
        ID_Fact_Maduracion BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ID_Maduracion_Origen BIGINT NOT NULL,
        ID_Geografia INT NOT NULL,
        ID_Tiempo INT NOT NULL,
        ID_Variedad INT NOT NULL,
        ID_Personal INT NULL,
        ID_Cinta INT NOT NULL,
        Semana_Ventana INT NOT NULL,
        Clave_Medicion NVARCHAR(100) NOT NULL,
        Valor_Medicion DECIMAL(18,4) NOT NULL,
        Fecha_Evento DATETIME2 NOT NULL,
        Fecha_Sistema DATETIME2 NOT NULL CONSTRAINT DF_Fact_Maduracion_Fecha_Sistema DEFAULT SYSDATETIME(),
        Estado_DQ NVARCHAR(20) NOT NULL CONSTRAINT DF_Fact_Maduracion_Estado_DQ DEFAULT N'OK'
    );

    ALTER TABLE Silver.Fact_Maduracion
        ADD CONSTRAINT FK_Fact_Maduracion_Geografia
            FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia);

    ALTER TABLE Silver.Fact_Maduracion
        ADD CONSTRAINT FK_Fact_Maduracion_Tiempo
            FOREIGN KEY (ID_Tiempo) REFERENCES Silver.Dim_Tiempo(ID_Tiempo);

    ALTER TABLE Silver.Fact_Maduracion
        ADD CONSTRAINT FK_Fact_Maduracion_Variedad
            FOREIGN KEY (ID_Variedad) REFERENCES Silver.Dim_Variedad(ID_Variedad);

    ALTER TABLE Silver.Fact_Maduracion
        ADD CONSTRAINT FK_Fact_Maduracion_Personal
            FOREIGN KEY (ID_Personal) REFERENCES Silver.Dim_Personal(ID_Personal);

    ALTER TABLE Silver.Fact_Maduracion
        ADD CONSTRAINT FK_Fact_Maduracion_Cinta
            FOREIGN KEY (ID_Cinta) REFERENCES Silver.Dim_Cinta(ID_Cinta);

    ALTER TABLE Silver.Fact_Maduracion
        ADD CONSTRAINT CK_Fact_Maduracion_Semana_Ventana
            CHECK (Semana_Ventana BETWEEN 1 AND 6);

    CREATE UNIQUE INDEX UX_Fact_Maduracion_Origen_Semana_Clave
        ON Silver.Fact_Maduracion (ID_Maduracion_Origen, Semana_Ventana, Clave_Medicion);

    CREATE INDEX IX_Fact_Maduracion_Tiempo_Geografia
        ON Silver.Fact_Maduracion (ID_Tiempo, ID_Geografia, ID_Variedad);
END;

SELECT
    N'Fact_Conteo_Fenologico' AS Tabla,
    c.COLUMN_NAME,
    c.DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS c
WHERE c.TABLE_SCHEMA = N'Silver'
  AND c.TABLE_NAME = N'Fact_Conteo_Fenologico'
  AND c.COLUMN_NAME = N'ID_Cinta'

UNION ALL

SELECT
    N'Fact_Maduracion' AS Tabla,
    c.COLUMN_NAME,
    c.DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS c
WHERE c.TABLE_SCHEMA = N'Silver'
  AND c.TABLE_NAME = N'Fact_Maduracion'
ORDER BY Tabla, COLUMN_NAME;
