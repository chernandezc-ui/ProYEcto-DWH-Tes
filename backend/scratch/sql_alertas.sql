-- =====================================================================
-- sql_alertas.sql
-- ---------------------------------------------------------------------
-- DDL idempotente para Ack persistente de alertas del Control Center.
--
-- Una fila por alerta atendida. El "id_alerta" es una cadena estable
-- generada por el portal/backend (ej. "etl-12345", "cuarentena-pendientes").
-- Si se reabre (DELETE), también se audita en Log_Decisiones_MDM.
--
-- Ejecutar manualmente desde SSMS o vía sqlcmd. Seguro de re-ejecutar.
-- =====================================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'MDM')
    EXEC ('CREATE SCHEMA MDM');
GO

IF OBJECT_ID('MDM.Alerta_Ack', 'U') IS NULL
BEGIN
    CREATE TABLE MDM.Alerta_Ack (
        ID_Alerta   NVARCHAR(120) NOT NULL,
        Usuario_DNI NVARCHAR(20)  NOT NULL,
        Fecha_Ack   DATETIME2(0)  NOT NULL CONSTRAINT DF_Alerta_Ack_Fecha DEFAULT SYSUTCDATETIME(),
        Comentario  NVARCHAR(500) NULL,
        CONSTRAINT PK_Alerta_Ack PRIMARY KEY (ID_Alerta)
    );

    CREATE INDEX IX_Alerta_Ack_Fecha
        ON MDM.Alerta_Ack (Fecha_Ack DESC);
END
GO
