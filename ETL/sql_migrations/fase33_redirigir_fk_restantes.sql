-- =============================================================================
-- FASE 33: Redirigir FKs restantes de Geografia y eliminar tabla obsoleta
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

DECLARE @fk NVARCHAR(256);
DECLARE @sql NVARCHAR(MAX);
DECLARE @tablas TABLE (NombreTabla NVARCHAR(128));

INSERT INTO @tablas (NombreTabla) VALUES 
    ('Silver.Fact_Maduracion'),
    ('Silver.Fact_Cosecha_SAP'),
    ('Silver.Fact_Proyecciones'),
    ('Silver.Fact_Sanidad_Activo'),
    ('Silver.Fact_Ciclo_Poda'),
    ('Silver.Fact_Tareo');

DECLARE @tablaActual NVARCHAR(128);
DECLARE cTablas CURSOR FOR SELECT NombreTabla FROM @tablas;

OPEN cTablas;
FETCH NEXT FROM cTablas INTO @tablaActual;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @fk = NULL;
    
    SELECT @fk = fk.name
    FROM sys.foreign_keys fk
    JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
    JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id
    WHERE fk.parent_object_id = OBJECT_ID(@tablaActual)
      AND c.name = 'ID_Geografia'
      AND fk.referenced_object_id = OBJECT_ID('Silver.Dim_Geografia_Obsoleta');

    IF @fk IS NOT NULL
    BEGIN
        PRINT 'Redirigiendo FK en ' + @tablaActual + ': ' + @fk;
        
        -- Drop de la FK vieja
        SET @sql = 'ALTER TABLE ' + @tablaActual + ' DROP CONSTRAINT [' + @fk + ']';
        EXEC(@sql);
        
        -- Crear FK nueva apuntando a Dim_Geografia
        DECLARE @nuevaFk NVARCHAR(256) = 'FK_' + REPLACE(@tablaActual, 'Silver.', '') + '_Geo';
        
        IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = @nuevaFk AND parent_object_id = OBJECT_ID(@tablaActual))
        BEGIN
            SET @sql = 'ALTER TABLE ' + @tablaActual + ' ADD CONSTRAINT [' + @nuevaFk + '] FOREIGN KEY (ID_Geografia) REFERENCES Silver.Dim_Geografia(ID_Geografia)';
            EXEC(@sql);
        END
    END
    ELSE
    BEGIN
        PRINT 'No se encontró FK obsoleta en ' + @tablaActual + ' o ya fue corregida.';
    END

    FETCH NEXT FROM cTablas INTO @tablaActual;
END

CLOSE cTablas;
DEALLOCATE cTablas;
GO

PRINT '-------------------------------------------------------';
PRINT 'Intentando eliminar Dim_Geografia_Obsoleta por ultima vez...';
PRINT '-------------------------------------------------------';

IF OBJECT_ID('Silver.Dim_Geografia_Obsoleta', 'U') IS NOT NULL
BEGIN
    BEGIN TRY
        DROP TABLE Silver.Dim_Geografia_Obsoleta;
        PRINT ' - Eliminada con exito.';
    END TRY
    BEGIN CATCH
        PRINT ' - ERROR: No se pudo eliminar.';
        PRINT ERROR_MESSAGE();
    END CATCH
END
GO
