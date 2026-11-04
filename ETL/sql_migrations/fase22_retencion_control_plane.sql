-- =============================================================================
-- fase22_retencion_control_plane.sql
-- =============================================================================
-- Retención operativa para Control.*.
-- Crea el procedimiento Control.sp_Purgar_Historial_Control.
--
-- Política por defecto:
--   Corrida_Evento          -> 90 días
--   Comando_Ejecucion       -> 180 días (PROCESADO / ERROR_COLA)
--   Corrida + Paso + Cmd    -> 365 días, solo corridas cerradas
-- =============================================================================

USE ACP_DataWarehose_Proyecciones;
GO

IF OBJECT_ID(N'Control.Corrida', N'U') IS NULL
    THROW 50020, 'Falta Control.Corrida. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Corrida_Evento', N'U') IS NULL
    THROW 50021, 'Falta Control.Corrida_Evento. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Corrida_Paso', N'U') IS NULL
    THROW 50022, 'Falta Control.Corrida_Paso. Ejecuta primero crear_tablas_control.sql.', 1;
IF OBJECT_ID(N'Control.Comando_Ejecucion', N'U') IS NULL
    THROW 50023, 'Falta Control.Comando_Ejecucion. Ejecuta primero crear_tablas_control.sql.', 1;
GO

CREATE OR ALTER PROCEDURE Control.sp_Purgar_Historial_Control
    @Dias_Eventos INT = 90,
    @Dias_Comandos INT = 180,
    @Dias_Corridas INT = 365
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ahora DATETIME2(0) = GETDATE();
    DECLARE @corte_eventos DATETIME2(0) = DATEADD(DAY, -@Dias_Eventos, @ahora);
    DECLARE @corte_comandos DATETIME2(0) = DATEADD(DAY, -@Dias_Comandos, @ahora);
    DECLARE @corte_corridas DATETIME2(0) = DATEADD(DAY, -@Dias_Corridas, @ahora);

    DECLARE @eventos_eliminados INT = 0;
    DECLARE @comandos_eliminados INT = 0;
    DECLARE @pasos_eliminados INT = 0;
    DECLARE @corridas_eliminadas INT = 0;

    DECLARE @corridas_cerradas TABLE (
        ID_Corrida VARCHAR(36) PRIMARY KEY
    );

    INSERT INTO @corridas_cerradas (ID_Corrida)
    SELECT ID_Corrida
    FROM Control.Corrida
    WHERE Estado IN ('OK', 'ERROR', 'CANCELADO', 'TIMEOUT')
      AND COALESCE(Fecha_Fin, Fecha_Solicitud) < @corte_corridas;

    BEGIN TRANSACTION;

    DELETE ce
    FROM Control.Corrida_Evento ce
    INNER JOIN Control.Corrida c
        ON c.ID_Corrida = ce.ID_Corrida
    WHERE c.Estado IN ('OK', 'ERROR', 'CANCELADO', 'TIMEOUT')
      AND ce.Fecha_Evento < @corte_eventos
      AND c.ID_Corrida NOT IN (SELECT ID_Corrida FROM @corridas_cerradas);
    SET @eventos_eliminados += @@ROWCOUNT;

    DELETE cmd
    FROM Control.Comando_Ejecucion cmd
    LEFT JOIN Control.Corrida c
        ON c.ID_Corrida = cmd.ID_Corrida
    WHERE cmd.Estado_Cmd IN ('PROCESADO', 'ERROR_COLA')
      AND COALESCE(cmd.Fecha_Proceso, cmd.Fecha_Comando) < @corte_comandos
      AND ISNULL(c.Estado, 'OK') NOT IN ('PENDIENTE', 'EJECUTANDO');
    SET @comandos_eliminados += @@ROWCOUNT;

    DELETE ce
    FROM Control.Corrida_Evento ce
    WHERE ce.ID_Corrida IN (SELECT ID_Corrida FROM @corridas_cerradas);
    SET @eventos_eliminados += @@ROWCOUNT;

    DELETE cp
    FROM Control.Corrida_Paso cp
    WHERE cp.ID_Corrida IN (SELECT ID_Corrida FROM @corridas_cerradas);
    SET @pasos_eliminados += @@ROWCOUNT;

    DELETE cmd
    FROM Control.Comando_Ejecucion cmd
    WHERE cmd.ID_Corrida IN (SELECT ID_Corrida FROM @corridas_cerradas);
    SET @comandos_eliminados += @@ROWCOUNT;

    DELETE c
    FROM Control.Corrida c
    WHERE c.ID_Corrida IN (SELECT ID_Corrida FROM @corridas_cerradas);
    SET @corridas_eliminadas += @@ROWCOUNT;

    COMMIT TRANSACTION;

    SELECT
        @eventos_eliminados AS Eventos_Eliminados,
        @comandos_eliminados AS Comandos_Eliminados,
        @pasos_eliminados AS Pasos_Eliminados,
        @corridas_eliminadas AS Corridas_Eliminadas,
        @corte_eventos AS Corte_Eventos,
        @corte_comandos AS Corte_Comandos,
        @corte_corridas AS Corte_Corridas;
END;
GO

PRINT 'fase22_retencion_control_plane.sql aplicado correctamente.';
GO
