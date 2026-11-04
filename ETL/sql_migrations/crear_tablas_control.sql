-- =============================================================================
-- crear_tablas_control.sql
-- =============================================================================
-- Esquema de control operativo del pipeline ETL.
-- Reemplaza el broker SSE en memoria por estado persistido en SQL Server.
--
-- EJECUTAR EN: ACP_DataWarehose_Proyecciones
-- Idempotente: seguro ejecutar múltiples veces.
-- =============================================================================

USE ACP_DataWarehose_Proyecciones;
GO

-- ── Esquema ────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Control')
BEGIN
    EXEC sp_executesql N'CREATE SCHEMA Control';
    PRINT 'Esquema Control creado.';
END
GO

-- =============================================================================
-- Control.Corrida
-- Registro maestro de una ejecución del pipeline ETL.
-- Estado: PENDIENTE → EJECUTANDO → OK | ERROR | CANCELADO | TIMEOUT
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Control.Corrida') AND type = 'U')
BEGIN
    CREATE TABLE Control.Corrida (
        ID_Corrida          VARCHAR(36)     NOT NULL,   -- UUID
        Iniciado_Por        VARCHAR(100)    NOT NULL,
        Comentario          VARCHAR(500)        NULL,
        Estado              VARCHAR(20)     NOT NULL
            CONSTRAINT CHK_Corrida_Estado CHECK (
                Estado IN ('PENDIENTE','EJECUTANDO','OK','ERROR','CANCELADO','TIMEOUT')
            ),
        Intento_Numero      INT             NOT NULL DEFAULT 1,
        Max_Reintentos      INT             NOT NULL DEFAULT 0,
        Fecha_Solicitud     DATETIME2(0)    NOT NULL DEFAULT GETDATE(),
        Fecha_Inicio        DATETIME2(0)        NULL,
        Fecha_Fin           DATETIME2(0)        NULL,
        PID_Runner          INT                 NULL,   -- PID del proceso runner activo
        Heartbeat_Ultimo    DATETIME2(0)        NULL,   -- Actualizado cada 30s por el runner
        Timeout_Segundos    INT             NOT NULL DEFAULT 3600,  -- 1h por defecto
        Mensaje_Final       VARCHAR(1000)       NULL,
        ID_Log_Auditoria    INT                 NULL,   -- FK a Auditoria.Log_Carga

        CONSTRAINT PK_Corrida PRIMARY KEY (ID_Corrida)
    );
    PRINT 'Tabla Control.Corrida creada.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Corrida_Estado' AND object_id = OBJECT_ID('Control.Corrida'))
BEGIN
    CREATE INDEX IX_Corrida_Estado ON Control.Corrida (Estado, Fecha_Solicitud DESC);
    CREATE INDEX IX_Corrida_FechaSolicitud ON Control.Corrida (Fecha_Solicitud DESC);
    PRINT 'Índices Control.Corrida creados.';
END
GO

-- =============================================================================
-- Control.Corrida_Evento
-- Log línea a línea del output del subprocess. Reemplaza el broker SSE en memoria.
-- El endpoint SSE lee de aquí, no de una cola asyncio.
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Control.Corrida_Evento') AND type = 'U')
BEGIN
    CREATE TABLE Control.Corrida_Evento (
        ID_Evento       BIGINT IDENTITY(1,1) NOT NULL,
        ID_Corrida      VARCHAR(36)          NOT NULL,
        Tipo            VARCHAR(20)          NOT NULL DEFAULT 'LOG'
            CONSTRAINT CHK_Evento_Tipo CHECK (Tipo IN ('LOG','PROGRESO','ERROR','FIN')),
        Mensaje         VARCHAR(4000)        NOT NULL,
        Fecha_Evento    DATETIME2(3)         NOT NULL DEFAULT GETDATE(),  -- ms precision

        CONSTRAINT PK_Corrida_Evento PRIMARY KEY (ID_Evento),
        CONSTRAINT FK_Evento_Corrida FOREIGN KEY (ID_Corrida)
            REFERENCES Control.Corrida (ID_Corrida)
    );
    PRINT 'Tabla Control.Corrida_Evento creada.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Evento_Corrida_ID' AND object_id = OBJECT_ID('Control.Corrida_Evento'))
BEGIN
    CREATE INDEX IX_Evento_Corrida_ID ON Control.Corrida_Evento (ID_Corrida, ID_Evento ASC);
    PRINT 'Índice IX_Evento_Corrida_ID creado.';
END
GO

