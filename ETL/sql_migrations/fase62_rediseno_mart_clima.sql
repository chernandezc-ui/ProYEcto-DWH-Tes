/* ==========================================================================
   fase62_rediseno_mart_clima.sql
   --------------------------------------------------------------------------
   Rediseña Gold.Mart_Clima. GDD se calcula como SUM((T-10) * dt_dias)
   por día y sector, con dt = LAG(Fecha_Hora) particionado por sector
   (replica exactamente el cálculo de R con difftime(DateTime, lag(DateTime))).
   ========================================================================== */
SET XACT_ABORT ON;

IF OBJECT_ID(N'Gold.Mart_Clima', N'U') IS NOT NULL
    DROP TABLE Gold.Mart_Clima;
GO

CREATE TABLE Gold.Mart_Clima
(
    ID_Tiempo                    INT           NOT NULL,
    Sector_Climatico             NVARCHAR(100) NOT NULL,
    Fundo                        NVARCHAR(100) NOT NULL
        CONSTRAINT DF_Mart_Clima_Fundo DEFAULT (N'ARANDANO ACP'),
    ID_Campana                   INT           NOT NULL,
    Semana_ISO                   INT           NOT NULL,
    Temp_Promedio_Diaria         DECIMAL(6,2)  NULL,
    Temp_Maxima_Dia              DECIMAL(6,2)  NULL,
    Temp_Minima_Dia              DECIMAL(6,2)  NULL,
    Humedad_Promedio             DECIMAL(6,2)  NULL,
    Precipitacion_Total          DECIMAL(10,2) NULL,
    Indice_UV_Max                DECIMAL(5,2)  NULL,
    Indice_UV_Min                DECIMAL(5,2)  NULL,
    Radiacion_Solar_Prom_Diurna  DECIMAL(8,2)  NULL,
    Radiacion_Solar_Max          DECIMAL(8,2)  NULL,
    VPD_Promedio                 DECIMAL(6,3)  NULL,
    GDD                          DECIMAL(8,3)  NULL
);
GO

CREATE INDEX IX_Mart_Clima_Tiempo_Sector
    ON Gold.Mart_Clima (ID_Tiempo, Sector_Climatico);
GO

-- Seed del fundo por defecto. Cualquier fila sin fundo cae aquí vía
-- mdm.lookup.FUNDO_DEFECTO en resolver_geografia (default global del pipeline).
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Fundo_Catalogo WHERE Fundo = N'ARANDANO ACP')
    INSERT INTO Silver.Dim_Fundo_Catalogo (Fundo) VALUES (N'ARANDANO ACP');
GO
