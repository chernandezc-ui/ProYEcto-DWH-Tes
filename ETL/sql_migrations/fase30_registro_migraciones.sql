-- ============================================================================
-- fase30_registro_migraciones.sql
-- ============================================================================
-- Crea la infraestructura de trazabilidad para las migraciones SQL del pipeline.
-- Una vez aplicada, todas las migraciones futuras quedan registradas con su hash,
-- fecha y ejecutor para auditoría y prevención de drift código↔DB.
-- ============================================================================

-- 1. Crear esquema Admin si no existe
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Admin')
    EXEC('CREATE SCHEMA Admin');
GO

-- 2. Crear tabla de registro de migraciones
IF NOT EXISTS (
    SELECT 1 FROM sys.objects o
    JOIN sys.schemas s ON s.schema_id = o.schema_id
    WHERE s.name = 'Admin' AND o.name = 'Migraciones_Aplicadas' AND o.type = 'U'
)
BEGIN
    CREATE TABLE Admin.Migraciones_Aplicadas (
        ID_Migracion       INT IDENTITY(1,1) PRIMARY KEY,
        Nombre_Archivo     NVARCHAR(255)  NOT NULL,
        Hash_SHA256        NVARCHAR(64)   NOT NULL,
        Fecha_Aplicacion   DATETIME2      NOT NULL DEFAULT GETDATE(),
        Ejecutado_Por      NVARCHAR(128)  NOT NULL DEFAULT SYSTEM_USER,
        Duracion_Segundos  FLOAT          NULL,
        Estado             NVARCHAR(20)   NOT NULL DEFAULT 'OK',  -- OK, ERROR
        Mensaje_Error      NVARCHAR(MAX)  NULL,
        
        CONSTRAINT UQ_Migraciones_Nombre UNIQUE (Nombre_Archivo)
    );
    PRINT 'Tabla Admin.Migraciones_Aplicadas creada.';
END
ELSE
    PRINT 'Tabla Admin.Migraciones_Aplicadas ya existe.';
GO

-- 3. Registrar esta propia migración como la primera
IF NOT EXISTS (
    SELECT 1 FROM Admin.Migraciones_Aplicadas 
    WHERE Nombre_Archivo = 'fase30_registro_migraciones.sql'
)
BEGIN
    INSERT INTO Admin.Migraciones_Aplicadas (Nombre_Archivo, Hash_SHA256, Estado)
    VALUES ('fase30_registro_migraciones.sql', 'BOOTSTRAP', 'OK');
    PRINT 'Migración fase30 registrada como bootstrap.';
END
GO
