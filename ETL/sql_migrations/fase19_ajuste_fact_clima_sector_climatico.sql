IF OBJECT_ID(N'Silver.Fact_Telemetria_Clima', N'U') IS NOT NULL
BEGIN
    DROP TABLE Silver.Fact_Telemetria_Clima;
END;
GO

CREATE TABLE Silver.Fact_Telemetria_Clima
(
    ID_Telemetria_Clima    BIGINT IDENTITY(1,1) NOT NULL,
    ID_Tiempo              INT NOT NULL,
    Sector_Climatico       NVARCHAR(50) NOT NULL,
    Temperatura_Max_C      DECIMAL(8,2) NULL,
    Temperatura_Min_C      DECIMAL(8,2) NULL,
    Humedad_Relativa_Pct   DECIMAL(8,2) NULL,
    Precipitacion_mm       DECIMAL(12,3) NULL,
    VPD                    DECIMAL(8,3) NULL,
    Radiacion_Solar        DECIMAL(12,3) NULL,
    Fecha_Evento           DATETIME2 NOT NULL,
    Fecha_Sistema          DATETIME2 NOT NULL
        CONSTRAINT DF_Fact_Telemetria_Clima_Fecha_Sistema DEFAULT (SYSDATETIME()),

    CONSTRAINT PK_Fact_Telemetria_Clima
        PRIMARY KEY CLUSTERED (ID_Telemetria_Clima),

    CONSTRAINT FK_Fact_Telemetria_Clima_Tiempo
        FOREIGN KEY (ID_Tiempo)
        REFERENCES Silver.Dim_Tiempo (ID_Tiempo),

    CONSTRAINT CK_Fact_Telemetria_Clima_Sector
        CHECK (LEN(LTRIM(RTRIM(Sector_Climatico))) >= 1),

    CONSTRAINT CK_Fact_Telemetria_Clima_Humedad
        CHECK (Humedad_Relativa_Pct IS NULL OR (Humedad_Relativa_Pct >= 0 AND Humedad_Relativa_Pct <= 100))
);
GO

CREATE INDEX IX_Fact_Telemetria_Clima_Tiempo_Sector
    ON Silver.Fact_Telemetria_Clima (ID_Tiempo, Sector_Climatico);
GO

CREATE INDEX IX_Fact_Telemetria_Clima_Sector_Fecha
    ON Silver.Fact_Telemetria_Clima (Sector_Climatico, Fecha_Evento);
GO

IF OBJECT_ID(N'Gold.Mart_Clima', N'U') IS NOT NULL
BEGIN
    DROP TABLE Gold.Mart_Clima;
END;
GO

CREATE TABLE Gold.Mart_Clima
(
    ID_Tiempo            INT NOT NULL,
    Sector_Climatico     NVARCHAR(50) NOT NULL,
    Semana_ISO           INT NOT NULL,
    Temp_Max_Promedio    DECIMAL(12,3) NULL,
    Temp_Min_Promedio    DECIMAL(12,3) NULL,
    VPD_Promedio         DECIMAL(12,3) NULL,
    Humedad_Promedio     DECIMAL(12,3) NULL,
    Precipitacion_Total  DECIMAL(14,3) NULL
);
GO

CREATE INDEX IX_Mart_Clima_Tiempo_Sector
    ON Gold.Mart_Clima (ID_Tiempo, Sector_Climatico);
GO
