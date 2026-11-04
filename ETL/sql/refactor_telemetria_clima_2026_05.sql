/* ===========================================================================
   refactor_telemetria_clima_2026_05.sql
   Reemplaza Bronce.Reporte_Clima y Bronce.Variables_Meteorologicas (ambas
   vacías) por una sola tabla Bronce.Telemetria_Clima alineada al Excel
   Meteorologia_Historica.xlsx (granularidad horaria).
   Reconstruye Silver.Fact_Telemetria_Clima con grano diario agregado.
   Idempotente: todos los DROP usan IF EXISTS.
   ========================================================================== */
SET XACT_ABORT ON;

/* -- 1. Soltar dependencias y tablas viejas ------------------------------- */
IF OBJECT_ID('Silver.vFact_Telemetria_Clima','V') IS NOT NULL
    DROP VIEW Silver.vFact_Telemetria_Clima;

IF OBJECT_ID('Silver.Fact_Telemetria_Clima','U') IS NOT NULL
    DROP TABLE Silver.Fact_Telemetria_Clima;

IF OBJECT_ID('Bronce.Reporte_Clima','U') IS NOT NULL
    DROP TABLE Bronce.Reporte_Clima;

IF OBJECT_ID('Bronce.Variables_Meteorologicas','U') IS NOT NULL
    DROP TABLE Bronce.Variables_Meteorologicas;

/* -- 2. Crear Bronce.Telemetria_Clima (horario, todo Raw NVARCHAR) -------- */
CREATE TABLE Bronce.Telemetria_Clima (
    ID_Telemetria_Clima     BIGINT IDENTITY(1,1) NOT NULL,
    Semana_Raw              NVARCHAR(20)  NULL,
    FechaHora_Raw           NVARCHAR(50)  NULL,
    Sector_Raw              NVARCHAR(100) NULL,
    Temp_Exterior_Raw       NVARCHAR(30)  NULL,
    Temp_Maxima_Raw         NVARCHAR(30)  NULL,
    Temp_Minima_Raw         NVARCHAR(30)  NULL,
    Humedad_Externa_Raw     NVARCHAR(30)  NULL,
    Punto_Rocio_Raw         NVARCHAR(30)  NULL,
    Velocidad_Max_KmH_Raw   NVARCHAR(30)  NULL,
    Velocidad_Max_Ms_Raw    NVARCHAR(30)  NULL,
    Lluvia_Raw              NVARCHAR(30)  NULL,
    Intensidad_Lluvia_Raw   NVARCHAR(30)  NULL,
    Radiacion_Solar_Raw     NVARCHAR(30)  NULL,
    Indice_UV_Raw           NVARCHAR(30)  NULL,
    Evapotranspiracion_Raw  NVARCHAR(30)  NULL,
    Indice_Calor_Raw        NVARCHAR(30)  NULL,
    Calor_Raw               NVARCHAR(30)  NULL,
    Grados_Dia_Raw          NVARCHAR(30)  NULL,
    Nombre_Archivo          NVARCHAR(260) NULL,
    Fecha_Sistema           DATETIME2(0)  NOT NULL CONSTRAINT DF_BTC_Fecha_Sistema DEFAULT (SYSUTCDATETIME()),
    Estado_Carga            VARCHAR(20)   NOT NULL CONSTRAINT DF_BTC_Estado_Carga DEFAULT ('CARGADO'),
    CONSTRAINT PK_Bronce_Telemetria_Clima PRIMARY KEY CLUSTERED (ID_Telemetria_Clima)
);

CREATE INDEX IX_BTC_Estado ON Bronce.Telemetria_Clima(Estado_Carga);
CREATE INDEX IX_BTC_FechaHora ON Bronce.Telemetria_Clima(FechaHora_Raw);

/* -- 3. Crear Silver.Fact_Telemetria_Clima (diario agregado) -------------- */
CREATE TABLE Silver.Fact_Telemetria_Clima (
    ID_Telemetria_Clima         BIGINT IDENTITY(1,1) NOT NULL,
    ID_Tiempo                   INT           NOT NULL,
    Sector_Climatico            NVARCHAR(100) NOT NULL,
    Temperatura_Max_C           DECIMAL(5,2)  NULL,
    Temperatura_Min_C           DECIMAL(5,2)  NULL,
    Temperatura_Prom_C          DECIMAL(5,2)  NULL,
    Humedad_Relativa_Prom_Pct   DECIMAL(5,2)  NULL,
    Punto_Rocio_Prom_C          DECIMAL(5,2)  NULL,
    Velocidad_Viento_Max_KmH    DECIMAL(6,2)  NULL,
    Lluvia_Total_mm             DECIMAL(8,2)  NULL,
    Radiacion_Solar_Prom_Wm2    DECIMAL(8,2)  NULL,
    Indice_UV_Max               DECIMAL(5,2)  NULL,
    Evapotranspiracion_Total_mm DECIMAL(6,2)  NULL,
    Grados_Dia_Total            DECIMAL(7,2)  NULL,
    Fecha_Evento                DATETIME2(0)  NOT NULL,
    Fecha_Sistema               DATETIME2(0)  NOT NULL CONSTRAINT DF_FTC_Fecha_Sistema DEFAULT (SYSUTCDATETIME()),
    ID_Campana                  INT           NULL,
    CONSTRAINT PK_Fact_Telemetria_Clima PRIMARY KEY CLUSTERED (ID_Telemetria_Clima),
    CONSTRAINT UQ_Fact_Telemetria_Clima_Grain UNIQUE (ID_Tiempo, Sector_Climatico),
    CONSTRAINT CK_Fact_Telemetria_Clima_Sector  CHECK (LEN(LTRIM(RTRIM(Sector_Climatico))) >= 1),
    CONSTRAINT CK_Fact_Telemetria_Clima_Humedad CHECK (Humedad_Relativa_Prom_Pct IS NULL OR Humedad_Relativa_Prom_Pct BETWEEN 0 AND 100)
);

CREATE INDEX IX_FTC_Tiempo  ON Silver.Fact_Telemetria_Clima(ID_Tiempo);
CREATE INDEX IX_FTC_Sector  ON Silver.Fact_Telemetria_Clima(Sector_Climatico);
CREATE INDEX IX_FTC_Campana ON Silver.Fact_Telemetria_Clima(ID_Campana);

/* -- 4. Recrear vista ----------------------------------------------------- */
GO
CREATE VIEW Silver.vFact_Telemetria_Clima AS
SELECT
    f.ID_Telemetria_Clima,
    f.ID_Tiempo,
    t.Fecha,
    t.Anio, t.Mes, t.Semana_ISO,
    f.Sector_Climatico,
    f.Temperatura_Max_C,
    f.Temperatura_Min_C,
    f.Temperatura_Prom_C,
    f.Humedad_Relativa_Prom_Pct,
    f.Punto_Rocio_Prom_C,
    f.Velocidad_Viento_Max_KmH,
    f.Lluvia_Total_mm,
    f.Radiacion_Solar_Prom_Wm2,
    f.Indice_UV_Max,
    f.Evapotranspiracion_Total_mm,
    f.Grados_Dia_Total,
    f.Fecha_Evento,
    f.Fecha_Sistema,
    f.ID_Campana
FROM Silver.Fact_Telemetria_Clima f
JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = f.ID_Tiempo;
GO
