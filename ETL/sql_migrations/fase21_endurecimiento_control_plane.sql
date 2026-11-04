-- =============================================================================
-- fase21_endurecimiento_control_plane.sql
-- =============================================================================
-- Endurecimiento operativo de Control.* para ACP ETL.
-- Agrega índices de operación y vistas de monitoreo sin alterar contratos.
--
-- EJECUTAR DESPUÉS DE:
--   1. crear_tablas_control.sql
--
-- EJECUTAR EN:
--   ACP_DataWarehose_Proyecciones
-- =============================================================================

USE ACP_DataWarehose_Proyecciones;
GO

IF OBJECT_ID(N'Control.Corrida', N'U') IS NULL
    THROW 50001, 'Falta Control.Corrida. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Corrida_Evento', N'U') IS NULL
    THROW 50002, 'Falta Control.Corrida_Evento. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Corrida_Paso', N'U') IS NULL
    THROW 50003, 'Falta Control.Corrida_Paso. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Bloqueo_Ejecucion', N'U') IS NULL
    THROW 50004, 'Falta Control.Bloqueo_Ejecucion. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Comando_Ejecucion', N'U') IS NULL
    THROW 50005, 'Falta Control.Comando_Ejecucion. Ejecuta primero crear_tablas_control.sql.', 1;
GO

-- =============================================================================
-- Índices operativos
-- =============================================================================

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Corrida_Activas_Heartbeat'
      AND object_id = OBJECT_ID(N'Control.Corrida')
)
BEGIN
    CREATE INDEX IX_Corrida_Activas_Heartbeat
        ON Control.Corrida (Estado, Heartbeat_Ultimo DESC, Fecha_Solicitud DESC)
        INCLUDE (Fecha_Inicio, PID_Runner, Timeout_Segundos, Iniciado_Por, ID_Log_Auditoria)
        WHERE Estado IN ('PENDIENTE', 'EJECUTANDO');
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Corrida_IDLogAuditoria'
      AND object_id = OBJECT_ID(N'Control.Corrida')
)
BEGIN
    CREATE INDEX IX_Corrida_IDLogAuditoria
        ON Control.Corrida (ID_Log_Auditoria)
        INCLUDE (ID_Corrida, Estado, Fecha_Solicitud, Fecha_Inicio, Fecha_Fin, Iniciado_Por);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Evento_Corrida_Fecha'
      AND object_id = OBJECT_ID(N'Control.Corrida_Evento')
)
BEGIN
    CREATE INDEX IX_Evento_Corrida_Fecha
        ON Control.Corrida_Evento (ID_Corrida, Fecha_Evento DESC, ID_Evento DESC)
        INCLUDE (Tipo);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Paso_Corrida_Orden'
      AND object_id = OBJECT_ID(N'Control.Corrida_Paso')
)
BEGIN
    CREATE INDEX IX_Paso_Corrida_Orden
        ON Control.Corrida_Paso (ID_Corrida, Orden ASC, ID_Paso ASC)
        INCLUDE (Nombre_Paso, Estado, Fecha_Inicio, Fecha_Fin, Mensaje_Error);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Comando_Procesando'
      AND object_id = OBJECT_ID(N'Control.Comando_Ejecucion')
)
BEGIN
    CREATE INDEX IX_Comando_Procesando
        ON Control.Comando_Ejecucion (Estado_Cmd, Fecha_Proceso ASC)
        INCLUDE (ID_Corrida, Tipo_Comando, Iniciado_Por, Timeout_Seg)
        WHERE Estado_Cmd = 'PROCESANDO';
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Comando_Corrida_Historial'
      AND object_id = OBJECT_ID(N'Control.Comando_Ejecucion')
)
BEGIN
    CREATE INDEX IX_Comando_Corrida_Historial
        ON Control.Comando_Ejecucion (ID_Corrida, ID_Comando DESC)
        INCLUDE (Tipo_Comando, Estado_Cmd, Fecha_Comando, Fecha_Proceso, Mensaje_Error, Iniciado_Por);
END
GO

-- =============================================================================
-- Vistas operativas
-- =============================================================================

DECLARE @col_nombre_archivo SYSNAME =
    CASE
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Nombre_Archivo_Fuente') IS NOT NULL THEN 'Nombre_Archivo_Fuente'
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Nombre_Archivo') IS NOT NULL THEN 'Nombre_Archivo'
        ELSE NULL
    END;

DECLARE @col_estado_proceso SYSNAME =
    CASE
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Estado_Proceso') IS NOT NULL THEN 'Estado_Proceso'
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Estado') IS NOT NULL THEN 'Estado'
        ELSE NULL
    END;

IF @col_nombre_archivo IS NULL
    THROW 50006, 'Auditoria.Log_Carga no tiene columna de nombre de archivo compatible.', 1;

IF @col_estado_proceso IS NULL
    THROW 50007, 'Auditoria.Log_Carga no tiene columna de estado compatible.', 1;

DECLARE @sql_vw_corridas_activas NVARCHAR(MAX) = N'
CREATE OR ALTER VIEW Control.vw_Corridas_Activas
AS
SELECT
    c.ID_Corrida,
    c.Iniciado_Por,
    c.Comentario,
    c.Estado,
    c.Intento_Numero,
    c.Max_Reintentos,
    c.Fecha_Solicitud,
    c.Fecha_Inicio,
    c.Heartbeat_Ultimo,
    c.Timeout_Segundos,
    c.PID_Runner,
    DATEDIFF(SECOND, c.Fecha_Solicitud, GETDATE()) AS Segundos_Desde_Solicitud,
    CASE
        WHEN c.Heartbeat_Ultimo IS NULL THEN NULL
        ELSE DATEDIFF(SECOND, c.Heartbeat_Ultimo, GETDATE())
    END AS Segundos_Desde_Heartbeat,
    l.' + QUOTENAME(@col_nombre_archivo) + N' AS Nombre_Ejecucion_Auditoria,
    l.Tabla_Destino,
    l.' + QUOTENAME(@col_estado_proceso) + N' AS Estado_Auditoria
