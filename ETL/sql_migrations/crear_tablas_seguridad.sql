-- =============================================================================
-- crear_tablas_seguridad.sql
-- =============================================================================
-- Crea el esquema Seguridad y las tablas de usuarios y auditoría de acceso
-- para el backend ACP Platform.
--
-- EJECUTAR UNA SOLA VEZ en: ACP_DataWarehose_Proyecciones
-- Requiere permisos de DDL (db_owner o equivalente).
-- =============================================================================

USE ACP_DataWarehose_Proyecciones;
GO

-- ── Esquema ────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Seguridad')
BEGIN
    EXEC sp_executesql N'CREATE SCHEMA Seguridad';
    PRINT 'Esquema Seguridad creado.';
END
GO

-- ── Tabla de usuarios de la aplicación ────────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Seguridad.Usuarios') AND type = 'U'
)
BEGIN
    CREATE TABLE Seguridad.Usuarios (
        ID_Usuario      INT IDENTITY(1,1)    NOT NULL,
        Nombre_Usuario  VARCHAR(100)         NOT NULL,
        Nombre_Display  VARCHAR(200)         NOT NULL,
        Email           VARCHAR(200)             NULL,
        Hash_Clave      VARCHAR(300)         NOT NULL,  -- bcrypt hash
        Rol             VARCHAR(50)          NOT NULL,
        Es_Activo       BIT                  NOT NULL DEFAULT 1,
        Fecha_Creacion  DATETIME2(0)         NOT NULL DEFAULT GETDATE(),
        Ultimo_Acceso   DATETIME2(0)             NULL,

        CONSTRAINT PK_Usuarios          PRIMARY KEY (ID_Usuario),
        CONSTRAINT UQ_Usuarios_Nombre   UNIQUE      (Nombre_Usuario),
        CONSTRAINT CHK_Usuarios_Rol     CHECK       (
            Rol IN ('admin', 'operador_etl', 'analista_mdm', 'viewer')
        )
    );

    PRINT 'Tabla Seguridad.Usuarios creada.';
END
ELSE
    PRINT 'Tabla Seguridad.Usuarios ya existe — omitida.';
GO

-- ── Índice de búsqueda rápida por nombre de usuario ───────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Usuarios_NombreUsuario'
      AND object_id = OBJECT_ID('Seguridad.Usuarios')
)
BEGIN
    CREATE INDEX IX_Usuarios_NombreUsuario
        ON Seguridad.Usuarios (Nombre_Usuario)
    WHERE Es_Activo = 1;

    PRINT 'Índice IX_Usuarios_NombreUsuario creado.';
END
GO

-- ── Tabla de auditoría de accesos de la aplicación ────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Auditoria.Log_Acceso') AND type = 'U'
)
BEGIN
    CREATE TABLE Auditoria.Log_Acceso (
        ID_Acceso       INT IDENTITY(1,1)   NOT NULL,
        Nombre_Usuario  VARCHAR(100)        NOT NULL,
        Accion          VARCHAR(200)        NOT NULL,  -- Ej: 'LOGIN', 'LANZAR_ETL', 'RESOLVER_CUARENTENA'
        Endpoint        VARCHAR(300)            NULL,  -- /api/v1/etl/corridas
        Request_ID      VARCHAR(50)             NULL,
        IP_Origen       VARCHAR(50)             NULL,
        Resultado       VARCHAR(20)         NOT NULL,  -- OK | DENEGADO | ERROR
        Detalle         VARCHAR(500)            NULL,
        Fecha_Accion    DATETIME2(0)        NOT NULL DEFAULT GETDATE(),

        CONSTRAINT PK_Log_Acceso PRIMARY KEY (ID_Acceso)
    );

    PRINT 'Tabla Auditoria.Log_Acceso creada.';
END
ELSE
    PRINT 'Tabla Auditoria.Log_Acceso ya existe — omitida.';
GO

-- ── Índice de búsqueda por usuario y fecha ────────────────────────────────────
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LogAcceso_Usuario_Fecha'
      AND object_id = OBJECT_ID('Auditoria.Log_Acceso')
)
BEGIN
    CREATE INDEX IX_LogAcceso_Usuario_Fecha
        ON Auditoria.Log_Acceso (Nombre_Usuario, Fecha_Accion DESC);

    PRINT 'Índice IX_LogAcceso_Usuario_Fecha creado.';
END
GO

PRINT '=== DDL de seguridad completado ===';
GO
