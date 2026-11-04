/*
ddl_marts_v2.sql
================
Crea las 7 nuevas tablas de la capa Gold (Marts).
*/

-- 2.1 Gold.Mart_Fisiologia
IF OBJECT_ID('Gold.Mart_Fisiologia', 'U') IS NOT NULL DROP TABLE Gold.Mart_Fisiologia;
CREATE TABLE Gold.Mart_Fisiologia (
    ID_Mart_Fisiologia BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    Tercio NVARCHAR(20),
    Brotes_Productivos_Promedio DECIMAL(10,2),
    Brotes_Vegetativos_Promedio DECIMAL(10,2),
    Hinchadas_Promedio DECIMAL(10,2),
    Productivas_Promedio DECIMAL(10,2),
    Total_Organos_Promedio DECIMAL(10,2),
    Ratio_Productivo_Veg AS (CAST(Brotes_Productivos_Promedio AS DECIMAL(10,2)) / NULLIF(Brotes_Vegetativos_Promedio, 0)),
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);

-- 2.2 Gold.Mart_Evaluacion_Vegetativa
IF OBJECT_ID('Gold.Mart_Evaluacion_Vegetativa', 'U') IS NOT NULL DROP TABLE Gold.Mart_Evaluacion_Vegetativa;
CREATE TABLE Gold.Mart_Evaluacion_Vegetativa (
    ID_Mart_Vegetativa BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    Tipo_Evaluacion NVARCHAR(100),
    Plantas_Evaluadas_Total INT,
    Plantas_En_Floracion_Total INT,
    Pct_Floracion_Promedio DECIMAL(8,2),
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);

-- 2.3 Gold.Mart_Maduracion
IF OBJECT_ID('Gold.Mart_Maduracion', 'U') IS NOT NULL DROP TABLE Gold.Mart_Maduracion;
CREATE TABLE Gold.Mart_Maduracion (
    ID_Mart_Maduracion BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    ID_Estado_Fenologico INT,
    Estado_Fenologico NVARCHAR(100),
    ID_Cinta INT,
    Color_Cinta NVARCHAR(50),
    Organos_Observados INT,
    Dias_Pasados_Promedio DECIMAL(8,2),
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);

-- 2.4 Gold.Mart_Tasa_Crecimiento
IF OBJECT_ID('Gold.Mart_Tasa_Crecimiento', 'U') IS NOT NULL DROP TABLE Gold.Mart_Tasa_Crecimiento;
CREATE TABLE Gold.Mart_Tasa_Crecimiento (
    ID_Mart_Crecimiento BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    Tipo_Evaluacion NVARCHAR(100),
    Estado_Vegetativo NVARCHAR(100),
    Tipo_Tallo NVARCHAR(50),
    Medida_Crecimiento_Promedio DECIMAL(10,4),
    Medida_Crecimiento_Max DECIMAL(10,4),
    Dias_Desde_Poda_Promedio DECIMAL(8,2),
    Cantidad_Mediciones INT,
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);
CREATE INDEX IX_Mart_Crecimiento_Tiempo_Variedad ON Gold.Mart_Tasa_Crecimiento (ID_Tiempo, ID_Variedad);

-- 2.5 Gold.Mart_Induccion_Floral
IF OBJECT_ID('Gold.Mart_Induccion_Floral', 'U') IS NOT NULL DROP TABLE Gold.Mart_Induccion_Floral;
CREATE TABLE Gold.Mart_Induccion_Floral (
    ID_Mart_Induccion BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    Tipo_Evaluacion NVARCHAR(100),
    Pct_Plantas_Con_Induccion_Prom DECIMAL(5,2),
    Pct_Brotes_Con_Induccion_Prom DECIMAL(5,2),
    Pct_Brotes_Con_Flor_Prom DECIMAL(5,2),
    Brotes_Totales INT,
    Brotes_Con_Flor INT,
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);

-- 2.6 Gold.Mart_Ciclo_Poda
IF OBJECT_ID('Gold.Mart_Ciclo_Poda', 'U') IS NOT NULL DROP TABLE Gold.Mart_Ciclo_Poda;
CREATE TABLE Gold.Mart_Ciclo_Poda (
    ID_Mart_Poda BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    Tipo_Evaluacion NVARCHAR(100),
    Tallos_Planta_Total DECIMAL(8,2),
    Longitud_Tallo_Total DECIMAL(8,2),
    Diametro_Tallo_Total DECIMAL(8,2),
    Ramilla_Planta_Total DECIMAL(8,2),
    Tocones_Planta_Total DECIMAL(8,2),
    Cortes_Defectuosos_Total DECIMAL(8,2),
    Altura_Poda_Total DECIMAL(8,2),
    N_Muestras INT NOT NULL DEFAULT 0,
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);

-- 2.7 Gold.Mart_Peladas
IF OBJECT_ID('Gold.Mart_Peladas', 'U') IS NOT NULL DROP TABLE Gold.Mart_Peladas;
CREATE TABLE Gold.Mart_Peladas (
    ID_Mart_Peladas BIGINT IDENTITY(1,1) PRIMARY KEY,
    ID_Tiempo INT NOT NULL,
    ID_Geografia INT NOT NULL,
    ID_Variedad INT NOT NULL,
    ID_Campana INT NOT NULL,
    Fundo NVARCHAR(MAX),
    Modulo INT,
    Variedad NVARCHAR(100),
    Semana_ISO INT,
    Botones_Florales_Total INT,
    Flores_Total INT,
    Bayas_Pequenas_Total INT,
    Bayas_Grandes_Total INT,
    Fase_1_Total INT,
    Fase_2_Total INT,
    Bayas_Cremas_Total INT,
    Bayas_Maduras_Total INT,
    Bayas_Cosechables_Total INT,
    Pct_Cosechable AS (CAST(Bayas_Cosechables_Total AS DECIMAL(10,2)) / NULLIF(Botones_Florales_Total + Flores_Total + Bayas_Pequenas_Total + Bayas_Grandes_Total + Fase_1_Total + Fase_2_Total + Bayas_Cremas_Total + Bayas_Maduras_Total, 0) * 100),
    Plantas_Productivas_Total INT,
    Plantas_No_Productivas_Total INT,
    Muestras_Total INT,
    Fecha_Actualizacion DATETIME2 DEFAULT SYSDATETIME()
);
