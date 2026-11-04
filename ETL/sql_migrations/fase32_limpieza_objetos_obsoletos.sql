-- =============================================================================
-- FASE 32: Limpieza de Base de Datos (Objetos Obsoletos e Índices sin Uso)
-- =============================================================================

USE [ACP_DataWarehose_Proyecciones];
GO

PRINT '-------------------------------------------------------';
PRINT '1. LIMPIEZA DE TABLAS DE RESPALDO Y OBSOLETAS';
PRINT '-------------------------------------------------------';

IF OBJECT_ID('Auditoria.Respaldo_Bronce_Fisiologia_20260401', 'U') IS NOT NULL
BEGIN
    PRINT 'Eliminando tabla: Auditoria.Respaldo_Bronce_Fisiologia_20260401';
    DROP TABLE Auditoria.Respaldo_Bronce_Fisiologia_20260401;
END
GO

IF OBJECT_ID('Auditoria.Respaldo_Fact_Fisiologia_20260401', 'U') IS NOT NULL
BEGIN
    PRINT 'Eliminando tabla: Auditoria.Respaldo_Fact_Fisiologia_20260401';
    DROP TABLE Auditoria.Respaldo_Fact_Fisiologia_20260401;
END
GO

IF OBJECT_ID('Auditoria.Respaldo_Cuarentena_Fisiologia_20260401', 'U') IS NOT NULL
BEGIN
    PRINT 'Eliminando tabla: Auditoria.Respaldo_Cuarentena_Fisiologia_20260401';
    DROP TABLE Auditoria.Respaldo_Cuarentena_Fisiologia_20260401;
END
GO

-- Se intenta eliminar Dim_Geografia_Obsoleta. Si aún existen FKs apuntando a ella
-- (que no deberían por la Fase 31), el motor de SQL Server bloqueará la acción
-- por seguridad (Constraint Error), lo cual es el comportamiento deseado.
IF OBJECT_ID('Silver.Dim_Geografia_Obsoleta', 'U') IS NOT NULL
BEGIN
    PRINT 'Eliminando tabla obsoleta: Silver.Dim_Geografia_Obsoleta';
    BEGIN TRY
        DROP TABLE Silver.Dim_Geografia_Obsoleta;
        PRINT ' - Eliminada con exito.';
    END TRY
    BEGIN CATCH
        PRINT ' - ERROR: No se pudo eliminar. Es posible que aún existan Foreign Keys apuntando a ella.';
        PRINT ERROR_MESSAGE();
    END CATCH
END
GO

PRINT '-------------------------------------------------------';
PRINT '2. ELIMINACIÓN DE ÍNDICES SIN USO (Cero Lecturas)';
PRINT '-------------------------------------------------------';

-- Silver.Fact_Induccion_Floral
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Induccion_Floral_Tiempo_Geografia' AND object_id = OBJECT_ID('Silver.Fact_Induccion_Floral'))
BEGIN
    PRINT 'Eliminando índice: IX_Fact_Induccion_Floral_Tiempo_Geografia';
    DROP INDEX IX_Fact_Induccion_Floral_Tiempo_Geografia ON Silver.Fact_Induccion_Floral;
END
GO

-- Control.Comando_Ejecucion
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Comando_Corrida_Historial' AND object_id = OBJECT_ID('Control.Comando_Ejecucion'))
BEGIN
    PRINT 'Eliminando índice: IX_Comando_Corrida_Historial';
    DROP INDEX IX_Comando_Corrida_Historial ON Control.Comando_Ejecucion;
END
GO

-- Control.Corrida_Evento
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Evento_Corrida_ID' AND object_id = OBJECT_ID('Control.Corrida_Evento'))
BEGIN
    PRINT 'Eliminando índice: IX_Evento_Corrida_ID';
    DROP INDEX IX_Evento_Corrida_ID ON Control.Corrida_Evento;
END
GO

-- Silver.Fact_Maduracion
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Fact_Maduracion_Cinta_Tiempo' AND object_id = OBJECT_ID('Silver.Fact_Maduracion'))
BEGIN
    PRINT 'Eliminando índice: IX_Fact_Maduracion_Cinta_Tiempo';
    DROP INDEX IX_Fact_Maduracion_Cinta_Tiempo ON Silver.Fact_Maduracion;
END
GO

-- Control.Corrida (3 índices)
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Corrida_IDLogAuditoria' AND object_id = OBJECT_ID('Control.Corrida'))
BEGIN
    PRINT 'Eliminando índice: IX_Corrida_IDLogAuditoria';
    DROP INDEX IX_Corrida_IDLogAuditoria ON Control.Corrida;
END
GO

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Corrida_Estado' AND object_id = OBJECT_ID('Control.Corrida'))
BEGIN
    PRINT 'Eliminando índice: IX_Corrida_Estado';
    DROP INDEX IX_Corrida_Estado ON Control.Corrida;
END
GO

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Corrida_FechaSolicitud' AND object_id = OBJECT_ID('Control.Corrida'))
BEGIN
    PRINT 'Eliminando índice: IX_Corrida_FechaSolicitud';
    DROP INDEX IX_Corrida_FechaSolicitud ON Control.Corrida;
END
GO

PRINT '-------------------------------------------------------';
PRINT 'Fase 32 completada: Limpieza ejecutada de forma segura.';
PRINT '-------------------------------------------------------';
