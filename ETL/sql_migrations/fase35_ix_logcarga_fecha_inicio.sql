-- =============================================================================
-- fase35_ix_logcarga_fecha_inicio.sql
-- =============================================================================
-- Índice descending en Auditoria.Log_Carga(Fecha_Inicio DESC) para acelerar
-- las queries del dashboard que ordenan por fecha sin filtrar por tabla.
--
-- Contexto (O-4):
--   fase34 ya creó IX_LogCarga_Tabla_Fecha (Tabla_Destino, Fecha_Inicio DESC).
--   Ese índice cubre búsquedas filtradas por tabla. Las queries de historial
--   reciente del portal y el endpoint GET /api/v1/etl/corridas hacen:
--
--     SELECT TOP N ... FROM Auditoria.Log_Carga ORDER BY Fecha_Inicio DESC
--
--   sin filtrar por Tabla_Destino. El optimizador no puede usar IX_LogCarga_Tabla_Fecha
--   eficientemente (leading column es Tabla_Destino). Este índice resuelve ese gap.
--
-- PREREQUISITOS:  Fases 1-34 aplicadas.
-- BASE DE DATOS:  ACP_DataWarehose_Proyecciones
-- IDEMPOTENTE:    Sí — guarda dentro de IF NOT EXISTS.
-- ROLLBACK:       DROP INDEX IF EXISTS IX_LogCarga_Fecha_Inicio ON Auditoria.Log_Carga;
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

SET QUOTED_IDENTIFIER ON;
GO

PRINT '=== fase35: Índice Auditoria.Log_Carga(Fecha_Inicio DESC) ===';
PRINT CONVERT(NVARCHAR, GETDATE(), 120);
GO

-- =============================================================================
-- BLOQUE 1: Índice de dashboard por fecha descendente en Auditoria.Log_Carga
-- =============================================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name       = 'IX_LogCarga_Fecha_Inicio'
      AND object_id  = OBJECT_ID('Auditoria.Log_Carga')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_LogCarga_Fecha_Inicio
        ON Auditoria.Log_Carga (Fecha_Inicio DESC)
        INCLUDE (
            Tabla_Destino,
            Estado_Proceso,
            Filas_Insertadas,
            Filas_Cuarentena,
            Filas_Rechazadas,
            Duracion_Segundos
        );
    PRINT 'Creado: IX_LogCarga_Fecha_Inicio en Auditoria.Log_Carga.';
END
ELSE
    PRINT 'OMITIDO: IX_LogCarga_Fecha_Inicio ya existe.';
GO

-- =============================================================================
-- REGISTRO EN CONTROL DE MIGRACIONES
-- =============================================================================

IF OBJECT_ID('Silver.Migraciones_Aplicadas', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM Silver.Migraciones_Aplicadas
        WHERE Nombre_Fase = 'fase35_ix_logcarga_fecha_inicio'
    )
    INSERT INTO Silver.Migraciones_Aplicadas (Nombre_Fase, Fecha_Aplicacion, Descripcion)
    VALUES (
        'fase35_ix_logcarga_fecha_inicio',
        GETDATE(),
        'Índice IX_LogCarga_Fecha_Inicio en Auditoria.Log_Carga(Fecha_Inicio DESC) para queries de historial del dashboard'
    );
    PRINT 'Registrado en Silver.Migraciones_Aplicadas.';
END
GO

PRINT '=== fase35: Completado ===';
PRINT CONVERT(NVARCHAR, GETDATE(), 120);
GO

-- =============================================================================
-- ROLLBACK
-- =============================================================================
/*
USE [ACP_DataWarehose_Proyecciones];
DROP INDEX IF EXISTS IX_LogCarga_Fecha_Inicio ON Auditoria.Log_Carga;
*/
