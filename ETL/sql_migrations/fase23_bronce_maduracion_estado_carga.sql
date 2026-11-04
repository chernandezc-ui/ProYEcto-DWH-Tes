SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'FASE 23 - NORMALIZAR Bronce.Maduracion CON Estado_Carga';
PRINT '============================================================';

IF OBJECT_ID('Bronce.Maduracion', 'U') IS NULL
BEGIN
    RAISERROR('No existe Bronce.Maduracion.', 16, 1);
    RETURN;
END;

IF COL_LENGTH('Bronce.Maduracion', 'Estado_Carga') IS NULL
BEGIN
    PRINT 'Agregando columna Estado_Carga a Bronce.Maduracion...';

    ALTER TABLE Bronce.Maduracion
    ADD Estado_Carga NVARCHAR(20) NULL;
END;
ELSE
BEGIN
    PRINT 'Bronce.Maduracion ya tiene Estado_Carga.';
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints dc
    INNER JOIN sys.columns c
        ON c.default_object_id = dc.object_id
    INNER JOIN sys.tables t
        ON t.object_id = c.object_id
    INNER JOIN sys.schemas s
        ON s.schema_id = t.schema_id
    WHERE s.name = 'Bronce'
      AND t.name = 'Maduracion'
      AND c.name = 'Estado_Carga'
)
BEGIN
    PRINT 'Creando default DF_Bronce_Maduracion_Estado_Carga...';

    ALTER TABLE Bronce.Maduracion
    ADD CONSTRAINT DF_Bronce_Maduracion_Estado_Carga
        DEFAULT ('CARGADO') FOR Estado_Carga;
END;
ELSE
BEGIN
    PRINT 'Default de Estado_Carga ya existe.';
END;

PRINT 'Cerrando historico actual como PROCESADO...';
EXEC sp_executesql N'
    UPDATE Bronce.Maduracion
    SET Estado_Carga = ''PROCESADO''
    WHERE Estado_Carga IS NULL
       OR LTRIM(RTRIM(Estado_Carga)) = '''';
';

DECLARE @persisten_nulos_estado_carga BIT = 0;

EXEC sp_executesql
    N'
        SELECT @salida = CASE
            WHEN EXISTS (
                SELECT 1
                FROM Bronce.Maduracion
                WHERE Estado_Carga IS NULL
            ) THEN 1
            ELSE 0
        END;
    ',
    N'@salida BIT OUTPUT',
    @salida = @persisten_nulos_estado_carga OUTPUT;

IF @persisten_nulos_estado_carga = 1
BEGIN
    RAISERROR('Persisten filas con Estado_Carga NULL en Bronce.Maduracion.', 16, 1);
    RETURN;
END;

BEGIN TRY
    ALTER TABLE Bronce.Maduracion
    ALTER COLUMN Estado_Carga NVARCHAR(20) NOT NULL;
    PRINT 'Estado_Carga queda NOT NULL.';
END TRY
BEGIN CATCH
    PRINT 'No se pudo dejar Estado_Carga NOT NULL.';
    PRINT ERROR_MESSAGE();
    THROW;
END CATCH;

PRINT 'Resumen final Bronce.Maduracion:';
EXEC sp_executesql N'
    SELECT Estado_Carga, COUNT(*) AS Filas
    FROM Bronce.Maduracion
    GROUP BY Estado_Carga
    ORDER BY Estado_Carga;
';

PRINT 'Validacion de pipeline futuro:';
PRINT '- Historico actual debe quedar PROCESADO.';
PRINT '- Nuevas cargas entraran como CARGADO.';
PRINT '- Si no hay archivo nuevo, Fact_Maduracion debe leer 0 filas.';
