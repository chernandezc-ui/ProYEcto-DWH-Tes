-- ============================================================================
-- Auditoria.Cambios_Portal — Registro de cambios manuales desde el Portal MDM
-- ============================================================================
-- Ejecutar este script en la BD ACP_DataWarehose_Proyecciones para habilitar
-- la trazabilidad de cambios manuales realizados desde el portal web.
--
-- Cada vez que un usuario aprueba/rechaza un registro de cuarentena,
-- edita un catálogo, o modifica un parámetro, el portal registra:
--   • Quién hizo el cambio
--   • Qué tabla/campo/registro se afectó
--   • Valores antes y después
--   • Fecha exacta de la acción
-- ============================================================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Auditoria')
    EXEC('CREATE SCHEMA Auditoria');
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'Auditoria.Cambios_Portal') AND type = 'U')
BEGIN
    CREATE TABLE Auditoria.Cambios_Portal (
        ID_Cambio        INT IDENTITY(1,1) PRIMARY KEY,
        Tabla_Afectada   VARCHAR(200)  NOT NULL,
        Registro_ID      VARCHAR(100)  NOT NULL,
        Campo            VARCHAR(200)  NOT NULL,
        Valor_Anterior   NVARCHAR(MAX) NULL,
        Valor_Nuevo      NVARCHAR(MAX) NULL,
        Usuario          VARCHAR(100)  NOT NULL DEFAULT 'portal_user',
        Accion           VARCHAR(50)   NOT NULL DEFAULT 'UPDATE', -- UPDATE, INSERT, DELETE, APPROVE, REJECT
        Fecha_Cambio     DATETIME2     NOT NULL DEFAULT GETDATE(),

        -- Índices para consulta rápida
        INDEX IX_Cambios_Fecha    NONCLUSTERED (Fecha_Cambio DESC),
        INDEX IX_Cambios_Tabla    NONCLUSTERED (Tabla_Afectada),
        INDEX IX_Cambios_Usuario  NONCLUSTERED (Usuario),
    );

    PRINT 'Tabla Auditoria.Cambios_Portal creada exitosamente.';
END
ELSE
BEGIN
    PRINT 'Tabla Auditoria.Cambios_Portal ya existe — sin cambios.';
END
GO
