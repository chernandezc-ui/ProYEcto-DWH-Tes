/*
================================================================================
  Migración: Crear Silver.Fact_Ciclos_Fenologicos
================================================================================
  Fecha:       2026-05-24
  Motivo:      Bronce.Ciclos_Fenologicos quedó huérfana tras la migración
               Bronce.Maduracion → Bronce.Ciclos_Fenologicos (sin reemplazo del
               fact_maduracion borrado). Esta migración crea el destino Silver
               para que el nuevo procesador fact_ciclos_fenologicos.py tenga
               donde insertar.

  Grain:       Geografía × Tiempo × Variedad × Cama × Tipo_Evaluacion × Categoria

  Idempotente: usa IF NOT EXISTS para que se pueda correr varias veces.
================================================================================
*/

IF NOT EXISTS (
    SELECT 1
    FROM sys.tables t
    INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Silver' AND t.name = 'Fact_Ciclos_Fenologicos'
)
BEGIN
    CREATE TABLE Silver.Fact_Ciclos_Fenologicos (
        ID_Ciclo_Fenologico_Silver  BIGINT          IDENTITY(1,1) PRIMARY KEY,

        -- Dimensiones (FKs)
        ID_Geografia                INT             NOT NULL REFERENCES Silver.Dim_Geografia(ID_Geografia),
        ID_Tiempo                   INT             NOT NULL REFERENCES Silver.Dim_Tiempo(ID_Tiempo),
        ID_Variedad                 INT             NOT NULL REFERENCES Silver.Dim_Variedad(ID_Variedad),

        -- Atributos del grain (extraídos de Valores_Raw)
        Cama                        NVARCHAR(50)    NULL,
        Tipo_Evaluacion             NVARCHAR(100)   NULL,   -- "Poda general", etc.
        Categoria                   NVARCHAR(100)   NOT NULL,  -- FFase1, FFase2, Crema...

        -- Métricas
        Cantidad                    DECIMAL(12, 2)  NULL,
        Dia                         INT             NULL,

        -- Metadatos
        Evaluador                   NVARCHAR(150)   NULL,
        Fecha_Evento                DATETIME2       NOT NULL,
        Fecha_Sistema               DATETIME2       NOT NULL DEFAULT GETDATE(),
        Estado_DQ                   NVARCHAR(20)    NOT NULL DEFAULT 'OK',

        -- Rastreo a Bronce
        id_origen_rastreo           BIGINT          NULL
    );

    PRINT '✓ Silver.Fact_Ciclos_Fenologicos creada.';
END
ELSE
BEGIN
    PRINT '· Silver.Fact_Ciclos_Fenologicos ya existe — sin cambios.';
END
GO

-- Índice UNIQUE filtrado para garantizar el grain (mismo patrón que Fact_Ciclo_Poda)
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_Fact_Ciclos_Fenologicos_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclos_Fenologicos')
)
BEGIN
    CREATE UNIQUE INDEX UX_Fact_Ciclos_Fenologicos_Grain
    ON Silver.Fact_Ciclos_Fenologicos
        (ID_Geografia, ID_Tiempo, ID_Variedad, Cama, Tipo_Evaluacion, Categoria)
    WHERE Cama IS NOT NULL AND Categoria IS NOT NULL;

    PRINT '✓ UX_Fact_Ciclos_Fenologicos_Grain creado.';
END
GO

-- Índices de soporte para queries comunes
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Fact_Ciclos_Fenologicos_Fecha'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclos_Fenologicos')
)
BEGIN
    CREATE INDEX IX_Fact_Ciclos_Fenologicos_Fecha
    ON Silver.Fact_Ciclos_Fenologicos (Fecha_Evento DESC);
END
GO
