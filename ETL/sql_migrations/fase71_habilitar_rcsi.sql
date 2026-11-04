-- ============================================================================
-- fase71_habilitar_rcsi.sql
-- ============================================================================
-- Objetivo (V-06 / §19 ACID - Aislamiento):
--   Habilitar READ_COMMITTED_SNAPSHOT (RCSI) en la base de datos del DWH.
--
--   Con RCSI, las lecturas bajo el nivel por defecto (READ COMMITTED) usan
--   versionado de filas en tempdb en lugar de bloqueos compartidos. Esto
--   entrega lecturas consistentes SIN bloquear a los escritores y hace
--   INNECESARIAS las pistas `WITH (NOLOCK)` que hoy provocan lecturas sucias
--   (dirty reads), no repetibles y phantom reads en las consultas de reporte.
--
-- Idempotente: solo aplica el cambio si aún no está activo. Reejecutable.
--
-- IMPORTANTE:
--   * ALTER DATABASE ... SET READ_COMMITTED_SNAPSHOT requiere que no existan
--     otras conexiones activas a la BD (toma un lock exclusivo momentáneo).
--     Ejecutar en ventana de mantenimiento o con SINGLE_USER si es necesario.
--   * Tras verificar RCSI en producción, retirar progresivamente las pistas
--     WITH (NOLOCK) de las consultas de solo lectura del backend
--     (repo_proyecciones, servicio_analista_charts, servicio_analista_notificaciones).
-- ============================================================================

SET NOCOUNT ON;

DECLARE @db SYSNAME = DB_NAME();
DECLARE @rcsi_on BIT = (
    SELECT is_read_committed_snapshot_on
    FROM sys.databases
    WHERE database_id = DB_ID()
);

IF @rcsi_on = 1
BEGIN
    PRINT 'RCSI ya está habilitado en [' + @db + ']. Nada que hacer.';
END
ELSE
BEGIN
    PRINT 'Habilitando READ_COMMITTED_SNAPSHOT en [' + @db + ']...';
    DECLARE @sql NVARCHAR(MAX) =
        N'ALTER DATABASE ' + QUOTENAME(@db) +
        N' SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;';
    EXEC sp_executesql @sql;
    PRINT 'RCSI habilitado correctamente en [' + @db + '].';
END
GO
