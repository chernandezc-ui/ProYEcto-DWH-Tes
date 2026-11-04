/* ===========================================================================
   refactor_telemetria_clima_silver_horario.sql
   Reemplaza Silver.Fact_Telemetria_Clima diario por uno HORARIO tipado
   (mismo grano que Bronce). Las agregaciones SUM/MIN/MAX/AVG se haran en
   un mart Gold posterior.
   Grano: (Sector_Climatico, Fecha_Hora) UNIQUE.
   ========================================================================== */
SET XACT_ABORT ON;

IF OBJECT_ID('Silver.vFact_Telemetria_Clima','V') IS NOT NULL
    DROP VIEW Silver.vFact_Telemetria_Clima;

IF OBJECT_ID('Silver.Fact_Telemetria_Clima','U') IS NOT NULL
    DROP TABLE Silver.Fact_Telemetria_Clima;

CREATE TABLE Silver.Fact_Telemetria_Clima (
    ID_Telemetria_Clima       BIGINT IDENTITY(1,1) NOT NULL,
    ID_Tiempo                 INT           NOT NULL,
    Fecha_Hora                DATETIME2(0)  NOT NULL,
    Sector_Climatico          NVARCHAR(100) NOT NULL,
    Semana                    SMALLINT      NULL,
    Temp_Exterior_C           DECIMAL(5,2)  NULL,
    Temp_Maxima_C             DECIMAL(5,2)  NULL,
    Temp_Minima_C             DECIMAL(5,2)  NULL,
    Humedad_Externa_Pct       DECIMAL(5,2)  NULL,
    Punto_Rocio_C             DECIMAL(5,2)  NULL,
    Velocidad_Max_KmH         DECIMAL(6,2)  NULL,
    Velocidad_Max_Ms          DECIMAL(6,2)  NULL,
    Lluvia_mm                 DECIMAL(7,2)  NULL,
    Intensidad_Lluvia_mm_hr   DECIMAL(7,2)  NULL,
    Radiacion_Solar_Wm2       DECIMAL(8,2)  NULL,
    Indice_UV                 DECIMAL(5,2)  NULL,
    Evapotranspiracion_mm     DECIMAL(6,3)  NULL,
    Indice_Calor              DECIMAL(5,2)  NULL,
    Calor                     DECIMAL(5,2)  NULL,
    Grados_Dia                DECIMAL(6,3)  NULL,
    Fecha_Sistema             DATETIME2(0)  NOT NULL CONSTRAINT DF_FTC_Fecha_Sistema DEFAULT (SYSUTCDATETIME()),
    ID_Campana                INT           NULL,
    CONSTRAINT PK_Fact_Telemetria_Clima PRIMARY KEY CLUSTERED (ID_Telemetria_Clima),
    CONSTRAINT UQ_Fact_Telemetria_Clima_Grain UNIQUE (Sector_Climatico, Fecha_Hora),
    CONSTRAINT CK_Fact_Telemetria_Clima_Sector  CHECK (LEN(LTRIM(RTRIM(Sector_Climatico))) >= 1),
    CONSTRAINT CK_Fact_Telemetria_Clima_Humedad CHECK (Humedad_Externa_Pct IS NULL OR Humedad_Externa_Pct BETWEEN 0 AND 100)
);

CREATE INDEX IX_FTC_Tiempo   ON Silver.Fact_Telemetria_Clima(ID_Tiempo);
CREATE INDEX IX_FTC_FecHora  ON Silver.Fact_Telemetria_Clima(Fecha_Hora);
CREATE INDEX IX_FTC_Sector   ON Silver.Fact_Telemetria_Clima(Sector_Climatico);
CREATE INDEX IX_FTC_Campana  ON Silver.Fact_Telemetria_Clima(ID_Campana);

GO
CREATE VIEW Silver.vFact_Telemetria_Clima AS
SELECT
    f.ID_Telemetria_Clima,
    f.ID_Tiempo,
    t.Fecha,
    t.Anio, t.Mes, t.Semana_ISO,
    f.Fecha_Hora,
    f.Sector_Climatico,
    f.Semana,
    f.Temp_Exterior_C,
    f.Temp_Maxima_C,
    f.Temp_Minima_C,
    f.Humedad_Externa_Pct,
    f.Punto_Rocio_C,
    f.Velocidad_Max_KmH,
    f.Velocidad_Max_Ms,
    f.Lluvia_mm,
    f.Intensidad_Lluvia_mm_hr,
    f.Radiacion_Solar_Wm2,
    f.Indice_UV,
    f.Evapotranspiracion_mm,
    f.Indice_Calor,
    f.Calor,
    f.Grados_Dia,
    f.Fecha_Sistema,
    f.ID_Campana
FROM Silver.Fact_Telemetria_Clima f
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = f.ID_Tiempo;
GO