-- =============================================================================
-- Control.Corrida_Paso
-- Pasos del pipeline. Permite trazar el progreso a nivel de etapa.
-- Población futura: cuando el pipeline sea descompuesto en tareas.
-- Por ahora el runner inserta un solo paso "PIPELINE_COMPLETO".
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Control.Corrida_Paso') AND type = 'U')
BEGIN
    CREATE TABLE Control.Corrida_Paso (
        ID_Paso         INT IDENTITY(1,1)   NOT NULL,
        ID_Corrida      VARCHAR(36)         NOT NULL,
        Nombre_Paso     VARCHAR(100)        NOT NULL,
        Orden           INT                 NOT NULL DEFAULT 1,
        Estado          VARCHAR(20)         NOT NULL DEFAULT 'PENDIENTE'
            CONSTRAINT CHK_Paso_Estado CHECK (
                Estado IN ('PENDIENTE','EJECUTANDO','OK','ERROR','OMITIDO')
            ),
        Fecha_Inicio    DATETIME2(0)            NULL,
        Fecha_Fin       DATETIME2(0)            NULL,
        Mensaje_Error   VARCHAR(1000)           NULL,

        CONSTRAINT PK_Corrida_Paso PRIMARY KEY (ID_Paso),
        CONSTRAINT FK_Paso_Corrida FOREIGN KEY (ID_Corrida)
            REFERENCES Control.Corrida (ID_Corrida)
    );
    PRINT 'Tabla Control.Corrida_Paso creada.';
END
GO

-- =============================================================================
-- Control.Bloqueo_Ejecucion
-- Distributed lock: garantiza máximo 1 corrida ejecutando a la vez.
-- El runner adquiere el lock antes de ejecutar y lo libera al terminar.
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Control.Bloqueo_Ejecucion') AND type = 'U')
BEGIN
    CREATE TABLE Control.Bloqueo_Ejecucion (
        ID_Lock             INT             NOT NULL DEFAULT 1,   -- Singleton
        ID_Corrida_Activa   VARCHAR(36)         NULL,
        Adquirido_Por       VARCHAR(100)        NULL,   -- hostname del runner
        Fecha_Adquisicion   DATETIME2(0)        NULL,
        Heartbeat           DATETIME2(0)        NULL,   -- actualizado cada 30s

        CONSTRAINT PK_Bloqueo PRIMARY KEY (ID_Lock),
        CONSTRAINT CHK_Bloqueo_Singleton CHECK (ID_Lock = 1)
    );

    -- Insertar la fila singleton (lock libre al inicio)
    INSERT INTO Control.Bloqueo_Ejecucion (ID_Lock, ID_Corrida_Activa)
    VALUES (1, NULL);

    PRINT 'Tabla Control.Bloqueo_Ejecucion creada e inicializada.';
END
GO

-- =============================================================================
-- Control.Comando_Ejecucion
-- Cola de comandos: FastAPI inserta, runner polling y ejecuta.
-- Una vez procesado, el comando pasa a estado PROCESADO o ERROR_COLA.
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM sys.objects
    WHERE object_id = OBJECT_ID(N'Control.Comando_Ejecucion') AND type = 'U')
BEGIN
    CREATE TABLE Control.Comando_Ejecucion (
        ID_Comando      INT IDENTITY(1,1)   NOT NULL,
        ID_Corrida      VARCHAR(36)         NOT NULL,
        Tipo_Comando    VARCHAR(50)         NOT NULL DEFAULT 'INICIAR'
            CONSTRAINT CHK_Comando_Tipo CHECK (
                Tipo_Comando IN ('INICIAR','CANCELAR','REINTENTAR')
            ),
        Iniciado_Por    VARCHAR(100)        NOT NULL,
        Comentario      VARCHAR(500)            NULL,
        Max_Reintentos  INT                 NOT NULL DEFAULT 0,
        Timeout_Seg     INT                 NOT NULL DEFAULT 3600,
        Estado_Cmd      VARCHAR(20)         NOT NULL DEFAULT 'PENDIENTE'
            CONSTRAINT CHK_Comando_Estado CHECK (
                Estado_Cmd IN ('PENDIENTE','PROCESANDO','PROCESADO','ERROR_COLA')
            ),
        Fecha_Comando   DATETIME2(0)        NOT NULL DEFAULT GETDATE(),
        Fecha_Proceso   DATETIME2(0)            NULL,
        Mensaje_Error   VARCHAR(500)            NULL,

        CONSTRAINT PK_Comando PRIMARY KEY (ID_Comando),
        CONSTRAINT FK_Comando_Corrida FOREIGN KEY (ID_Corrida)
            REFERENCES Control.Corrida (ID_Corrida)
    );
    PRINT 'Tabla Control.Comando_Ejecucion creada.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Comando_Pendiente' AND object_id = OBJECT_ID('Control.Comando_Ejecucion'))
BEGIN
    CREATE INDEX IX_Comando_Pendiente
        ON Control.Comando_Ejecucion (Estado_Cmd, Fecha_Comando ASC)
        WHERE Estado_Cmd = 'PENDIENTE';
    PRINT 'Índice IX_Comando_Pendiente creado.';
END
GO

PRINT '=== DDL del esquema Control completado ===';
GO