FROM Control.Corrida c
LEFT JOIN Auditoria.Log_Carga l
    ON l.ID_Log_Carga = c.ID_Log_Auditoria
WHERE c.Estado IN (''PENDIENTE'', ''EJECUTANDO'');';

EXEC sp_executesql @sql_vw_corridas_activas;
GO

DECLARE @col_nombre_archivo SYSNAME =
    CASE
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Nombre_Archivo_Fuente') IS NOT NULL THEN 'Nombre_Archivo_Fuente'
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Nombre_Archivo') IS NOT NULL THEN 'Nombre_Archivo'
        ELSE NULL
    END;

DECLARE @col_estado_proceso SYSNAME =
    CASE
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Estado_Proceso') IS NOT NULL THEN 'Estado_Proceso'
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Estado') IS NOT NULL THEN 'Estado'
        ELSE NULL
    END;

IF @col_nombre_archivo IS NULL
    THROW 50008, 'Auditoria.Log_Carga no tiene columna de nombre de archivo compatible.', 1;

IF @col_estado_proceso IS NULL
    THROW 50009, 'Auditoria.Log_Carga no tiene columna de estado compatible.', 1;

DECLARE @sql_vw_cola_comandos NVARCHAR(MAX) = N'
CREATE OR ALTER VIEW Control.vw_Cola_Comandos
AS
SELECT
    cmd.ID_Comando,
    cmd.ID_Corrida,
    cmd.Tipo_Comando,
    cmd.Iniciado_Por,
    cmd.Estado_Cmd,
    cmd.Fecha_Comando,
    cmd.Fecha_Proceso,
    cmd.Timeout_Seg,
    DATEDIFF(SECOND, cmd.Fecha_Comando, GETDATE()) AS Segundos_En_Cola,
    c.Estado AS Estado_Corrida,
    c.Heartbeat_Ultimo,
    CASE
        WHEN c.Heartbeat_Ultimo IS NULL THEN NULL
        ELSE DATEDIFF(SECOND, c.Heartbeat_Ultimo, GETDATE())
    END AS Segundos_Desde_Heartbeat
FROM Control.Comando_Ejecucion cmd
LEFT JOIN Control.Corrida c
    ON c.ID_Corrida = cmd.ID_Corrida;';

EXEC sp_executesql @sql_vw_cola_comandos;
GO

DECLARE @col_nombre_archivo SYSNAME =
    CASE
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Nombre_Archivo_Fuente') IS NOT NULL THEN 'Nombre_Archivo_Fuente'
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Nombre_Archivo') IS NOT NULL THEN 'Nombre_Archivo'
        ELSE NULL
    END;

DECLARE @col_estado_proceso SYSNAME =
    CASE
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Estado_Proceso') IS NOT NULL THEN 'Estado_Proceso'
        WHEN COL_LENGTH('Auditoria.Log_Carga', 'Estado') IS NOT NULL THEN 'Estado'
        ELSE NULL
    END;

IF @col_nombre_archivo IS NULL
    THROW 50010, 'Auditoria.Log_Carga no tiene columna de nombre de archivo compatible.', 1;

IF @col_estado_proceso IS NULL
    THROW 50011, 'Auditoria.Log_Carga no tiene columna de estado compatible.', 1;

IF OBJECT_ID(N'Auditoria.Log_Carga', N'U') IS NOT NULL
BEGIN
    DECLARE @sql_vw_ultima_corrida NVARCHAR(MAX) = N'
        CREATE OR ALTER VIEW Control.vw_Ultima_Corrida_Por_Tabla
        AS
        WITH ultimas AS (
            SELECT
                l.Tabla_Destino,
                l.ID_Log_Carga,
                l.' + QUOTENAME(@col_nombre_archivo) + N' AS Nombre_Archivo,
                l.Fecha_Inicio,
                l.Fecha_Fin,
                l.' + QUOTENAME(@col_estado_proceso) + N' AS Estado,
                l.Filas_Leidas,
                l.Filas_Insertadas,
                l.Filas_Rechazadas,
                l.Duracion_Segundos,
                l.Mensaje_Error,
                c.ID_Corrida,
                c.Iniciado_Por,
                c.Comentario,
                ROW_NUMBER() OVER (
                    PARTITION BY l.Tabla_Destino
                    ORDER BY l.Fecha_Inicio DESC, l.ID_Log_Carga DESC
                ) AS rn
            FROM Auditoria.Log_Carga l
            LEFT JOIN Control.Corrida c
                ON c.ID_Log_Auditoria = l.ID_Log_Carga
        )
        SELECT
            Tabla_Destino,
            ID_Log_Carga,
            ID_Corrida,
            Iniciado_Por,
            Comentario,
            Nombre_Archivo,
            Fecha_Inicio,
            Fecha_Fin,
            Estado,
            Filas_Leidas,
            Filas_Insertadas,
            Filas_Rechazadas,
            Duracion_Segundos,
            Mensaje_Error
        FROM ultimas
        WHERE rn = 1;
    ';
    EXEC sp_executesql @sql_vw_ultima_corrida;
END
GO

PRINT 'fase21_endurecimiento_control_plane.sql aplicado correctamente.';
GO
