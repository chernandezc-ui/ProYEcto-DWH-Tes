-- ========================================================================
-- DDL . ACP_DataWarehose_Proyecciones - Agricola Cerro Prieto
-- v3 - Sincronizado con la BD real (autogenerado por ETL/tools/generate_docs.py)
-- Collation: Modern_Spanish_CI_AS
-- ========================================================================
USE master;
GO

IF DB_ID('ACP_DataWarehose_Proyecciones') IS NULL
BEGIN
    CREATE DATABASE ACP_DataWarehose_Proyecciones
        COLLATE Modern_Spanish_CI_AS;
END
GO
USE ACP_DataWarehose_Proyecciones;
GO

-- ========================================================================
-- SCHEMAS
-- ========================================================================
IF SCHEMA_ID('Admin') IS NULL EXEC('CREATE SCHEMA [Admin]');
GO
IF SCHEMA_ID('Auditoria') IS NULL EXEC('CREATE SCHEMA [Auditoria]');
GO
IF SCHEMA_ID('Bronce') IS NULL EXEC('CREATE SCHEMA [Bronce]');
GO
IF SCHEMA_ID('Config') IS NULL EXEC('CREATE SCHEMA [Config]');
GO
IF SCHEMA_ID('Control') IS NULL EXEC('CREATE SCHEMA [Control]');
GO
IF SCHEMA_ID('Gold') IS NULL EXEC('CREATE SCHEMA [Gold]');
GO
IF SCHEMA_ID('MDM') IS NULL EXEC('CREATE SCHEMA [MDM]');
GO
IF SCHEMA_ID('Seguridad') IS NULL EXEC('CREATE SCHEMA [Seguridad]');
GO
IF SCHEMA_ID('Silver') IS NULL EXEC('CREATE SCHEMA [Silver]');
GO

-- ========================================================================
-- TABLAS
-- ========================================================================

-- ---- Schema [Bronce] . 25 tablas ----

IF OBJECT_ID('[Bronce].[Calibres]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Calibres] (
    [ID_Calibres] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Calibres] PRIMARY KEY ([ID_Calibres])
);
END
GO

IF OBJECT_ID('[Bronce].[Censo_Plantas]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Censo_Plantas] (
    [ID_Censo_Plantas] BIGINT IDENTITY(1,1) NOT NULL,
    [Campana_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Area_Raw] NVARCHAR(30) NULL,
    [Plantas_Raw] NVARCHAR(30) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT ('CARGADO'),
    CONSTRAINT [PK_Bronce_Censo_Plantas] PRIMARY KEY ([ID_Censo_Plantas])
);
END
GO

IF OBJECT_ID('[Bronce].[Ciclos_Fenologicos]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Ciclos_Fenologicos] (
    [ID_Ciclo_Fenologico] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Organo_Raw] NVARCHAR(50) NULL,
    [Color_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [FechaSubida_Raw] NVARCHAR(50) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(50) NULL DEFAULT ('CARGADO'),
    CONSTRAINT [PK_Bronce_Ciclos_Fenologicos] PRIMARY KEY ([ID_Ciclo_Fenologico])
);
END
GO

IF OBJECT_ID('[Bronce].[Cierre_Mapas_Cosecha]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Cierre_Mapas_Cosecha] (
    [ID_Cierre_Cosecha] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Cierre_Mapas_Cosecha] PRIMARY KEY ([ID_Cierre_Cosecha])
);
END
GO

IF OBJECT_ID('[Bronce].[Consolidado_Tareos]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Consolidado_Tareos] (
    [ID_Tareo] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [IDPersonalGeneral_Raw] NVARCHAR(20) NULL,
    [DNIResponsable_Raw] NVARCHAR(20) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Actividad_Raw] NVARCHAR(150) NULL,
    [Labor_Raw] NVARCHAR(150) NULL,
    [HorasTrabajadas_Raw] NVARCHAR(20) NULL,
    [IDPlanilla_Raw] NVARCHAR(20) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Consolidado_Tareos] PRIMARY KEY ([ID_Tareo])
);
END
GO

IF OBJECT_ID('[Bronce].[Conteo_Fruta]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Conteo_Fruta] (
    [ID_Conteo_Fruta] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Tipo_Evaluacion_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fecha_Registro_Raw] NVARCHAR(50) NULL,
    [Punto_Raw] NVARCHAR(50) NULL,
    [BotonesFlorales_Raw] NVARCHAR(50) NULL,
    [Flores_Raw] NVARCHAR(50) NULL,
    [BayasPequenas_Raw] NVARCHAR(50) NULL,
    [BayasGrandes_Raw] NVARCHAR(50) NULL,
    [Fase1_Raw] NVARCHAR(50) NULL,
    [Fase2_Raw] NVARCHAR(50) NULL,
    [BayasCremas_Raw] NVARCHAR(50) NULL,
    [BayasMaduras_Raw] NVARCHAR(50) NULL,
    [BayasCosechables_Raw] NVARCHAR(50) NULL,
    [YemasActivadas_Raw] NVARCHAR(50) NULL,
    [PlantasProductivas_Raw] NVARCHAR(50) NULL,
    [PlantasNoProductivas_Raw] NVARCHAR(50) NULL,
    [Muestras_Raw] NVARCHAR(50) NULL,
    [DNI_Raw] NVARCHAR(50) NULL,
    [Nombres_Raw] NVARCHAR(150) NULL,
    [Fecha_Subida_Raw] NVARCHAR(50) NULL,
    [Fundo_Raw] NVARCHAR(50) NULL,
    [Sector_Raw] NVARCHAR(50) NULL,
    CONSTRAINT [PK_Bronce_Conteo_Fruta] PRIMARY KEY ([ID_Conteo_Fruta])
);
END
GO

IF OBJECT_ID('[Bronce].[Cosecha_SAP]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Cosecha_SAP] (
    [ID_Cosecha_SAP] BIGINT IDENTITY(1,1) NOT NULL,
    [Campana_Raw] NVARCHAR(50) NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Semana_Raw] NVARCHAR(20) NULL,
    [Sector_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Kg_Total_Raw] NVARCHAR(30) NULL,
    [Area_Raw] NVARCHAR(30) NULL,
    [Plantas_Raw] NVARCHAR(30) NULL,
    [SemCal_Raw] NVARCHAR(20) NULL,
    [Semana_Cosecha_Raw] NVARCHAR(20) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT ('CARGADO'),
    CONSTRAINT [PK_Bronce_Cosecha_SAP] PRIMARY KEY ([ID_Cosecha_SAP])
);
END
GO

IF OBJECT_ID('[Bronce].[Dashboard]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Dashboard] (
    [ID_Dashboard] BIGINT IDENTITY(1,1) NOT NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Ruta_Origen] NVARCHAR(500) NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Dashboard] PRIMARY KEY ([ID_Dashboard])
);
END
GO

IF OBJECT_ID('[Bronce].[Data_SAP]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Data_SAP] (
    [ID_Data_SAP] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Cosecha_Raw] NVARCHAR(50) NULL,
    [Consumidor_PEP_Raw] NVARCHAR(100) NULL,
    [Des_Consumidor_PEP_Raw] NVARCHAR(200) NULL,
    [Variedad_Codigo_Raw] NVARCHAR(50) NULL,
    [Des_Variedad_Raw] NVARCHAR(100) NULL,
    [Material_Codigo_Raw] NVARCHAR(50) NULL,
    [Descripcion_Material_Raw] NVARCHAR(200) NULL,
    [Codigo_Cliente_Raw] NVARCHAR(30) NULL,
    [Responsable_Raw] NVARCHAR(150) NULL,
    [Lote_Raw] NVARCHAR(50) NULL,
    [Almacen_Raw] NVARCHAR(50) NULL,
    [Peso_Bruto_Raw] NVARCHAR(30) NULL,
    [Peso_Tara_Raw] NVARCHAR(30) NULL,
    [Peso_Neto_Raw] NVARCHAR(30) NULL,
    [Cantidad_Jabas_Raw] NVARCHAR(20) NULL,
    [Doc_Remision_Raw] NVARCHAR(50) NULL,
    [Fecha_Recepcion_Raw] NVARCHAR(50) NULL,
    [FechaSubida_Raw] NVARCHAR(50) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fecha_Raw] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [Modulo_Raw] NVARCHAR(MAX) NULL,
    [Variedad_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Data_SAP] PRIMARY KEY ([ID_Data_SAP])
);
END
GO

IF OBJECT_ID('[Bronce].[Evaluacion_Calidad_Poda]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Evaluacion_Calidad_Poda] (
    [ID_Evaluacion_Poda] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Tipo_Evaluacion_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [TallosPlanta_Raw] NVARCHAR(MAX) NULL,
    [LongitudTallo_Raw] NVARCHAR(MAX) NULL,
    [DiametroTallo_Raw] NVARCHAR(MAX) NULL,
    [RamillaPlanta_Raw] NVARCHAR(MAX) NULL,
    [ToconesPlanta_Raw] NVARCHAR(MAX) NULL,
    [CortesDefectuosos_Raw] NVARCHAR(MAX) NULL,
    [AlturaPoda_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Evaluacion_Calidad_Poda] PRIMARY KEY ([ID_Evaluacion_Poda])
);
END
GO

IF OBJECT_ID('[Bronce].[Evaluacion_Pesos]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Evaluacion_Pesos] (
    [ID_Evaluacion_Pesos] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluacion_Raw] NVARCHAR(50) NULL,
    [PesoBaya_Raw] NVARCHAR(20) NULL,
    [CantMuestra_Raw] NVARCHAR(20) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [DNI_Raw] NVARCHAR(MAX) NULL,
    [Nombres_Raw] NVARCHAR(MAX) NULL,
    [Cremas_Raw] NVARCHAR(MAX) NULL,
    [Maduras_Raw] NVARCHAR(MAX) NULL,
    [Cosechables_Raw] NVARCHAR(MAX) NULL,
    [Estado_Carga] NVARCHAR(50) NULL DEFAULT ('CARGADO'),
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [BayasPequenas_Raw] NVARCHAR(MAX) NULL,
    [PesoBayasPequenas_Raw] NVARCHAR(MAX) NULL,
    [BayasPequenas2_Raw] NVARCHAR(MAX) NULL,
    [BayasGrandes_Raw] NVARCHAR(MAX) NULL,
    [PesoBayasGrandes_Raw] NVARCHAR(MAX) NULL,
    [BayasFase1_Raw] NVARCHAR(MAX) NULL,
    [PesoBayasFase1_Raw] NVARCHAR(MAX) NULL,
    [BayasFase2_Raw] NVARCHAR(MAX) NULL,
    [PesoBayasFase2_Raw] NVARCHAR(MAX) NULL,
    [PesoCremas_Raw] NVARCHAR(MAX) NULL,
    [PesoMaduras_Raw] NVARCHAR(MAX) NULL,
    [PesoCosechables_Raw] NVARCHAR(MAX) NULL,
    [Fecha_Subida_Raw] NVARCHAR(MAX) NULL,
    [Cama_Raw] NVARCHAR(MAX) NULL,
    [PesoBayasPequenas2_Raw] NVARCHAR(255) NULL,
    CONSTRAINT [PK_Bronce_Evaluacion_Pesos] PRIMARY KEY ([ID_Evaluacion_Pesos])
);
END
GO

IF OBJECT_ID('[Bronce].[Evaluacion_Vegetativa]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Evaluacion_Vegetativa] (
    [ID_Evaluacion_Veg] BIGINT IDENTITY(1,1) NOT NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT ('CARGADO'),
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Campana_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Cama_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [DNI_Raw] NVARCHAR(20) NULL,
    [Semanas_Poda_Raw] NVARCHAR(20) NULL,
    [Altura_Raw] NVARCHAR(50) NULL,
    [Tallos_Basales_Raw] NVARCHAR(50) NULL,
    [Tallos_Basales_Nuevos_Raw] NVARCHAR(50) NULL,
    [Muestra_Plantas_Raw] NVARCHAR(20) NULL,
    [Piso1_Brotes_Raw] NVARCHAR(50) NULL,
    [Piso1_Productivos_Raw] NVARCHAR(50) NULL,
    [Piso1_Diametro_Raw] NVARCHAR(50) NULL,
    [Piso2_Brotes_Raw] NVARCHAR(50) NULL,
    [Piso2_Productivos_Raw] NVARCHAR(50) NULL,
    [Piso2_Diametro_Raw] NVARCHAR(50) NULL,
    [Piso3_Brotes_Raw] NVARCHAR(50) NULL,
    [Piso3_Productivos_Raw] NVARCHAR(50) NULL,
    [Piso3_Diametro_Raw] NVARCHAR(50) NULL,
    [Piso4_Brotes_Raw] NVARCHAR(50) NULL,
    [Piso4_Productivos_Raw] NVARCHAR(50) NULL,
    [Piso4_Diametro_Raw] NVARCHAR(50) NULL,
    [Piso5_Brotes_Raw] NVARCHAR(50) NULL,
    [Piso5_Productivos_Raw] NVARCHAR(50) NULL,
    [Piso5_Diametro_Raw] NVARCHAR(50) NULL,
    [Brotes_Productivos_Total_Raw] NVARCHAR(50) NULL,
    [Diametro_Tallo_Basal_Raw] NVARCHAR(50) NULL,
    [Fecha_Registro_Movil_Raw] NVARCHAR(50) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Evaluacion_Vegetativa] PRIMARY KEY ([ID_Evaluacion_Veg])
);
END
GO

IF OBJECT_ID('[Bronce].[Fiscalizacion]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Fiscalizacion] (
    [ID_Fiscalizacion] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [DNI_Raw] NVARCHAR(20) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Fiscalizacion] PRIMARY KEY ([ID_Fiscalizacion])
);
END
GO

IF OBJECT_ID('[Bronce].[Fisiologia]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Fisiologia] (
    [ID_Fisiologia] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Brote_Raw] NVARCHAR(10) NULL,
    [Tercio_Raw] NVARCHAR(20) NULL,
    [Hinchadas_Raw] NVARCHAR(20) NULL,
    [Productivas_Raw] NVARCHAR(20) NULL,
    [Total_Org_Raw] NVARCHAR(20) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [BrotesProd_Raw] NVARCHAR(100) NULL,
    [BrotesVeg_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(200) NULL,
    [Sector_Raw] NVARCHAR(200) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Fisiologia] PRIMARY KEY ([ID_Fisiologia])
);
END
GO

IF OBJECT_ID('[Bronce].[Floracion]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Floracion] (
    [ID_Evaluacion_Vegetativa] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(100) NULL,
    [DNI_Raw] NVARCHAR(20) NULL,
    [Fecha_Subida_Raw] NVARCHAR(100) NULL,
    [Nombres_Raw] NVARCHAR(200) NULL,
    [Consumidor_Raw] NVARCHAR(100) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Evaluacion_Raw] NVARCHAR(100) NULL,
    [Cama_Raw] NVARCHAR(50) NULL,
    [Descripcion_Raw] NVARCHAR(200) NULL,
    [N_Plantas_Evaluadas_Raw] NVARCHAR(50) NULL,
    [N_Plantas_en_Floracion_Raw] NVARCHAR(50) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT ('CARGADO'),
    CONSTRAINT [PK_Bronce_Floracion] PRIMARY KEY ([ID_Evaluacion_Vegetativa])
);
END
GO

IF OBJECT_ID('[Bronce].[Induccion_Floral]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Induccion_Floral] (
    [ID_Induccion_Floral] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Tipo_Evaluacion_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [DNI_Raw] NVARCHAR(20) NULL,
    [Fecha_Subida_Raw] NVARCHAR(50) NULL,
    [Nombres_Raw] NVARCHAR(200) NULL,
    [Consumidor_Raw] NVARCHAR(50) NULL,
    [Cama_Raw] NVARCHAR(50) NULL,
    [Descripcion_Raw] NVARCHAR(100) NULL,
    [PlantasPorCama_Raw] NVARCHAR(50) NULL,
    [PlantasConInduccion_Raw] NVARCHAR(50) NULL,
    [BrotesConInduccion_Raw] NVARCHAR(50) NULL,
    [BrotesTotales_Raw] NVARCHAR(50) NULL,
    [BrotesConFlor_Raw] NVARCHAR(50) NULL,
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT (N'CARGADO'),
    CONSTRAINT [PK_Bronce_Induccion_Floral] PRIMARY KEY ([ID_Induccion_Floral])
);
END
GO

IF OBJECT_ID('[Bronce].[Maduracion]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Maduracion] (
    [ID_Maduracion] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT ('CARGADO'),
    [Organo_Raw] NVARCHAR(100) NULL,
    [Color_Raw] NVARCHAR(100) NULL,
    [Sector_Raw] NVARCHAR(200) NULL,
    CONSTRAINT [PK_Bronce_Maduracion] PRIMARY KEY ([ID_Maduracion])
);
END
GO

IF OBJECT_ID('[Bronce].[Peladas]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Peladas] (
    [ID_Peladas] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [DNI_Raw] NVARCHAR(MAX) NULL,
    [Punto_Raw] NVARCHAR(MAX) NULL,
    [Muestras_Raw] NVARCHAR(MAX) NULL,
    [BotonesFlorales_Raw] NVARCHAR(MAX) NULL,
    [Flores_Raw] NVARCHAR(MAX) NULL,
    [BayasPequenas_Raw] NVARCHAR(MAX) NULL,
    [BayasGrandes_Raw] NVARCHAR(MAX) NULL,
    [Fase1_Raw] NVARCHAR(MAX) NULL,
    [Fase2_Raw] NVARCHAR(MAX) NULL,
    [BayasCremas_Raw] NVARCHAR(MAX) NULL,
    [BayasMaduras_Raw] NVARCHAR(MAX) NULL,
    [BayasCosechables_Raw] NVARCHAR(MAX) NULL,
    [PlantasProductivas_Raw] NVARCHAR(MAX) NULL,
    [PlantasNoProductivas_Raw] NVARCHAR(MAX) NULL,
    [YemasActivadas_Raw] NVARCHAR(50) NULL,
    [TotalOrganos_Raw] NVARCHAR(50) NULL,
    [TotalPlantas_Raw] NVARCHAR(50) NULL,
    [Nombres_Raw] NVARCHAR(200) NULL,
    CONSTRAINT [PK_Bronce_Peladas] PRIMARY KEY ([ID_Peladas])
);
END
GO

IF OBJECT_ID('[Bronce].[Pintado_Flores]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Pintado_Flores] (
    [ID_Pintado_Flores] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Pintado_Flores] PRIMARY KEY ([ID_Pintado_Flores])
);
END
GO

IF OBJECT_ID('[Bronce].[Proyeccion_Pesos]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Proyeccion_Pesos] (
    [ID_Proyeccion_Pesos] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Peso_Proyectado_Raw] NVARCHAR(20) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Proyeccion_Pesos] PRIMARY KEY ([ID_Proyeccion_Pesos])
);
END
GO

IF OBJECT_ID('[Bronce].[Reporte_Clima]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Reporte_Clima] (
    [ID_Reporte_Clima] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Hora_Raw] NVARCHAR(20) NULL,
    [Sector_Raw] NVARCHAR(50) NULL,
    [TempMax_Raw] NVARCHAR(20) NULL,
    [TempMin_Raw] NVARCHAR(20) NULL,
    [Humedad_Raw] NVARCHAR(20) NULL,
    [Precipitacion_Raw] NVARCHAR(20) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Reporte_Clima] PRIMARY KEY ([ID_Reporte_Clima])
);
END
GO

IF OBJECT_ID('[Bronce].[Reporte_Cosecha]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Reporte_Cosecha] (
    [ID_Reporte_Cosecha] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [KgNeto_Raw] NVARCHAR(30) NULL,
    [Jabas_Raw] NVARCHAR(20) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [Lote_Raw] NVARCHAR(MAX) NULL,
    [Responsable_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Reporte_Cosecha] PRIMARY KEY ([ID_Reporte_Cosecha])
);
END
GO

IF OBJECT_ID('[Bronce].[Seguimiento_Errores]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Seguimiento_Errores] (
    [ID_Seguimiento_Errores] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Tipo_Error_Raw] NVARCHAR(150) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Fundo_Raw] NVARCHAR(MAX) NULL,
    [Variedad_Raw] NVARCHAR(MAX) NULL,
    [Plantas_Vivas_Raw] NVARCHAR(MAX) NULL,
    [Plantas_Muertas_Raw] NVARCHAR(MAX) NULL,
    [Total_Plantas_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Seguimiento_Errores] PRIMARY KEY ([ID_Seguimiento_Errores])
);
END
GO

IF OBJECT_ID('[Bronce].[Tasa_Crecimiento_Brotes]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Tasa_Crecimiento_Brotes] (
    [ID_Tasa_Crecimiento] BIGINT IDENTITY(1,1) NOT NULL,
    [Codigo_Origen_Raw] NVARCHAR(100) NULL,
    [Semana_Raw] NVARCHAR(50) NULL,
    [Dia_Raw] NVARCHAR(50) NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [DNI_Raw] NVARCHAR(50) NULL,
    [Evaluador_Raw] NVARCHAR(150) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [Turno_Raw] NVARCHAR(50) NULL,
    [Valvula_Raw] NVARCHAR(50) NULL,
    [Condicion_Raw] NVARCHAR(100) NULL,
    [Estado_Vegetativo_Raw] NVARCHAR(100) NULL,
    [Variedad_Raw] NVARCHAR(100) NULL,
    [Cama_Raw] NVARCHAR(50) NULL,
    [Tipo_Tallo_Raw] NVARCHAR(50) NULL,
    [Ensayo_Raw] NVARCHAR(50) NULL,
    [Medida_Raw] NVARCHAR(50) NULL,
    [Fecha_Poda_Aux_Raw] NVARCHAR(50) NULL,
    [Campana_Raw] NVARCHAR(50) NULL,
    [Observacion_Raw] NVARCHAR(500) NULL,
    [Tipo_Evaluacion_Raw] NVARCHAR(100) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Estado_Carga] NVARCHAR(20) NOT NULL DEFAULT ('CARGADO'),
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Bronce_Tasa_Crecimiento_Brotes] PRIMARY KEY ([ID_Tasa_Crecimiento])
);
END
GO

IF OBJECT_ID('[Bronce].[Variables_Meteorologicas]','U') IS NULL
BEGIN
CREATE TABLE [Bronce].[Variables_Meteorologicas] (
    [ID_Variables_Met] BIGINT IDENTITY(1,1) NOT NULL,
    [Fecha_Raw] NVARCHAR(50) NULL,
    [Modulo_Raw] NVARCHAR(50) NULL,
    [VPD_Raw] NVARCHAR(20) NULL,
    [Radiacion_Raw] NVARCHAR(20) NULL,
    [Valores_Raw] NVARCHAR(MAX) NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_Carga] NVARCHAR(MAX) NULL,
    [Sector_Raw] NVARCHAR(MAX) NULL,
    [TempMax_Raw] NVARCHAR(MAX) NULL,
    [TempMin_Raw] NVARCHAR(MAX) NULL,
    [Humedad_Raw] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Bronce_Variables_Meteorologicas] PRIMARY KEY ([ID_Variables_Met])
);
END
GO

-- ---- Schema [Silver] . 37 tablas ----

IF OBJECT_ID('[Silver].[Bridge_Geografia_Cama]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Bridge_Geografia_Cama] (
    [ID_Bridge_Geografia_Cama] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Cama_Catalogo] INT NOT NULL,
    [Fecha_Inicio_Vigencia] DATE NOT NULL DEFAULT (CONVERT([date],getdate())),
    [Fecha_Fin_Vigencia] DATE NULL,
    [Es_Vigente] BIT NOT NULL DEFAULT ((1)),
    [Fuente_Registro] NVARCHAR(50) NOT NULL DEFAULT ('BACKFILL_DIM_GEOGRAFIA'),
    [Observacion] NVARCHAR(300) NULL,
    CONSTRAINT [PK_Silver_Bridge_Geografia_Cama] PRIMARY KEY ([ID_Bridge_Geografia_Cama])
);
END
GO

IF OBJECT_ID('[Silver].[Bridge_Geografia_Campana_Condicion]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Bridge_Geografia_Campana_Condicion] (
    [ID_Bridge] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [ID_Condicion] INT NOT NULL,
    [Vigencia_Inicio] DATE NOT NULL,
    [Vigencia_Fin] DATE NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Hash_Llave] BINARY(32) NOT NULL,
    [Fecha_Carga] DATETIME2(7) NOT NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Bridge_Geografia_Campana_Condicion] PRIMARY KEY ([ID_Bridge])
);
END
GO

IF OBJECT_ID('[Silver].[Bridge_Modulo_Campana]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Bridge_Modulo_Campana] (
    [ID_Bridge] INT IDENTITY(1,1) NOT NULL,
    [ID_Modulo_Catalogo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Tipo_Campana] NVARCHAR(50) NOT NULL,
    [Fecha_Inicio] DATE NOT NULL,
    [Fecha_Fin] DATE NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    [Semana_Poda_ISO] INT NULL,
    [Anio_Poda_ISO] INT NULL,
    CONSTRAINT [PK_Silver_Bridge_Modulo_Campana] PRIMARY KEY ([ID_Bridge])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Actividad_Operativa]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Actividad_Operativa] (
    [ID_Actividad] INT IDENTITY(1,1) NOT NULL,
    [ID_SAP] NVARCHAR(50) NULL,
    [Nombre_Actividad] NVARCHAR(150) NOT NULL,
    [ID_Labor] NVARCHAR(50) NULL,
    [Nombre_Labor] NVARCHAR(150) NULL,
    [Categoria] NVARCHAR(100) NULL,
    CONSTRAINT [PK_Silver_Dim_Actividad_Operativa] PRIMARY KEY ([ID_Actividad])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Cama_Catalogo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Cama_Catalogo] (
    [ID_Cama_Catalogo] INT IDENTITY(1,1) NOT NULL,
    [Cama_Normalizada] NVARCHAR(50) NOT NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NULL,
    CONSTRAINT [PK_Silver_Dim_Cama_Catalogo] PRIMARY KEY ([ID_Cama_Catalogo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Campana]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Campana] (
    [ID_Campana] INT IDENTITY(1,1) NOT NULL,
    [Anio_Cosecha] INT NOT NULL,
    [Nombre_Campana] NVARCHAR(100) NOT NULL,
    [Estado] NVARCHAR(50) NOT NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Dim_Campana] PRIMARY KEY ([ID_Campana])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Cinta]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Cinta] (
    [ID_Cinta] INT IDENTITY(1,1) NOT NULL,
    [Color_Cinta] NVARCHAR(50) NOT NULL,
    [Descripcion] NVARCHAR(200) NULL,
    CONSTRAINT [PK_Silver_Dim_Cinta] PRIMARY KEY ([ID_Cinta])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Condicion_Cultivo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Condicion_Cultivo] (
    [ID_Condicion] INT IDENTITY(1,1) NOT NULL,
    [Sustrato] NVARCHAR(100) NOT NULL,
    [Certificacion] NVARCHAR(50) NOT NULL,
    CONSTRAINT [PK_Silver_Dim_Condicion_Cultivo] PRIMARY KEY ([ID_Condicion])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Escenario_Proyeccion]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Escenario_Proyeccion] (
    [ID_Escenario] INT IDENTITY(1,1) NOT NULL,
    [Tipo_Escenario] NVARCHAR(50) NOT NULL,
    [Descripcion] NVARCHAR(200) NULL,
    [Horizonte_Semanas] INT NULL,
    [Frecuencia_Actualizacion] NVARCHAR(50) NULL,
    CONSTRAINT [PK_Silver_Dim_Escenario_Proyeccion] PRIMARY KEY ([ID_Escenario])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Estado_Fenologico]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Estado_Fenologico] (
    [ID_Estado_Fenologico] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Estado] NVARCHAR(100) NOT NULL,
    [Orden_Estado] INT NOT NULL,
    CONSTRAINT [PK_Silver_Dim_Estado_Fenologico] PRIMARY KEY ([ID_Estado_Fenologico])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Estado_Workflow]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Estado_Workflow] (
    [ID_Workflow] INT IDENTITY(1,1) NOT NULL,
    [Estado] NVARCHAR(50) NOT NULL,
    [Descripcion] NVARCHAR(200) NULL,
    CONSTRAINT [PK_Silver_Dim_Estado_Workflow] PRIMARY KEY ([ID_Workflow])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Fundo_Catalogo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Fundo_Catalogo] (
    [ID_Fundo_Catalogo] INT IDENTITY(1,1) NOT NULL,
    [Fundo] NVARCHAR(100) NOT NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Dim_Fundo_Catalogo] PRIMARY KEY ([ID_Fundo_Catalogo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Geografia]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Geografia] (
    [ID_Geografia] INT IDENTITY(1,1) NOT NULL,
    [ID_Fundo_Catalogo] INT NOT NULL,
    [ID_Sector_Catalogo] INT NOT NULL,
    [ID_Modulo_Catalogo] INT NOT NULL,
    [ID_Turno_Catalogo] INT NOT NULL,
    [ID_Valvula_Catalogo] INT NOT NULL,
    [ID_Cama_Catalogo] INT NOT NULL,
    [Es_Test_Block] BIT NOT NULL DEFAULT ((0)),
    [Codigo_SAP_Campo] NVARCHAR(50) NULL,
    [Nivel_Granularidad] VARCHAR(50) NOT NULL,
    [Fecha_Inicio_Vigencia] DATE NOT NULL,
    [Fecha_Fin_Vigencia] DATE NULL,
    [Es_Vigente] BIT NOT NULL DEFAULT ((1)),
    CONSTRAINT [PK_Silver_Dim_Geografia] PRIMARY KEY ([ID_Geografia])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Modulo_Catalogo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Modulo_Catalogo] (
    [ID_Modulo_Catalogo] INT IDENTITY(1,1) NOT NULL,
    [Modulo] INT NOT NULL,
    [SubModulo] INT NULL,
    [Tipo_Conduccion] NVARCHAR(50) NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Dim_Modulo_Catalogo] PRIMARY KEY ([ID_Modulo_Catalogo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Personal]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Personal] (
    [ID_Personal] INT IDENTITY(1,1) NOT NULL,
    [DNI] NVARCHAR(20) NOT NULL,
    [Nombre_Completo] NVARCHAR(200) NOT NULL,
    [Rol] NVARCHAR(100) NULL,
    [Sexo] NVARCHAR(10) NULL,
    [ID_Planilla] NVARCHAR(20) NULL,
    [Pct_Asertividad] DECIMAL(5,2) NULL,
    [Dias_Ausentismo] INT NULL,
    CONSTRAINT [PK_Silver_Dim_Personal] PRIMARY KEY ([ID_Personal])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Sector_Catalogo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Sector_Catalogo] (
    [ID_Sector_Catalogo] INT IDENTITY(1,1) NOT NULL,
    [Sector] NVARCHAR(100) NOT NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Dim_Sector_Catalogo] PRIMARY KEY ([ID_Sector_Catalogo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Tiempo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Tiempo] (
    [ID_Tiempo] INT NOT NULL,
    [Fecha] DATE NOT NULL,
    [Anio] INT NOT NULL,
    [Mes] INT NOT NULL,
    [Semana_ISO] INT NOT NULL,
    [Semana_Cosecha] INT NULL,
    [Dia_Semana] INT NOT NULL,
    [Nombre_Mes] NVARCHAR(20) NOT NULL,
    [Es_Fin_Semana] BIT NOT NULL DEFAULT ((0)),
    CONSTRAINT [PK_Silver_Dim_Tiempo] PRIMARY KEY ([ID_Tiempo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Turno_Catalogo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Turno_Catalogo] (
    [ID_Turno_Catalogo] INT IDENTITY(1,1) NOT NULL,
    [Turno] INT NOT NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Dim_Turno_Catalogo] PRIMARY KEY ([ID_Turno_Catalogo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Valvula_Catalogo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Valvula_Catalogo] (
    [ID_Valvula_Catalogo] INT IDENTITY(1,1) NOT NULL,
    [Valvula] NVARCHAR(50) NOT NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NULL DEFAULT (sysutcdatetime()),
    CONSTRAINT [PK_Silver_Dim_Valvula_Catalogo] PRIMARY KEY ([ID_Valvula_Catalogo])
);
END
GO

IF OBJECT_ID('[Silver].[Dim_Variedad]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Dim_Variedad] (
    [ID_Variedad] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Variedad] NVARCHAR(100) NOT NULL,
    [Breeder] NVARCHAR(100) NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Fecha_Modificacion] DATETIME2(7) NULL,
    CONSTRAINT [PK_Silver_Dim_Variedad] PRIMARY KEY ([ID_Variedad])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Censo_Plantas]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Censo_Plantas] (
    [ID_Censo] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [ID_Campana] INT NULL,
    [Plantas_Buenas] INT NULL,
    [Plantas_Regulares] INT NULL,
    [Plantas_Malas] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Censo_Plantas] PRIMARY KEY ([ID_Censo])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Ciclo_Poda]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Ciclo_Poda] (
    [ID_Poda] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Tallos_Planta] DECIMAL(8,2) NULL,
    [Longitud_Tallo] DECIMAL(8,2) NULL,
    [Diametro_Tallo] DECIMAL(8,2) NULL,
    [Ramilla_Planta] DECIMAL(8,2) NULL,
    [Tocones_Planta] DECIMAL(8,2) NULL,
    [Cortes_Defectuosos] DECIMAL(8,2) NULL,
    [Altura_Poda] DECIMAL(8,2) NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [ID_Campana] INT NULL,
    [Punto] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Ciclo_Poda] PRIMARY KEY ([ID_Poda])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Conteo_Fenologico]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Conteo_Fenologico] (
    [ID_Conteo_Fenologico] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NULL,
    [ID_Estado_Fenologico] INT NOT NULL,
    [Cantidad_Organos] INT NOT NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [Punto] INT NULL,
    [ID_Campana] INT NULL,
    [Fecha_Registro] DATETIME2(7) NULL,
    [Plantas_Productivas] INT NULL,
    [Plantas_No_Productivas] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Conteo_Fenologico] PRIMARY KEY ([ID_Conteo_Fenologico])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Cosecha_SAP]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Cosecha_SAP] (
    [ID_Cosecha_SAP] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Condicion_Cultivo] INT NOT NULL,
    [Kg_Neto_MP] DECIMAL(10,3) NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Cosecha_SAP] PRIMARY KEY ([ID_Cosecha_SAP])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Evaluacion_Pesos]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Evaluacion_Pesos] (
    [ID_Evaluacion_Pesos] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NOT NULL,
    [Peso_Promedio_Baya_g] DECIMAL(6,2) NOT NULL,
    [Cantidad_Bayas_Muestra] INT NULL,
    [Peso_Proyectado_Baya_g] DECIMAL(6,2) NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Evaluacion_Pesos] PRIMARY KEY ([ID_Evaluacion_Pesos])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Evaluacion_Vegetativa]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Evaluacion_Vegetativa] (
    [ID_Fact_Evaluacion_Vegetativa] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NULL,
    [Piso] TINYINT NOT NULL,
    [Semanas_Despues_Poda] INT NULL,
    [Altura] DECIMAL(8,2) NULL,
    [Tallos_Basales] DECIMAL(8,2) NULL,
    [Tallos_Basales_Nuevos] DECIMAL(8,2) NULL,
    [Muestra_Plantas] INT NULL,
    [Brotes_Generales] DECIMAL(8,2) NULL,
    [Brotes_Productivos] DECIMAL(8,2) NULL,
    [Diametro_Brote] DECIMAL(6,2) NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('OK'),
    [ID_Origen_Bronce] BIGINT NULL,
    CONSTRAINT [PK_Silver_Fact_Evaluacion_Vegetativa] PRIMARY KEY ([ID_Fact_Evaluacion_Vegetativa])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Fisiologia]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Fisiologia] (
    [ID_Fisiologia] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [Tercio] NVARCHAR(20) NULL,
    [Brotes_Productivos] INT NULL,
    [Brotes_Vegetativos] INT NULL,
    [Hinchadas] INT NULL,
    [Productivas] INT NULL,
    [Total_Organos] INT NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [ID_Campana] INT NULL,
    [Aux] NVARCHAR(255) NULL,
    CONSTRAINT [PK_Silver_Fact_Fisiologia] PRIMARY KEY ([ID_Fisiologia])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Floracion]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Floracion] (
    [ID_Fact_Floracion] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NOT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Cantidad_Plantas_Evaluadas] INT NOT NULL,
    [Cantidad_Plantas_en_Floracion] INT NOT NULL,
    [Fecha_Evento] DATE NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('OK'),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Floracion] PRIMARY KEY ([ID_Fact_Floracion])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Induccion_Floral]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Induccion_Floral] (
    [ID_Induccion_Floral] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NOT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Codigo_Consumidor] NVARCHAR(50) NULL,
    [Cantidad_Plantas_Por_Cama] INT NOT NULL,
    [Cantidad_Plantas_Con_Induccion] INT NOT NULL,
    [Cantidad_Brotes_Con_Induccion] INT NOT NULL,
    [Cantidad_Brotes_Totales] INT NOT NULL,
    [Cantidad_Brotes_Con_Flor] INT NOT NULL,
    [Pct_Plantas_Con_Induccion] DECIMAL(5,2) NULL,
    [Pct_Brotes_Con_Induccion] DECIMAL(5,2) NULL,
    [Pct_Brotes_Con_Flor] DECIMAL(5,2) NULL,
    [Fecha_Evento] DATE NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT (N'OK'),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Induccion_Floral] PRIMARY KEY ([ID_Induccion_Floral])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Maduracion]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Maduracion] (
    [ID_Maduracion] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Personal] INT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Estado_Fenologico] INT NOT NULL,
    [ID_Cinta] INT NOT NULL,
    [ID_Organo] INT NOT NULL,
    [Dias_Pasados_Del_Marcado] INT NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT (N'OK'),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Maduracion] PRIMARY KEY ([ID_Maduracion])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Peladas]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Peladas] (
    [ID_Peladas] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NULL,
    [ID_Estado_Fenologico] INT NOT NULL,
    [Punto] INT NOT NULL,
    [Cantidad] INT NOT NULL DEFAULT ((0)),
    [Muestras] INT NOT NULL,
    [Plantas_Productivas] INT NOT NULL DEFAULT ((0)),
    [Plantas_No_Productivas] INT NOT NULL DEFAULT ((0)),
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    CONSTRAINT [PK_Silver_Fact_Peladas] PRIMARY KEY ([ID_Peladas])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Peladas_Old]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Peladas_Old] (
    [ID_Peladas] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NULL,
    [Punto] INT NOT NULL,
    [Botones_Florales] INT NOT NULL DEFAULT ((0)),
    [Flores] INT NOT NULL DEFAULT ((0)),
    [Bayas_Pequenas] INT NOT NULL DEFAULT ((0)),
    [Bayas_Grandes] INT NOT NULL DEFAULT ((0)),
    [Fase_1] INT NOT NULL DEFAULT ((0)),
    [Fase_2] INT NOT NULL DEFAULT ((0)),
    [Bayas_Cremas] INT NOT NULL DEFAULT ((0)),
    [Bayas_Maduras] INT NOT NULL DEFAULT ((0)),
    [Bayas_Cosechables] INT NOT NULL DEFAULT ((0)),
    [Plantas_Productivas] INT NOT NULL DEFAULT ((0)),
    [Plantas_No_Productivas] INT NOT NULL DEFAULT ((0)),
    [Muestras] INT NOT NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [ID_Campana] INT NULL,
    [Yemas_Activadas] INT NOT NULL DEFAULT ((0)),
    CONSTRAINT [PK_Silver_Fact_Peladas_Old] PRIMARY KEY ([ID_Peladas])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Proyecciones]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Proyecciones] (
    [ID_Proyeccion] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Escenario] INT NOT NULL,
    [ID_Estado_Workflow] INT NOT NULL,
    [Kg_Proyectados] DECIMAL(12,3) NOT NULL,
    [MAPE] DECIMAL(8,4) NULL,
    [Version_Modelo] NVARCHAR(50) NULL,
    [Fecha_Cutoff] DATETIME2(7) NOT NULL,
    [ID_Version_Datos] NVARCHAR(100) NULL,
    [Flag_Override] BIT NOT NULL DEFAULT ((0)),
    [Motivo_Override] NVARCHAR(500) NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT ('Aprobado'),
    [ID_Campana] INT NULL,
    [Kg_Pesimista] DECIMAL(18,4) NULL,
    [Kg_Optimista] DECIMAL(18,4) NULL,
    [Pct_Maduracion] DECIMAL(10,6) NULL,
    [Pct_Productivas] DECIMAL(10,6) NULL,
    CONSTRAINT [PK_Silver_Fact_Proyecciones] PRIMARY KEY ([ID_Proyeccion])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Tareo]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Tareo] (
    [ID_Tareo] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Personal] INT NOT NULL,
    [ID_Actividad_Operativa] INT NOT NULL,
    [ID_Personal_Supervisor] INT NULL,
    [Horas_Trabajadas] DECIMAL(6,2) NOT NULL,
    [ID_Planilla] NVARCHAR(20) NULL,
    [Es_Observado_SAP] BIT NOT NULL DEFAULT ((0)),
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Tareo] PRIMARY KEY ([ID_Tareo])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Tasa_Crecimiento_Brotes]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] (
    [ID_Tasa_Crecimiento_Brotes] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Personal] INT NOT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Condicion] NVARCHAR(100) NULL,
    [Estado_Vegetativo] NVARCHAR(100) NULL,
    [Tipo_Tallo] NVARCHAR(50) NULL,
    [Codigo_Ensayo] NVARCHAR(50) NOT NULL,
    [Codigo_Origen] NVARCHAR(100) NULL,
    [Campana] NVARCHAR(30) NULL,
    [Observacion] NVARCHAR(500) NULL,
    [Fecha_Poda_Aux] DATE NULL,
    [Dias_Desde_Poda] INT NULL,
    [Medida_Crecimiento] DECIMAL(10,4) NOT NULL,
    [Fecha_Evento] DATE NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Estado_DQ] NVARCHAR(20) NOT NULL DEFAULT (N'OK'),
    [ID_Campana] INT NULL,
    [ID_Condicion] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Tasa_Crecimiento_Brotes] PRIMARY KEY ([ID_Tasa_Crecimiento_Brotes])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_Telemetria_Clima]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_Telemetria_Clima] (
    [ID_Telemetria_Clima] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [Sector_Climatico] NVARCHAR(50) NOT NULL,
    [Temperatura_Max_C] DECIMAL(8,2) NULL,
    [Temperatura_Min_C] DECIMAL(8,2) NULL,
    [Humedad_Relativa_Pct] DECIMAL(8,2) NULL,
    [Precipitacion_mm] DECIMAL(12,3) NULL,
    [VPD] DECIMAL(8,3) NULL,
    [Radiacion_Solar] DECIMAL(12,3) NULL,
    [Fecha_Evento] DATETIME2(7) NOT NULL,
    [Fecha_Sistema] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Silver_Fact_Telemetria_Clima] PRIMARY KEY ([ID_Telemetria_Clima])
);
END
GO

IF OBJECT_ID('[Silver].[Fact_areas_plantas]','U') IS NULL
BEGIN
CREATE TABLE [Silver].[Fact_areas_plantas] (
    [ID_Censo] INT IDENTITY(1,1) NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [Cantidad_Plantas] FLOAT NULL,
    [Area_ha] FLOAT NULL,
    [Fecha_Sistema] DATETIME2(7) NULL DEFAULT (sysdatetime()),
    [Estado_DQ] NVARCHAR(50) NULL DEFAULT ('OK'),
    [ID_Campana] INT NULL,
    [ID_Condicion] INT NULL,
    CONSTRAINT [PK_Silver_Fact_areas_plantas] PRIMARY KEY ([ID_Censo])
);
END
GO

-- ---- Schema [Gold] . 12 tablas ----

IF OBJECT_ID('[Gold].[Mart_Administrativo]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Administrativo] (
    [ID_Mart_Admin] BIGINT IDENTITY(1,1) NOT NULL,
    [Semana_ISO] INT NOT NULL,
    [DNI_Personal] NVARCHAR(20) NOT NULL,
    [Nombre_Personal] NVARCHAR(200) NOT NULL,
    [Sexo] NVARCHAR(10) NULL,
    [Rol] NVARCHAR(100) NULL,
    [Actividad] NVARCHAR(150) NULL,
    [Labor] NVARCHAR(150) NULL,
    [Horas_Trabajadas] DECIMAL(8,2) NULL,
    [Dias_Trabajados] INT NULL,
    [Pct_Asertividad] DECIMAL(5,2) NULL,
    [Registros_Observados_SAP] INT NULL,
    [Supervisor] NVARCHAR(200) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [ID_Tiempo] INT NULL,
    [ID_Personal] INT NULL,
    [ID_Actividad] INT NULL,
    [Horas_Trabajadas_Total] DECIMAL(18,2) NULL,
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Gold_Mart_Administrativo] PRIMARY KEY ([ID_Mart_Admin])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Ciclo_Poda]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Ciclo_Poda] (
    [ID_Mart_Poda] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NULL,
    [Semana_ISO] INT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Tallos_Planta_Total] DECIMAL(8,2) NULL,
    [Longitud_Tallo_Total] DECIMAL(8,2) NULL,
    [Diametro_Tallo_Total] DECIMAL(8,2) NULL,
    [Ramilla_Planta_Total] DECIMAL(8,2) NULL,
    [Tocones_Planta_Total] DECIMAL(8,2) NULL,
    [Cortes_Defectuosos_Total] DECIMAL(8,2) NULL,
    [Altura_Poda_Total] DECIMAL(8,2) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NULL DEFAULT (sysdatetime()),
    [N_Muestras] INT NOT NULL DEFAULT ((0)),
    CONSTRAINT [PK_Gold_Mart_Ciclo_Poda] PRIMARY KEY ([ID_Mart_Poda])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Clima]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Clima] (
    [ID_Tiempo] INT NOT NULL,
    [Sector_Climatico] NVARCHAR(50) NOT NULL,
    [Semana_ISO] INT NOT NULL,
    [Temp_Max_Promedio] DECIMAL(12,3) NULL,
    [Temp_Min_Promedio] DECIMAL(12,3) NULL,
    [VPD_Promedio] DECIMAL(12,3) NULL,
    [Humedad_Promedio] DECIMAL(12,3) NULL,
    [Precipitacion_Total] DECIMAL(14,3) NULL,
    [ID_Campana] INT NULL
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Cosecha]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Cosecha] (
    [ID_Mart_Cosecha] BIGINT IDENTITY(1,1) NOT NULL,
    [Semana_ISO] INT NOT NULL,
    [Fecha_Cosecha] DATE NOT NULL,
    [Modulo] INT NULL,
    [Turno] INT NULL,
    [Variedad] NVARCHAR(100) NOT NULL,
    [Condicion] NVARCHAR(50) NULL,
    [Kg_Neto_Real] DECIMAL(12,3) NULL,
    [Kg_Proyectados] DECIMAL(12,3) NULL,
    [Pct_Cumplimiento] DECIMAL(30,15) NULL,
    [Cantidad_Jabas] INT NULL,
    [Peso_Promedio_Jaba_kg] DECIMAL(21,14) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [ID_Tiempo] INT NULL,
    [ID_Geografia] INT NULL,
    [ID_Variedad] INT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [Fecha_Evento] NVARCHAR(MAX) NULL,
    [Kg_Brutos] DECIMAL(18,4) NULL,
    [Kg_Neto_MP] DECIMAL(18,4) NULL,
    [Kg_Proyectado] DECIMAL(18,4) NULL,
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Gold_Mart_Cosecha] PRIMARY KEY ([ID_Mart_Cosecha])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Evaluacion_Vegetativa]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Evaluacion_Vegetativa] (
    [ID_Mart_Vegetativa] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Fundo] NVARCHAR(100) NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NULL,
    [Semana_ISO] INT NULL,
    [Piso] TINYINT NOT NULL,
    [Semanas_Despues_Poda_Promedio] DECIMAL(6,2) NULL,
    [Altura_Promedio] DECIMAL(8,2) NULL,
    [Tallos_Basales_Promedio] DECIMAL(8,2) NULL,
    [Tallos_Basales_Nuevos_Promedio] DECIMAL(8,2) NULL,
    [Muestra_Plantas_Total] INT NULL,
    [Brotes_Generales_Promedio] DECIMAL(8,2) NULL,
    [Brotes_Productivos_Promedio] DECIMAL(8,2) NULL,
    [Diametro_Brote_Promedio] DECIMAL(6,2) NULL,
    [Ratio_Productivo_General] DECIMAL(21,13) NULL,
    [N_Muestras] INT NOT NULL DEFAULT ((0)),
    [Fecha_Actualizacion] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    CONSTRAINT [PK_Gold_Mart_Evaluacion_Vegetativa] PRIMARY KEY ([ID_Mart_Vegetativa])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Fenologia]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Fenologia] (
    [ID_Mart_Fenologia] BIGINT IDENTITY(1,1) NOT NULL,
    [Semana_ISO] INT NOT NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NOT NULL,
    [Color_Cinta] NVARCHAR(50) NULL,
    [Estado_Fenologico] NVARCHAR(100) NOT NULL,
    [Orden_Estado] INT NOT NULL,
    [Cantidad_Bayas] INT NULL,
    [Pct_Cosechable] DECIMAL(8,2) NULL,
    [Pct_Avance_Ciclo] DECIMAL(13,6) NULL,
    [Brotes_Productivos] INT NULL,
    [Brotes_Vegetativos] INT NULL,
    [Ratio_Productivo_Veg] DECIMAL(19,13) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Gold_Mart_Fenologia] PRIMARY KEY ([ID_Mart_Fenologia])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Fisiologia]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Fisiologia] (
    [ID_Mart_Fisiologia] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NULL,
    [Semana_ISO] INT NULL,
    [Tercio] NVARCHAR(20) NULL,
    [Brotes_Productivos_Promedio] DECIMAL(10,2) NULL,
    [Brotes_Vegetativos_Promedio] DECIMAL(10,2) NULL,
    [Hinchadas_Promedio] DECIMAL(10,2) NULL,
    [Productivas_Promedio] DECIMAL(10,2) NULL,
    [Total_Organos_Promedio] DECIMAL(10,2) NULL,
    [Ratio_Productivo_Veg] DECIMAL(23,13) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NULL DEFAULT (sysdatetime()),
    CONSTRAINT [PK_Gold_Mart_Fisiologia] PRIMARY KEY ([ID_Mart_Fisiologia])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Induccion_Floral]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Induccion_Floral] (
    [ID_Mart_Induccion] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NULL,
    [Semana_ISO] INT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Pct_Plantas_Con_Induccion_Prom] DECIMAL(5,2) NULL,
    [Pct_Brotes_Con_Induccion_Prom] DECIMAL(5,2) NULL,
    [Pct_Brotes_Con_Flor_Prom] DECIMAL(5,2) NULL,
    [Brotes_Totales] INT NULL,
    [Brotes_Con_Flor] INT NULL,
    [Fecha_Actualizacion] DATETIME2(7) NULL DEFAULT (sysdatetime()),
    CONSTRAINT [PK_Gold_Mart_Induccion_Floral] PRIMARY KEY ([ID_Mart_Induccion])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Maduracion]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Maduracion] (
    [ID_Mart_Maduracion] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NULL,
    [Semana_ISO] INT NULL,
    [ID_Estado_Fenologico] INT NULL,
    [Estado_Fenologico] NVARCHAR(100) NULL,
    [ID_Cinta] INT NULL,
    [Color_Cinta] NVARCHAR(50) NULL,
    [Organos_Observados] INT NULL,
    [Dias_Pasados_Promedio] DECIMAL(8,2) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NULL DEFAULT (sysdatetime()),
    CONSTRAINT [PK_Gold_Mart_Maduracion] PRIMARY KEY ([ID_Mart_Maduracion])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Pesos_Calibres]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Pesos_Calibres] (
    [ID_Mart_Pesos] BIGINT IDENTITY(1,1) NOT NULL,
    [Semana_ISO] INT NOT NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NOT NULL,
    [Evaluador] NVARCHAR(200) NULL,
    [Cant_Bayas_Muestra] INT NULL,
    [Peso_Promedio_Baya_g] DECIMAL(6,2) NULL,
    [Peso_Proyectado_Baya_g] DECIMAL(6,2) NULL,
    [Tendencia_Peso] DECIMAL(6,2) NULL,
    [Estado_DQ] NVARCHAR(20) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [ID_Tiempo] INT NULL,
    [ID_Geografia] INT NULL,
    [ID_Variedad] INT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Gold_Mart_Pesos_Calibres] PRIMARY KEY ([ID_Mart_Pesos])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Proyecciones]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Proyecciones] (
    [ID_Mart_Proyeccion] BIGINT IDENTITY(1,1) NOT NULL,
    [Semana_Objetivo] INT NOT NULL,
    [Modulo] INT NULL,
    [Turno] INT NULL,
    [Variedad] NVARCHAR(100) NOT NULL,
    [Version_Escenario] NVARCHAR(50) NOT NULL,
    [Fecha_Generacion] DATE NOT NULL,
    [Fecha_Cutoff] DATETIME2(7) NOT NULL,
    [Kg_Proyectados] DECIMAL(12,3) NOT NULL,
    [Kg_Real] DECIMAL(12,3) NULL,
    [Error_MAPE] DECIMAL(8,4) NULL,
    [Desviacion_kg] DECIMAL(13,3) NULL,
    [Flag_Override] BIT NOT NULL DEFAULT ((0)),
    [Motivo_Override] NVARCHAR(500) NULL,
    [Fecha_Actualizacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [ID_Tiempo] INT NULL,
    [ID_Geografia] INT NULL,
    [ID_Variedad] INT NULL,
    [ID_Escenario] INT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [MAPE] NVARCHAR(MAX) NULL,
    [Version_Modelo] NVARCHAR(MAX) NULL,
    [Estado_Workflow] NVARCHAR(MAX) NULL,
    [ID_Campana] INT NULL,
    CONSTRAINT [PK_Gold_Mart_Proyecciones] PRIMARY KEY ([ID_Mart_Proyeccion])
);
END
GO

IF OBJECT_ID('[Gold].[Mart_Tasa_Crecimiento]','U') IS NULL
BEGIN
CREATE TABLE [Gold].[Mart_Tasa_Crecimiento] (
    [ID_Mart_Crecimiento] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Tiempo] INT NOT NULL,
    [ID_Geografia] INT NOT NULL,
    [ID_Variedad] INT NOT NULL,
    [ID_Campana] INT NOT NULL,
    [Fundo] NVARCHAR(MAX) NULL,
    [Modulo] INT NULL,
    [Variedad] NVARCHAR(100) NULL,
    [Semana_ISO] INT NULL,
    [Tipo_Evaluacion] NVARCHAR(100) NULL,
    [Estado_Vegetativo] NVARCHAR(100) NULL,
    [Tipo_Tallo] NVARCHAR(50) NULL,
    [Medida_Crecimiento_Promedio] DECIMAL(10,4) NULL,
    [Medida_Crecimiento_Max] DECIMAL(10,4) NULL,
    [Dias_Desde_Poda_Promedio] DECIMAL(8,2) NULL,
    [Cantidad_Mediciones] INT NULL,
    [Fecha_Actualizacion] DATETIME2(7) NULL DEFAULT (sysdatetime()),
    CONSTRAINT [PK_Gold_Mart_Tasa_Crecimiento] PRIMARY KEY ([ID_Mart_Crecimiento])
);
END
GO

-- ---- Schema [MDM] . 8 tablas ----

IF OBJECT_ID('[MDM].[Catalogo_Geografia]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Catalogo_Geografia] (
    [ID_Catalogo_Geografia] INT IDENTITY(1,1) NOT NULL,
    [Fundo] NVARCHAR(100) NULL,
    [Sector] NVARCHAR(100) NULL,
    [Modulo] NVARCHAR(100) NULL,
    [Turno] NVARCHAR(100) NULL,
    [Valvula] NVARCHAR(50) NULL,
    [Cama] NVARCHAR(50) NULL,
    [Codigo_SAP_Campo] NVARCHAR(50) NULL,
    [Es_Test_Block] BIT NOT NULL DEFAULT ((0)),
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [SubModulo] INT NULL,
    [Tipo_Conduccion] NVARCHAR(50) NULL,
    CONSTRAINT [PK_MDM_Catalogo_Geografia] PRIMARY KEY ([ID_Catalogo_Geografia])
);
END
GO

IF OBJECT_ID('[MDM].[Catalogo_Personal]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Catalogo_Personal] (
    [ID_Catalogo_Personal] INT IDENTITY(1,1) NOT NULL,
    [DNI] NVARCHAR(20) NOT NULL,
    [Nombre_Completo] NVARCHAR(200) NOT NULL,
    [Rol] NVARCHAR(100) NULL,
    [Sexo] NVARCHAR(10) NULL,
    [Es_Activo] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Fecha_Modificacion] DATETIME2(7) NULL,
    CONSTRAINT [PK_MDM_Catalogo_Personal] PRIMARY KEY ([ID_Catalogo_Personal])
);
END
GO

IF OBJECT_ID('[MDM].[Catalogo_Variedades]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Catalogo_Variedades] (
    [ID_Catalogo_Variedad] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Canonico] NVARCHAR(100) NOT NULL,
    [Breeder] NVARCHAR(100) NULL,
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Fecha_Modificacion] DATETIME2(7) NULL,
    CONSTRAINT [PK_MDM_Catalogo_Variedades] PRIMARY KEY ([ID_Catalogo_Variedad])
);
END
GO

IF OBJECT_ID('[MDM].[Cuarentena]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Cuarentena] (
    [ID_Cuarentena] BIGINT IDENTITY(1,1) NOT NULL,
    [Tabla_Origen] NVARCHAR(100) NOT NULL,
    [Campo_Origen] NVARCHAR(100) NOT NULL,
    [Valor_Recibido] NVARCHAR(500) NULL,
    [Motivo] NVARCHAR(200) NOT NULL,
    [Tipo_Regla] NVARCHAR(20) NOT NULL,
    [Score_Levenshtein] DECIMAL(5,4) NULL,
    [Estado] NVARCHAR(20) NOT NULL DEFAULT ('Pendiente'),
    [Valor_Corregido] NVARCHAR(500) NULL,
    [Aprobado_Por] NVARCHAR(20) NULL,
    [Fecha_Ingreso] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Fecha_Resolucion] DATETIME2(7) NULL,
    [ID_Registro_Origen] BIGINT NULL,
    CONSTRAINT [PK_MDM_Cuarentena] PRIMARY KEY ([ID_Cuarentena])
);
END
GO

IF OBJECT_ID('[MDM].[Diccionario_Homologacion]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Diccionario_Homologacion] (
    [ID_Homologacion] INT IDENTITY(1,1) NOT NULL,
    [Texto_Crudo] NVARCHAR(200) NOT NULL,
    [Valor_Canonico] NVARCHAR(200) NOT NULL,
    [Tabla_Origen] NVARCHAR(100) NOT NULL,
    [Campo_Origen] NVARCHAR(100) NOT NULL,
    [Score_Levenshtein] DECIMAL(5,4) NULL,
    [Aprobado_Por] NVARCHAR(20) NULL,
    [Fecha_Aprobacion] DATETIME2(7) NULL,
    [Veces_Aplicado] INT NOT NULL DEFAULT ((0)),
    CONSTRAINT [PK_MDM_Diccionario_Homologacion] PRIMARY KEY ([ID_Homologacion])
);
END
GO

IF OBJECT_ID('[MDM].[Parametros_Validacion]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Parametros_Validacion] (
    [ID_Parametro] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Regla] NVARCHAR(100) NOT NULL,
    [Valor_Min] FLOAT NULL,
    [Valor_Max] FLOAT NULL,
    [Descripcion] NVARCHAR(500) NULL,
    [Fecha_Modificacion] DATETIME NULL DEFAULT (getdate()),
    CONSTRAINT [PK_MDM_Parametros_Validacion] PRIMARY KEY ([ID_Parametro])
);
END
GO

IF OBJECT_ID('[MDM].[Regla_Modulo_Raw]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Regla_Modulo_Raw] (
    [ID_Regla_Modulo] INT IDENTITY(1,1) NOT NULL,
    [Modulo_Raw] NVARCHAR(100) NOT NULL,
    [Modulo_Int] INT NULL,
    [SubModulo_Int] INT NULL,
    [Tipo_Conduccion] NVARCHAR(50) NULL,
    [Es_Test_Block] BIT NOT NULL DEFAULT ((0)),
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(0) NOT NULL DEFAULT (sysdatetime()),
    [Fecha_Modificacion] DATETIME2(0) NULL,
    [Observacion] NVARCHAR(300) NULL,
    CONSTRAINT [PK_MDM_Regla_Modulo_Raw] PRIMARY KEY ([ID_Regla_Modulo])
);
END
GO

IF OBJECT_ID('[MDM].[Regla_Modulo_Turno_SubModulo]','U') IS NULL
BEGIN
CREATE TABLE [MDM].[Regla_Modulo_Turno_SubModulo] (
    [ID_Regla_Modulo_Turno] INT IDENTITY(1,1) NOT NULL,
    [Modulo_Raw_Base] NVARCHAR(50) NOT NULL,
    [Modulo_Int] INT NOT NULL,
    [Turno_Desde] INT NOT NULL,
    [Turno_Hasta] INT NOT NULL,
    [SubModulo_Int] INT NOT NULL,
    [Tipo_Conduccion] NVARCHAR(50) NULL,
    [Es_Test_Block] BIT NOT NULL DEFAULT ((0)),
    [Es_Activa] BIT NOT NULL DEFAULT ((1)),
    [Prioridad] INT NOT NULL DEFAULT ((1)),
    [Observacion] NVARCHAR(300) NULL,
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    [Fecha_Modificacion] DATETIME2(7) NOT NULL DEFAULT (sysdatetime()),
    CONSTRAINT [PK_MDM_Regla_Modulo_Turno_SubModulo] PRIMARY KEY ([ID_Regla_Modulo_Turno])
);
END
GO

-- ---- Schema [Config] . 4 tablas ----

IF OBJECT_ID('[Config].[Analogos_Variedades]','U') IS NULL
BEGIN
CREATE TABLE [Config].[Analogos_Variedades] (
    [ID_Analogo] INT IDENTITY(1,1) NOT NULL,
    [Variedad_Nueva] NVARCHAR(100) NOT NULL,
    [Variedad_Analoga] NVARCHAR(100) NOT NULL,
    [Factor_Vigor] DECIMAL(6,4) NULL,
    [Desfase_Fenologico_Dias] INT NULL,
    [Activo] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Config_Analogos_Variedades] PRIMARY KEY ([ID_Analogo])
);
END
GO

IF OBJECT_ID('[Config].[Calendario_Entregables]','U') IS NULL
BEGIN
CREATE TABLE [Config].[Calendario_Entregables] (
    [ID_Entregable] INT IDENTITY(1,1) NOT NULL,
    [Tipo_Escenario] NVARCHAR(50) NOT NULL,
    [Frecuencia] NVARCHAR(20) NOT NULL,
    [Dia_Generacion] NVARCHAR(20) NULL,
    [Hora_Limite] TIME(7) NULL,
    [Activo] BIT NOT NULL DEFAULT ((1)),
    CONSTRAINT [PK_Config_Calendario_Entregables] PRIMARY KEY ([ID_Entregable])
);
END
GO

IF OBJECT_ID('[Config].[Parametros_Pipeline]','U') IS NULL
BEGIN
CREATE TABLE [Config].[Parametros_Pipeline] (
    [ID_Parametro] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Parametro] NVARCHAR(100) NOT NULL,
    [Valor] NVARCHAR(500) NOT NULL,
    [Descripcion] NVARCHAR(300) NULL,
    [Fecha_Modificacion] DATETIME2(7) NULL,
    [Modificado_Por] NVARCHAR(20) NULL,
    CONSTRAINT [PK_Config_Parametros_Pipeline] PRIMARY KEY ([ID_Parametro])
);
END
GO

IF OBJECT_ID('[Config].[Reglas_Validacion]','U') IS NULL
BEGIN
CREATE TABLE [Config].[Reglas_Validacion] (
    [ID_Regla] INT IDENTITY(1,1) NOT NULL,
    [Tabla_Destino] NVARCHAR(100) NOT NULL,
    [Columna] NVARCHAR(100) NOT NULL,
    [Valor_Min] DECIMAL(18,4) NULL,
    [Valor_Max] DECIMAL(18,4) NULL,
    [Tipo_Validacion] NVARCHAR(20) NOT NULL,
    [Accion] NVARCHAR(20) NOT NULL DEFAULT ('CUARENTENA'),
    [Descripcion] NVARCHAR(300) NULL,
    [Activo] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Fecha_Modificacion] DATETIME2(7) NULL,
    CONSTRAINT [PK_Config_Reglas_Validacion] PRIMARY KEY ([ID_Regla])
);
END
GO

-- ---- Schema [Control] . 5 tablas ----

IF OBJECT_ID('[Control].[Bloqueo_Ejecucion]','U') IS NULL
BEGIN
CREATE TABLE [Control].[Bloqueo_Ejecucion] (
    [ID_Lock] INT NOT NULL DEFAULT ((1)),
    [ID_Corrida_Activa] VARCHAR(36) NULL,
    [Adquirido_Por] VARCHAR(100) NULL,
    [Fecha_Adquisicion] DATETIME2(0) NULL,
    [Heartbeat] DATETIME2(0) NULL,
    CONSTRAINT [PK_Control_Bloqueo_Ejecucion] PRIMARY KEY ([ID_Lock])
);
END
GO

IF OBJECT_ID('[Control].[Comando_Ejecucion]','U') IS NULL
BEGIN
CREATE TABLE [Control].[Comando_Ejecucion] (
    [ID_Comando] INT IDENTITY(1,1) NOT NULL,
    [ID_Corrida] VARCHAR(36) NOT NULL,
    [Tipo_Comando] VARCHAR(50) NOT NULL DEFAULT ('INICIAR'),
    [Iniciado_Por] VARCHAR(100) NOT NULL,
    [Comentario] VARCHAR(500) NULL,
    [Max_Reintentos] INT NOT NULL DEFAULT ((0)),
    [Timeout_Seg] INT NOT NULL DEFAULT ((3600)),
    [Estado_Cmd] VARCHAR(20) NOT NULL DEFAULT ('PENDIENTE'),
    [Fecha_Comando] DATETIME2(0) NOT NULL DEFAULT (getdate()),
    [Fecha_Proceso] DATETIME2(0) NULL,
    [Mensaje_Error] VARCHAR(500) NULL,
    CONSTRAINT [PK_Control_Comando_Ejecucion] PRIMARY KEY ([ID_Comando])
);
END
GO

IF OBJECT_ID('[Control].[Corrida]','U') IS NULL
BEGIN
CREATE TABLE [Control].[Corrida] (
    [ID_Corrida] VARCHAR(36) NOT NULL,
    [Iniciado_Por] VARCHAR(100) NOT NULL,
    [Comentario] VARCHAR(500) NULL,
    [Estado] VARCHAR(20) NOT NULL,
    [Intento_Numero] INT NOT NULL DEFAULT ((1)),
    [Max_Reintentos] INT NOT NULL DEFAULT ((0)),
    [Fecha_Solicitud] DATETIME2(0) NOT NULL DEFAULT (getdate()),
    [Fecha_Inicio] DATETIME2(0) NULL,
    [Fecha_Fin] DATETIME2(0) NULL,
    [PID_Runner] INT NULL,
    [Heartbeat_Ultimo] DATETIME2(0) NULL,
    [Timeout_Segundos] INT NOT NULL DEFAULT ((3600)),
    [Mensaje_Final] VARCHAR(1000) NULL,
    [ID_Log_Auditoria] INT NULL,
    CONSTRAINT [PK_Control_Corrida] PRIMARY KEY ([ID_Corrida])
);
END
GO

IF OBJECT_ID('[Control].[Corrida_Evento]','U') IS NULL
BEGIN
CREATE TABLE [Control].[Corrida_Evento] (
    [ID_Evento] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Corrida] VARCHAR(36) NOT NULL,
    [Tipo] VARCHAR(20) NOT NULL DEFAULT ('LOG'),
    [Mensaje] VARCHAR(4000) NOT NULL,
    [Fecha_Evento] DATETIME2(3) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Control_Corrida_Evento] PRIMARY KEY ([ID_Evento])
);
END
GO

IF OBJECT_ID('[Control].[Corrida_Paso]','U') IS NULL
BEGIN
CREATE TABLE [Control].[Corrida_Paso] (
    [ID_Paso] INT IDENTITY(1,1) NOT NULL,
    [ID_Corrida] VARCHAR(36) NOT NULL,
    [Nombre_Paso] VARCHAR(100) NOT NULL,
    [Orden] INT NOT NULL DEFAULT ((1)),
    [Estado] VARCHAR(20) NOT NULL DEFAULT ('PENDIENTE'),
    [Fecha_Inicio] DATETIME2(0) NULL,
    [Fecha_Fin] DATETIME2(0) NULL,
    [Mensaje_Error] VARCHAR(1000) NULL,
    CONSTRAINT [PK_Control_Corrida_Paso] PRIMARY KEY ([ID_Paso])
);
END
GO

-- ---- Schema [Auditoria] . 5 tablas ----

IF OBJECT_ID('[Auditoria].[Cambios_Portal]','U') IS NULL
BEGIN
CREATE TABLE [Auditoria].[Cambios_Portal] (
    [ID_Cambio] INT IDENTITY(1,1) NOT NULL,
    [Tabla_Afectada] VARCHAR(200) NOT NULL,
    [Registro_ID] VARCHAR(100) NOT NULL,
    [Campo] VARCHAR(200) NOT NULL,
    [Valor_Anterior] NVARCHAR(MAX) NULL,
    [Valor_Nuevo] NVARCHAR(MAX) NULL,
    [Usuario] VARCHAR(100) NOT NULL DEFAULT ('portal_user'),
    [Accion] VARCHAR(50) NOT NULL DEFAULT ('UPDATE'),
    [Fecha_Cambio] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Auditoria_Cambios_Portal] PRIMARY KEY ([ID_Cambio])
);
END
GO

IF OBJECT_ID('[Auditoria].[Log_Acceso]','U') IS NULL
BEGIN
CREATE TABLE [Auditoria].[Log_Acceso] (
    [ID_Acceso] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Usuario] VARCHAR(100) NOT NULL,
    [Accion] VARCHAR(200) NOT NULL,
    [Endpoint] VARCHAR(300) NULL,
    [Request_ID] VARCHAR(50) NULL,
    [IP_Origen] VARCHAR(50) NULL,
    [Resultado] VARCHAR(20) NOT NULL,
    [Detalle] VARCHAR(500) NULL,
    [Fecha_Accion] DATETIME2(0) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Auditoria_Log_Acceso] PRIMARY KEY ([ID_Acceso])
);
END
GO

IF OBJECT_ID('[Auditoria].[Log_Carga]','U') IS NULL
BEGIN
CREATE TABLE [Auditoria].[Log_Carga] (
    [ID_Log_Carga] BIGINT IDENTITY(1,1) NOT NULL,
    [Nombre_Proceso] NVARCHAR(150) NOT NULL,
    [Tabla_Destino] NVARCHAR(100) NOT NULL,
    [Nombre_Archivo_Fuente] NVARCHAR(255) NULL,
    [Filas_Leidas] INT NULL,
    [Filas_Insertadas] INT NULL,
    [Filas_Cuarentena] INT NULL,
    [Filas_Rechazadas] INT NULL,
    [Duracion_Segundos] DECIMAL(10,2) NULL,
    [Estado_Proceso] NVARCHAR(20) NOT NULL,
    [Mensaje_Error] NVARCHAR(MAX) NULL,
    [Fecha_Inicio] DATETIME2(7) NOT NULL,
    [Fecha_Fin] DATETIME2(7) NULL,
    CONSTRAINT [PK_Auditoria_Log_Carga] PRIMARY KEY ([ID_Log_Carga])
);
END
GO

IF OBJECT_ID('[Auditoria].[Log_Decisiones_MDM]','U') IS NULL
BEGIN
CREATE TABLE [Auditoria].[Log_Decisiones_MDM] (
    [ID_Log_MDM] BIGINT IDENTITY(1,1) NOT NULL,
    [ID_Cuarentena] BIGINT NOT NULL,
    [Accion] NVARCHAR(20) NOT NULL,
    [Valor_Original] NVARCHAR(500) NULL,
    [Valor_Final] NVARCHAR(500) NULL,
    [Analista_DNI] NVARCHAR(20) NOT NULL,
    [Comentario] NVARCHAR(500) NULL,
    [Fecha_Decision] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Auditoria_Log_Decisiones_MDM] PRIMARY KEY ([ID_Log_MDM])
);
END
GO

IF OBJECT_ID('[Auditoria].[Log_Versiones_Modelo]','U') IS NULL
BEGIN
CREATE TABLE [Auditoria].[Log_Versiones_Modelo] (
    [ID_Log_Modelo] BIGINT IDENTITY(1,1) NOT NULL,
    [Nombre_Modelo] NVARCHAR(100) NOT NULL,
    [Version_Modelo] NVARCHAR(50) NOT NULL,
    [Tipo_Escenario] NVARCHAR(50) NULL,
    [Fecha_Cutoff] DATETIME2(7) NOT NULL,
    [ID_Version_Datos] NVARCHAR(100) NULL,
    [WMAPE_Obtenido] DECIMAL(8,4) NULL,
    [MAE_Obtenido] DECIMAL(12,4) NULL,
    [Semanas_Evaluadas] INT NULL,
    [Estado] NVARCHAR(20) NOT NULL,
    [Mensaje_Error] NVARCHAR(MAX) NULL,
    [Fecha_Ejecucion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    CONSTRAINT [PK_Auditoria_Log_Versiones_Modelo] PRIMARY KEY ([ID_Log_Modelo])
);
END
GO

-- ---- Schema [Admin] . 1 tablas ----

IF OBJECT_ID('[Admin].[Migraciones_Aplicadas]','U') IS NULL
BEGIN
CREATE TABLE [Admin].[Migraciones_Aplicadas] (
    [ID_Migracion] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Archivo] NVARCHAR(255) NOT NULL,
    [Hash_SHA256] NVARCHAR(64) NOT NULL,
    [Fecha_Aplicacion] DATETIME2(7) NOT NULL DEFAULT (getdate()),
    [Ejecutado_Por] NVARCHAR(128) NOT NULL DEFAULT (suser_sname()),
    [Duracion_Segundos] FLOAT NULL,
    [Estado] NVARCHAR(20) NOT NULL DEFAULT ('OK'),
    [Mensaje_Error] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_Admin_Migraciones_Aplicadas] PRIMARY KEY ([ID_Migracion])
);
END
GO

-- ---- Schema [Seguridad] . 1 tablas ----

IF OBJECT_ID('[Seguridad].[Usuarios]','U') IS NULL
BEGIN
CREATE TABLE [Seguridad].[Usuarios] (
    [ID_Usuario] INT IDENTITY(1,1) NOT NULL,
    [Nombre_Usuario] VARCHAR(100) NOT NULL,
    [Nombre_Display] VARCHAR(200) NOT NULL,
    [Email] VARCHAR(200) NULL,
    [Hash_Clave] VARCHAR(300) NOT NULL,
    [Rol] VARCHAR(50) NOT NULL,
    [Es_Activo] BIT NOT NULL DEFAULT ((1)),
    [Fecha_Creacion] DATETIME2(0) NOT NULL DEFAULT (getdate()),
    [Ultimo_Acceso] DATETIME2(0) NULL,
    CONSTRAINT [PK_Seguridad_Usuarios] PRIMARY KEY ([ID_Usuario])
);
END
GO

-- ---- Schema [dbo] . 1 tablas ----

IF OBJECT_ID('[dbo].[sysdiagrams]','U') IS NULL
BEGIN
CREATE TABLE [dbo].[sysdiagrams] (
    [name] SYSNAME NOT NULL,
    [principal_id] INT NOT NULL,
    [diagram_id] INT IDENTITY(1,1) NOT NULL,
    [version] INT NULL,
    [definition] VARBINARY(MAX) NULL,
    CONSTRAINT [PK_dbo_sysdiagrams] PRIMARY KEY ([diagram_id])
);
END
GO

-- ========================================================================
-- INDICES (no-PK)
-- ========================================================================
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Regla_Modulo_Raw_Activa' AND object_id=OBJECT_ID('[MDM].[Regla_Modulo_Raw]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Regla_Modulo_Raw_Activa] ON [MDM].[Regla_Modulo_Raw] ([Modulo_Raw]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Mart_Crecimiento_Tiempo_Variedad' AND object_id=OBJECT_ID('[Gold].[Mart_Tasa_Crecimiento]'))
    CREATE NONCLUSTERED INDEX [IX_Mart_Crecimiento_Tiempo_Variedad] ON [Gold].[Mart_Tasa_Crecimiento] ([ID_Tiempo], [ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_DimCondicion_Sustrato_Cert' AND object_id=OBJECT_ID('[Silver].[Dim_Condicion_Cultivo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_DimCondicion_Sustrato_Cert] ON [Silver].[Dim_Condicion_Cultivo] ([Sustrato], [Certificacion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Maduracion_Geografia_Tiempo' AND object_id=OBJECT_ID('[Silver].[Fact_Maduracion]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Maduracion_Geografia_Tiempo] ON [Silver].[Fact_Maduracion] ([ID_Geografia], [ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Maduracion_Variedad_Estado' AND object_id=OBJECT_ID('[Silver].[Fact_Maduracion]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Maduracion_Variedad_Estado] ON [Silver].[Fact_Maduracion] ([ID_Variedad], [ID_Estado_Fenologico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Maduracion_Seguimiento' AND object_id=OBJECT_ID('[Silver].[Fact_Maduracion]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Maduracion_Seguimiento] ON [Silver].[Fact_Maduracion] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Cinta], [ID_Organo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactMaduracion_Gold_Cobertura' AND object_id=OBJECT_ID('[Silver].[Fact_Maduracion]'))
    CREATE NONCLUSTERED INDEX [IX_FactMaduracion_Gold_Cobertura] ON [Silver].[Fact_Maduracion] ([ID_Tiempo], [ID_Geografia], [ID_Variedad]) INCLUDE ([ID_Estado_Fenologico], [ID_Cinta], [Dias_Pasados_Del_Marcado], [ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Dim_Fund__298DCC3C6A594996' AND object_id=OBJECT_ID('[Silver].[Dim_Fundo_Catalogo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Dim_Fund__298DCC3C6A594996] ON [Silver].[Dim_Fundo_Catalogo] ([Fundo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_DimVariedad_Nombre' AND object_id=OBJECT_ID('[Silver].[Dim_Variedad]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_DimVariedad_Nombre] ON [Silver].[Dim_Variedad] ([Nombre_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Dim_Sect__8D0726BD1D4FAD94' AND object_id=OBJECT_ID('[Silver].[Dim_Sector_Catalogo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Dim_Sect__8D0726BD1D4FAD94] ON [Silver].[Dim_Sector_Catalogo] ([Sector]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_DimPersonal_DNI' AND object_id=OBJECT_ID('[Silver].[Dim_Personal]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_DimPersonal_DNI] ON [Silver].[Dim_Personal] ([DNI]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Catalogo__C54D121BA68E6270' AND object_id=OBJECT_ID('[MDM].[Catalogo_Variedades]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Catalogo__C54D121BA68E6270] ON [MDM].[Catalogo_Variedades] ([Nombre_Canonico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Telemetria_Clima_Tiempo_Sector' AND object_id=OBJECT_ID('[Silver].[Fact_Telemetria_Clima]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Telemetria_Clima_Tiempo_Sector] ON [Silver].[Fact_Telemetria_Clima] ([ID_Tiempo], [Sector_Climatico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Telemetria_Clima_Sector_Fecha' AND object_id=OBJECT_ID('[Silver].[Fact_Telemetria_Clima]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Telemetria_Clima_Sector_Fecha] ON [Silver].[Fact_Telemetria_Clima] ([Sector_Climatico], [Fecha_Evento]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_TelClima_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Telemetria_Clima]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_TelClima_Grain] ON [Silver].[Fact_Telemetria_Clima] ([ID_Tiempo], [Sector_Climatico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_CosechaSAP_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Cosecha_SAP]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_CosechaSAP_Grain] ON [Silver].[Fact_Cosecha_SAP] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Condicion_Cultivo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Dim_Turn__A1DE4AE8C2967396' AND object_id=OBJECT_ID('[Silver].[Dim_Turno_Catalogo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Dim_Turn__A1DE4AE8C2967396] ON [Silver].[Dim_Turno_Catalogo] ([Turno]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Catalogo__C035B8DDAA1D8C59' AND object_id=OBJECT_ID('[MDM].[Catalogo_Personal]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Catalogo__C035B8DDAA1D8C59] ON [MDM].[Catalogo_Personal] ([DNI]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_EvalVeg_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Evaluacion_Vegetativa]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_EvalVeg_Grain] ON [Silver].[Fact_Evaluacion_Vegetativa] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Campana], [Piso], [ID_Origen_Bronce]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Mart_Clima_Tiempo_Sector' AND object_id=OBJECT_ID('[Gold].[Mart_Clima]'))
    CREATE NONCLUSTERED INDEX [IX_Mart_Clima_Tiempo_Sector] ON [Gold].[Mart_Clima] ([ID_Tiempo], [Sector_Climatico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Induccion_Floral_Variedad_Fecha' AND object_id=OBJECT_ID('[Silver].[Fact_Induccion_Floral]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Induccion_Floral_Variedad_Fecha] ON [Silver].[Fact_Induccion_Floral] ([ID_Variedad], [Fecha_Evento]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_InducFloral_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Induccion_Floral]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_InducFloral_Grain] ON [Silver].[Fact_Induccion_Floral] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Personal], [Tipo_Evaluacion], [Codigo_Consumidor]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_ConteoFen_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Conteo_Fenologico]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_ConteoFen_Grain] ON [Silver].[Fact_Conteo_Fenologico] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Estado_Fenologico], [Punto]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactConteoFen_Tiempo_Estado' AND object_id=OBJECT_ID('[Silver].[Fact_Conteo_Fenologico]'))
    CREATE NONCLUSTERED INDEX [IX_FactConteoFen_Tiempo_Estado] ON [Silver].[Fact_Conteo_Fenologico] ([ID_Tiempo], [ID_Estado_Fenologico], [ID_Geografia], [ID_Variedad]) INCLUDE ([Cantidad_Organos], [Estado_DQ], [ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_ConteoFen_Performance' AND object_id=OBJECT_ID('[Silver].[Fact_Conteo_Fenologico]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_ConteoFen_Performance] ON [Silver].[Fact_Conteo_Fenologico] ([ID_Tiempo], [ID_Geografia], [ID_Variedad]) INCLUDE ([ID_Estado_Fenologico], [Cantidad_Organos], [Punto]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Homologacion_Lookup' AND object_id=OBJECT_ID('[MDM].[Diccionario_Homologacion]'))
    CREATE NONCLUSTERED INDEX [IX_Homologacion_Lookup] ON [MDM].[Diccionario_Homologacion] ([Tabla_Origen], [Campo_Origen], [Texto_Crudo]) INCLUDE ([Valor_Canonico], [Veces_Aplicado]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Dim_Valv__49518AF470B0136F' AND object_id=OBJECT_ID('[Silver].[Dim_Valvula_Catalogo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Dim_Valv__49518AF470B0136F] ON [Silver].[Dim_Valvula_Catalogo] ([Valvula]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Cuarentena_Estado_Tabla' AND object_id=OBJECT_ID('[MDM].[Cuarentena]'))
    CREATE NONCLUSTERED INDEX [IX_Cuarentena_Estado_Tabla] ON [MDM].[Cuarentena] ([Estado], [Tabla_Origen], [Fecha_Ingreso]) INCLUDE ([Campo_Origen], [Motivo], [Tipo_Regla], [Valor_Recibido], [ID_Registro_Origen]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Cambios_Usuario' AND object_id=OBJECT_ID('[Auditoria].[Cambios_Portal]'))
    CREATE NONCLUSTERED INDEX [IX_Cambios_Usuario] ON [Auditoria].[Cambios_Portal] ([Usuario]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Cambios_Tabla' AND object_id=OBJECT_ID('[Auditoria].[Cambios_Portal]'))
    CREATE NONCLUSTERED INDEX [IX_Cambios_Tabla] ON [Auditoria].[Cambios_Portal] ([Tabla_Afectada]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Cambios_Fecha' AND object_id=OBJECT_ID('[Auditoria].[Cambios_Portal]'))
    CREATE NONCLUSTERED INDEX [IX_Cambios_Fecha] ON [Auditoria].[Cambios_Portal] ([Fecha_Cambio]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Dim_Camp__83BC75CA5880B909' AND object_id=OBJECT_ID('[Silver].[Dim_Campana]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Dim_Camp__83BC75CA5880B909] ON [Silver].[Dim_Campana] ([Nombre_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Parametr__65BA970343823AE6' AND object_id=OBJECT_ID('[Config].[Parametros_Pipeline]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Parametr__65BA970343823AE6] ON [Config].[Parametros_Pipeline] ([Nombre_Parametro]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Proyecciones_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Proyecciones]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Proyecciones_Grain] ON [Silver].[Fact_Proyecciones] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Escenario], [Fecha_Cutoff]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_TasaCrecimiento_Tiempo_Geografia' AND object_id=OBJECT_ID('[Silver].[Fact_Tasa_Crecimiento_Brotes]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_TasaCrecimiento_Tiempo_Geografia] ON [Silver].[Fact_Tasa_Crecimiento_Brotes] ([ID_Tiempo], [ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_TasaCrecimiento_Variedad_Fecha' AND object_id=OBJECT_ID('[Silver].[Fact_Tasa_Crecimiento_Brotes]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_TasaCrecimiento_Variedad_Fecha] ON [Silver].[Fact_Tasa_Crecimiento_Brotes] ([ID_Variedad], [Fecha_Evento]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_TasaCrecimiento_Ensayo' AND object_id=OBJECT_ID('[Silver].[Fact_Tasa_Crecimiento_Brotes]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_TasaCrecimiento_Ensayo] ON [Silver].[Fact_Tasa_Crecimiento_Brotes] ([Codigo_Ensayo], [Fecha_Evento]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_TCBrotes_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Tasa_Crecimiento_Brotes]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_TCBrotes_Grain] ON [Silver].[Fact_Tasa_Crecimiento_Brotes] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [Tipo_Evaluacion], [Tipo_Tallo], [Codigo_Ensayo], [Medida_Crecimiento], [Codigo_Origen]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_Combinacion_Geografica_Nueva' AND object_id=OBJECT_ID('[Silver].[Dim_Geografia]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_Combinacion_Geografica_Nueva] ON [Silver].[Dim_Geografia] ([ID_Fundo_Catalogo], [ID_Sector_Catalogo], [ID_Modulo_Catalogo], [ID_Turno_Catalogo], [ID_Valvula_Catalogo], [ID_Cama_Catalogo], [Fecha_Inicio_Vigencia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_DimGeo_ModuloTurnoValvula_Vigente' AND object_id=OBJECT_ID('[Silver].[Dim_Geografia]'))
    CREATE NONCLUSTERED INDEX [IX_DimGeo_ModuloTurnoValvula_Vigente] ON [Silver].[Dim_Geografia] ([ID_Modulo_Catalogo], [ID_Turno_Catalogo], [ID_Valvula_Catalogo]) INCLUDE ([ID_Fundo_Catalogo], [ID_Sector_Catalogo], [ID_Cama_Catalogo], [Codigo_SAP_Campo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_DimGeo_Catalogo_Performance' AND object_id=OBJECT_ID('[Silver].[Dim_Geografia]'))
    CREATE NONCLUSTERED INDEX [IX_DimGeo_Catalogo_Performance] ON [Silver].[Dim_Geografia] ([ID_Modulo_Catalogo], [ID_Turno_Catalogo], [ID_Valvula_Catalogo], [Es_Vigente]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_LogCarga_Tabla_Fecha' AND object_id=OBJECT_ID('[Auditoria].[Log_Carga]'))
    CREATE NONCLUSTERED INDEX [IX_LogCarga_Tabla_Fecha] ON [Auditoria].[Log_Carga] ([Tabla_Destino], [Fecha_Inicio]) INCLUDE ([Estado_Proceso], [Filas_Insertadas], [Filas_Cuarentena], [Filas_Rechazadas], [Duracion_Segundos]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Regla_Modulo_Turno_SubModulo_Busqueda' AND object_id=OBJECT_ID('[MDM].[Regla_Modulo_Turno_SubModulo]'))
    CREATE NONCLUSTERED INDEX [IX_Regla_Modulo_Turno_SubModulo_Busqueda] ON [MDM].[Regla_Modulo_Turno_SubModulo] ([Modulo_Raw_Base], [Es_Activa], [Turno_Desde], [Turno_Hasta], [Prioridad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Censo_Plantas_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Censo_Plantas]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Censo_Plantas_Grain] ON [Silver].[Fact_Censo_Plantas] ([ID_Geografia], [ID_Tiempo], [ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactCenso_Geografia_Tiempo' AND object_id=OBJECT_ID('[Silver].[Fact_Censo_Plantas]'))
    CREATE NONCLUSTERED INDEX [IX_FactCenso_Geografia_Tiempo] ON [Silver].[Fact_Censo_Plantas] ([ID_Geografia], [ID_Tiempo]) INCLUDE ([ID_Variedad], [Plantas_Buenas], [Plantas_Regulares], [Plantas_Malas]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UK_principal_name' AND object_id=OBJECT_ID('[dbo].[sysdiagrams]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UK_principal_name] ON [dbo].[sysdiagrams] ([principal_id], [name]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_EvalPesos_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Evaluacion_Pesos]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_EvalPesos_Grain] ON [Silver].[Fact_Evaluacion_Pesos] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactPesos_Gold_Cobertura' AND object_id=OBJECT_ID('[Silver].[Fact_Evaluacion_Pesos]'))
    CREATE NONCLUSTERED INDEX [IX_FactPesos_Gold_Cobertura] ON [Silver].[Fact_Evaluacion_Pesos] ([ID_Tiempo], [ID_Geografia], [ID_Variedad]) INCLUDE ([Peso_Promedio_Baya_g], [Cantidad_Bayas_Muestra], [Peso_Proyectado_Baya_g], [Estado_DQ], [ID_Personal], [ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_Usuarios_Nombre' AND object_id=OBJECT_ID('[Seguridad].[Usuarios]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_Usuarios_Nombre] ON [Seguridad].[Usuarios] ([Nombre_Usuario]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Usuarios_NombreUsuario' AND object_id=OBJECT_ID('[Seguridad].[Usuarios]'))
    CREATE NONCLUSTERED INDEX [IX_Usuarios_NombreUsuario] ON [Seguridad].[Usuarios] ([Nombre_Usuario]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Bronce_Induccion_Floral_EstadoCarga' AND object_id=OBJECT_ID('[Bronce].[Induccion_Floral]'))
    CREATE NONCLUSTERED INDEX [IX_Bronce_Induccion_Floral_EstadoCarga] ON [Bronce].[Induccion_Floral] ([Estado_Carga], [Fecha_Sistema]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Bronce_Evaluacion_Vegetativa_Estado' AND object_id=OBJECT_ID('[Bronce].[Floracion]'))
    CREATE NONCLUSTERED INDEX [IX_Bronce_Evaluacion_Vegetativa_Estado] ON [Bronce].[Floracion] ([Estado_Carga], [Fecha_Raw]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_CicloPoda_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Ciclo_Poda]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_CicloPoda_Grain] ON [Silver].[Fact_Ciclo_Poda] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [Tipo_Evaluacion], [Punto]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactCicloPoda_Tiempo_Variedad' AND object_id=OBJECT_ID('[Silver].[Fact_Ciclo_Poda]'))
    CREATE NONCLUSTERED INDEX [IX_FactCicloPoda_Tiempo_Variedad] ON [Silver].[Fact_Ciclo_Poda] ([ID_Tiempo], [ID_Variedad]) INCLUDE ([ID_Geografia], [Tipo_Evaluacion], [Estado_DQ]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_LogAcceso_Usuario_Fecha' AND object_id=OBJECT_ID('[Auditoria].[Log_Acceso]'))
    CREATE NONCLUSTERED INDEX [IX_LogAcceso_Usuario_Fecha] ON [Auditoria].[Log_Acceso] ([Nombre_Usuario], [Fecha_Accion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Evaluacion_Vegetativa_Analitica' AND object_id=OBJECT_ID('[Silver].[Fact_Floracion]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Evaluacion_Vegetativa_Analitica] ON [Silver].[Fact_Floracion] ([ID_Tiempo], [ID_Geografia], [ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Floracion_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Floracion]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Floracion_Grain] ON [Silver].[Fact_Floracion] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [ID_Personal], [Tipo_Evaluacion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Corrida_Estado' AND object_id=OBJECT_ID('[Control].[Corrida]'))
    CREATE NONCLUSTERED INDEX [IX_Corrida_Estado] ON [Control].[Corrida] ([Estado], [Fecha_Solicitud]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Corrida_Activas_Heartbeat' AND object_id=OBJECT_ID('[Control].[Corrida]'))
    CREATE NONCLUSTERED INDEX [IX_Corrida_Activas_Heartbeat] ON [Control].[Corrida] ([Estado], [Heartbeat_Ultimo], [Fecha_Solicitud]) INCLUDE ([Fecha_Inicio], [PID_Runner], [Timeout_Segundos], [Iniciado_Por], [ID_Log_Auditoria]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Corrida_FechaSolicitud' AND object_id=OBJECT_ID('[Control].[Corrida]'))
    CREATE NONCLUSTERED INDEX [IX_Corrida_FechaSolicitud] ON [Control].[Corrida] ([Fecha_Solicitud]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Tareo_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Tareo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Tareo_Grain] ON [Silver].[Fact_Tareo] ([ID_Geografia], [ID_Tiempo], [ID_Personal], [ID_Actividad_Operativa]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactTareo_Tiempo_Personal' AND object_id=OBJECT_ID('[Silver].[Fact_Tareo]'))
    CREATE NONCLUSTERED INDEX [IX_FactTareo_Tiempo_Personal] ON [Silver].[Fact_Tareo] ([ID_Tiempo], [ID_Personal]) INCLUDE ([ID_Geografia], [ID_Actividad_Operativa], [Horas_Trabajadas], [Es_Observado_SAP]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_Migraciones_Nombre' AND object_id=OBJECT_ID('[Admin].[Migraciones_Aplicadas]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_Migraciones_Nombre] ON [Admin].[Migraciones_Aplicadas] ([Nombre_Archivo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Evento_Corrida_ID' AND object_id=OBJECT_ID('[Control].[Corrida_Evento]'))
    CREATE NONCLUSTERED INDEX [IX_Evento_Corrida_ID] ON [Control].[Corrida_Evento] ([ID_Corrida], [ID_Evento]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Evento_Corrida_Fecha' AND object_id=OBJECT_ID('[Control].[Corrida_Evento]'))
    CREATE NONCLUSTERED INDEX [IX_Evento_Corrida_Fecha] ON [Control].[Corrida_Evento] ([ID_Corrida], [Fecha_Evento], [ID_Evento]) INCLUDE ([Tipo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Fisiologia_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Fisiologia]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Fisiologia_Grain] ON [Silver].[Fact_Fisiologia] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [Tercio]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactFisiologia_Tiempo_Variedad' AND object_id=OBJECT_ID('[Silver].[Fact_Fisiologia]'))
    CREATE NONCLUSTERED INDEX [IX_FactFisiologia_Tiempo_Variedad] ON [Silver].[Fact_Fisiologia] ([ID_Tiempo], [ID_Variedad], [ID_Geografia]) INCLUDE ([Tercio], [Brotes_Productivos], [Brotes_Vegetativos], [Hinchadas], [Productivas], [Total_Organos], [Estado_DQ], [ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Paso_Corrida_Orden' AND object_id=OBJECT_ID('[Control].[Corrida_Paso]'))
    CREATE NONCLUSTERED INDEX [IX_Paso_Corrida_Orden] ON [Control].[Corrida_Paso] ([ID_Corrida], [Orden], [ID_Paso]) INCLUDE ([Nombre_Paso], [Estado], [Fecha_Inicio], [Fecha_Fin], [Mensaje_Error]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ_Bridge_GCC_Hash' AND object_id=OBJECT_ID('[Silver].[Bridge_Geografia_Campana_Condicion]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_Bridge_GCC_Hash] ON [Silver].[Bridge_Geografia_Campana_Condicion] ([Hash_Llave]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Bridge_GCC_Geo_Vigencia' AND object_id=OBJECT_ID('[Silver].[Bridge_Geografia_Campana_Condicion]'))
    CREATE NONCLUSTERED INDEX [IX_Bridge_GCC_Geo_Vigencia] ON [Silver].[Bridge_Geografia_Campana_Condicion] ([ID_Geografia], [Vigencia_Inicio], [Vigencia_Fin]) INCLUDE ([ID_Campana], [ID_Condicion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Fact_Peladas_Performance' AND object_id=OBJECT_ID('[Silver].[Fact_Peladas_Old]'))
    CREATE NONCLUSTERED INDEX [IX_Fact_Peladas_Performance] ON [Silver].[Fact_Peladas_Old] ([ID_Tiempo], [ID_Geografia]) INCLUDE ([Plantas_Productivas], [Plantas_No_Productivas]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UQ__Parametr__38B4F5FBA7F343D9' AND object_id=OBJECT_ID('[MDM].[Parametros_Validacion]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UQ__Parametr__38B4F5FBA7F343D9] ON [MDM].[Parametros_Validacion] ([Nombre_Regla]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Comando_Pendiente' AND object_id=OBJECT_ID('[Control].[Comando_Ejecucion]'))
    CREATE NONCLUSTERED INDEX [IX_Comando_Pendiente] ON [Control].[Comando_Ejecucion] ([Estado_Cmd], [Fecha_Comando]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Comando_Procesando' AND object_id=OBJECT_ID('[Control].[Comando_Ejecucion]'))
    CREATE NONCLUSTERED INDEX [IX_Comando_Procesando] ON [Control].[Comando_Ejecucion] ([Estado_Cmd], [Fecha_Proceso]) INCLUDE ([ID_Corrida], [Tipo_Comando], [Iniciado_Por], [Timeout_Seg]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Fact_Peladas_Grain' AND object_id=OBJECT_ID('[Silver].[Fact_Peladas]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Fact_Peladas_Grain] ON [Silver].[Fact_Peladas] ([ID_Geografia], [ID_Tiempo], [ID_Variedad], [Punto], [ID_Estado_Fenologico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_FactPeladas_Tiempo_Variedad' AND object_id=OBJECT_ID('[Silver].[Fact_Peladas]'))
    CREATE NONCLUSTERED INDEX [IX_FactPeladas_Tiempo_Variedad] ON [Silver].[Fact_Peladas] ([ID_Tiempo], [ID_Variedad], [ID_Geografia]) INCLUDE ([ID_Estado_Fenologico], [Cantidad], [Muestras], [Plantas_Productivas], [Plantas_No_Productivas], [Estado_DQ]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Dim_Cama_Catalogo_Cama' AND object_id=OBJECT_ID('[Silver].[Dim_Cama_Catalogo]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Dim_Cama_Catalogo_Cama] ON [Silver].[Dim_Cama_Catalogo] ([Cama_Normalizada]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='UX_Bridge_Geografia_Cama_Estado' AND object_id=OBJECT_ID('[Silver].[Bridge_Geografia_Cama]'))
    CREATE UNIQUE NONCLUSTERED INDEX [UX_Bridge_Geografia_Cama_Estado] ON [Silver].[Bridge_Geografia_Cama] ([ID_Geografia], [ID_Cama_Catalogo], [Es_Vigente], [Fecha_Fin_Vigencia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_Bridge_Geografia_Cama_Lookup' AND object_id=OBJECT_ID('[Silver].[Bridge_Geografia_Cama]'))
    CREATE NONCLUSTERED INDEX [IX_Bridge_Geografia_Cama_Lookup] ON [Silver].[Bridge_Geografia_Cama] ([ID_Geografia], [Es_Vigente]) INCLUDE ([ID_Cama_Catalogo], [Fecha_Inicio_Vigencia], [Fecha_Fin_Vigencia]);
GO

-- ========================================================================
-- FOREIGN KEYS
-- ========================================================================
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cicl__ID_Ca__4336F4B9')
    ALTER TABLE [Silver].[Fact_Ciclo_Poda] WITH CHECK ADD CONSTRAINT [FK__Fact_Cicl__ID_Ca__4336F4B9] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cicl__ID_Ti__55F4C372')
    ALTER TABLE [Silver].[Fact_Ciclo_Poda] WITH CHECK ADD CONSTRAINT [FK__Fact_Cicl__ID_Ti__55F4C372] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cicl__ID_Va__56E8E7AB')
    ALTER TABLE [Silver].[Fact_Ciclo_Poda] WITH CHECK ADD CONSTRAINT [FK__Fact_Cicl__ID_Va__56E8E7AB] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cont__ID_Ca__442B18F2')
    ALTER TABLE [Silver].[Fact_Conteo_Fenologico] WITH CHECK ADD CONSTRAINT [FK__Fact_Cont__ID_Ca__442B18F2] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cont__ID_Es__2CF2ADDF')
    ALTER TABLE [Silver].[Fact_Conteo_Fenologico] WITH CHECK ADD CONSTRAINT [FK__Fact_Cont__ID_Es__2CF2ADDF] FOREIGN KEY ([ID_Estado_Fenologico]) REFERENCES [Silver].[Dim_Estado_Fenologico] ([ID_Estado_Fenologico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cont__ID_Pe__2B0A656D')
    ALTER TABLE [Silver].[Fact_Conteo_Fenologico] WITH CHECK ADD CONSTRAINT [FK__Fact_Cont__ID_Pe__2B0A656D] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cont__ID_Ti__29221CFB')
    ALTER TABLE [Silver].[Fact_Conteo_Fenologico] WITH CHECK ADD CONSTRAINT [FK__Fact_Cont__ID_Ti__29221CFB] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cont__ID_Va__2A164134')
    ALTER TABLE [Silver].[Fact_Conteo_Fenologico] WITH CHECK ADD CONSTRAINT [FK__Fact_Cont__ID_Va__2A164134] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cose__ID_Ca__451F3D2B')
    ALTER TABLE [Silver].[Fact_Cosecha_SAP] WITH CHECK ADD CONSTRAINT [FK__Fact_Cose__ID_Ca__451F3D2B] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cose__ID_Co__22751F6C')
    ALTER TABLE [Silver].[Fact_Cosecha_SAP] WITH CHECK ADD CONSTRAINT [FK__Fact_Cose__ID_Co__22751F6C] FOREIGN KEY ([ID_Condicion_Cultivo]) REFERENCES [Silver].[Dim_Condicion_Cultivo] ([ID_Condicion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cose__ID_Ti__208CD6FA')
    ALTER TABLE [Silver].[Fact_Cosecha_SAP] WITH CHECK ADD CONSTRAINT [FK__Fact_Cose__ID_Ti__208CD6FA] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Cose__ID_Va__2180FB33')
    ALTER TABLE [Silver].[Fact_Cosecha_SAP] WITH CHECK ADD CONSTRAINT [FK__Fact_Cose__ID_Va__2180FB33] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Ca__2724C5F0')
    ALTER TABLE [Silver].[Fact_Evaluacion_Vegetativa] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Ca__2724C5F0] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Ca__46136164')
    ALTER TABLE [Silver].[Fact_Evaluacion_Pesos] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Ca__46136164] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Ca__4707859D')
    ALTER TABLE [Silver].[Fact_Floracion] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Ca__4707859D] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Ge__24485945')
    ALTER TABLE [Silver].[Fact_Evaluacion_Vegetativa] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Ge__24485945] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Pe__4F47C5E3')
    ALTER TABLE [Silver].[Fact_Evaluacion_Pesos] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Pe__4F47C5E3] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Ti__253C7D7E')
    ALTER TABLE [Silver].[Fact_Evaluacion_Vegetativa] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Ti__253C7D7E] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Ti__4D5F7D71')
    ALTER TABLE [Silver].[Fact_Evaluacion_Pesos] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Ti__4D5F7D71] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Va__2630A1B7')
    ALTER TABLE [Silver].[Fact_Evaluacion_Vegetativa] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Va__2630A1B7] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Eval__ID_Va__4E53A1AA')
    ALTER TABLE [Silver].[Fact_Evaluacion_Pesos] WITH CHECK ADD CONSTRAINT [FK__Fact_Eval__ID_Va__4E53A1AA] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Fisi__ID_Ca__47FBA9D6')
    ALTER TABLE [Silver].[Fact_Fisiologia] WITH CHECK ADD CONSTRAINT [FK__Fact_Fisi__ID_Ca__47FBA9D6] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Fisi__ID_Ti__65370702')
    ALTER TABLE [Silver].[Fact_Fisiologia] WITH CHECK ADD CONSTRAINT [FK__Fact_Fisi__ID_Ti__65370702] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Fisi__ID_Va__662B2B3B')
    ALTER TABLE [Silver].[Fact_Fisiologia] WITH CHECK ADD CONSTRAINT [FK__Fact_Fisi__ID_Va__662B2B3B] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Indu__ID_Ca__48EFCE0F')
    ALTER TABLE [Silver].[Fact_Induccion_Floral] WITH CHECK ADD CONSTRAINT [FK__Fact_Indu__ID_Ca__48EFCE0F] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Madu__ID_Ca__49E3F248')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK__Fact_Madu__ID_Ca__49E3F248] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Ca__4AD81681')
    ALTER TABLE [Silver].[Fact_Peladas_Old] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Ca__4AD81681] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Es__7775B2CE')
    ALTER TABLE [Silver].[Fact_Peladas] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Es__7775B2CE] FOREIGN KEY ([ID_Estado_Fenologico]) REFERENCES [Silver].[Dim_Estado_Fenologico] ([ID_Estado_Fenologico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Ge__73A521EA')
    ALTER TABLE [Silver].[Fact_Peladas] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Ge__73A521EA] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Pe__6DCC4D03')
    ALTER TABLE [Silver].[Fact_Peladas_Old] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Pe__6DCC4D03] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Pe__76818E95')
    ALTER TABLE [Silver].[Fact_Peladas] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Pe__76818E95] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Ti__6BE40491')
    ALTER TABLE [Silver].[Fact_Peladas_Old] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Ti__6BE40491] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Ti__74994623')
    ALTER TABLE [Silver].[Fact_Peladas] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Ti__74994623] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Va__6CD828CA')
    ALTER TABLE [Silver].[Fact_Peladas_Old] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Va__6CD828CA] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Pela__ID_Va__758D6A5C')
    ALTER TABLE [Silver].[Fact_Peladas] WITH CHECK ADD CONSTRAINT [FK__Fact_Pela__ID_Va__758D6A5C] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Proy__ID_Ca__4BCC3ABA')
    ALTER TABLE [Silver].[Fact_Proyecciones] WITH CHECK ADD CONSTRAINT [FK__Fact_Proy__ID_Ca__4BCC3ABA] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Proy__ID_Es__395884C4')
    ALTER TABLE [Silver].[Fact_Proyecciones] WITH CHECK ADD CONSTRAINT [FK__Fact_Proy__ID_Es__395884C4] FOREIGN KEY ([ID_Escenario]) REFERENCES [Silver].[Dim_Escenario_Proyeccion] ([ID_Escenario]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Proy__ID_Es__3A4CA8FD')
    ALTER TABLE [Silver].[Fact_Proyecciones] WITH CHECK ADD CONSTRAINT [FK__Fact_Proy__ID_Es__3A4CA8FD] FOREIGN KEY ([ID_Estado_Workflow]) REFERENCES [Silver].[Dim_Estado_Workflow] ([ID_Workflow]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Proy__ID_Ti__37703C52')
    ALTER TABLE [Silver].[Fact_Proyecciones] WITH CHECK ADD CONSTRAINT [FK__Fact_Proy__ID_Ti__37703C52] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Proy__ID_Va__3864608B')
    ALTER TABLE [Silver].[Fact_Proyecciones] WITH CHECK ADD CONSTRAINT [FK__Fact_Proy__ID_Va__3864608B] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Sani__ID_Ca__4CC05EF3')
    ALTER TABLE [Silver].[Fact_Censo_Plantas] WITH CHECK ADD CONSTRAINT [FK__Fact_Sani__ID_Ca__4CC05EF3] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Sani__ID_Ti__47A6A41B')
    ALTER TABLE [Silver].[Fact_Censo_Plantas] WITH CHECK ADD CONSTRAINT [FK__Fact_Sani__ID_Ti__47A6A41B] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Sani__ID_Va__489AC854')
    ALTER TABLE [Silver].[Fact_Censo_Plantas] WITH CHECK ADD CONSTRAINT [FK__Fact_Sani__ID_Va__489AC854] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tare__ID_Ac__5E8A0973')
    ALTER TABLE [Silver].[Fact_Tareo] WITH CHECK ADD CONSTRAINT [FK__Fact_Tare__ID_Ac__5E8A0973] FOREIGN KEY ([ID_Actividad_Operativa]) REFERENCES [Silver].[Dim_Actividad_Operativa] ([ID_Actividad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tare__ID_Ca__4DB4832C')
    ALTER TABLE [Silver].[Fact_Tareo] WITH CHECK ADD CONSTRAINT [FK__Fact_Tare__ID_Ca__4DB4832C] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tare__ID_Pe__5D95E53A')
    ALTER TABLE [Silver].[Fact_Tareo] WITH CHECK ADD CONSTRAINT [FK__Fact_Tare__ID_Pe__5D95E53A] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tare__ID_Pe__5F7E2DAC')
    ALTER TABLE [Silver].[Fact_Tareo] WITH CHECK ADD CONSTRAINT [FK__Fact_Tare__ID_Pe__5F7E2DAC] FOREIGN KEY ([ID_Personal_Supervisor]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tare__ID_Ti__5CA1C101')
    ALTER TABLE [Silver].[Fact_Tareo] WITH CHECK ADD CONSTRAINT [FK__Fact_Tare__ID_Ti__5CA1C101] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tasa__ID_Ca__4EA8A765')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK__Fact_Tasa__ID_Ca__4EA8A765] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Fact_Tele__ID_Ca__4F9CCB9E')
    ALTER TABLE [Silver].[Fact_Telemetria_Clima] WITH CHECK ADD CONSTRAINT [FK__Fact_Tele__ID_Ca__4F9CCB9E] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK__Log_Decis__ID_Cu__3FD07829')
    ALTER TABLE [Auditoria].[Log_Decisiones_MDM] WITH CHECK ADD CONSTRAINT [FK__Log_Decis__ID_Cu__3FD07829] FOREIGN KEY ([ID_Cuarentena]) REFERENCES [MDM].[Cuarentena] ([ID_Cuarentena]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Bridge_GCC_Cmp')
    ALTER TABLE [Silver].[Bridge_Geografia_Campana_Condicion] WITH CHECK ADD CONSTRAINT [FK_Bridge_GCC_Cmp] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Bridge_GCC_Cnd')
    ALTER TABLE [Silver].[Bridge_Geografia_Campana_Condicion] WITH CHECK ADD CONSTRAINT [FK_Bridge_GCC_Cnd] FOREIGN KEY ([ID_Condicion]) REFERENCES [Silver].[Dim_Condicion_Cultivo] ([ID_Condicion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Bridge_GCC_Geo')
    ALTER TABLE [Silver].[Bridge_Geografia_Campana_Condicion] WITH CHECK ADD CONSTRAINT [FK_Bridge_GCC_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Bridge_Geografia_Cama_Dim_Cama_Catalogo_REAL')
    ALTER TABLE [Silver].[Bridge_Geografia_Cama] WITH CHECK ADD CONSTRAINT [FK_Bridge_Geografia_Cama_Dim_Cama_Catalogo_REAL] FOREIGN KEY ([ID_Cama_Catalogo]) REFERENCES [Silver].[Dim_Cama_Catalogo] ([ID_Cama_Catalogo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Bridge_Geografia_Cama_Dim_Geografia')
    ALTER TABLE [Silver].[Bridge_Geografia_Cama] WITH CHECK ADD CONSTRAINT [FK_Bridge_Geografia_Cama_Dim_Geografia] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Comando_Corrida')
    ALTER TABLE [Control].[Comando_Ejecucion] WITH CHECK ADD CONSTRAINT [FK_Comando_Corrida] FOREIGN KEY ([ID_Corrida]) REFERENCES [Control].[Corrida] ([ID_Corrida]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Evento_Corrida')
    ALTER TABLE [Control].[Corrida_Evento] WITH CHECK ADD CONSTRAINT [FK_Evento_Corrida] FOREIGN KEY ([ID_Corrida]) REFERENCES [Control].[Corrida] ([ID_Corrida]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Ciclo_Poda_Geo')
    ALTER TABLE [Silver].[Fact_Ciclo_Poda] WITH CHECK ADD CONSTRAINT [FK_Fact_Ciclo_Poda_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_ConteoFen_Geo')
    ALTER TABLE [Silver].[Fact_Conteo_Fenologico] WITH CHECK ADD CONSTRAINT [FK_Fact_ConteoFen_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Cosecha_SAP_Geo')
    ALTER TABLE [Silver].[Fact_Cosecha_SAP] WITH CHECK ADD CONSTRAINT [FK_Fact_Cosecha_SAP_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_EvalPesos_Geo')
    ALTER TABLE [Silver].[Fact_Evaluacion_Pesos] WITH CHECK ADD CONSTRAINT [FK_Fact_EvalPesos_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Fisiologia_Geo')
    ALTER TABLE [Silver].[Fact_Fisiologia] WITH CHECK ADD CONSTRAINT [FK_Fact_Fisiologia_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Induccion_Floral_Geografia')
    ALTER TABLE [Silver].[Fact_Induccion_Floral] WITH CHECK ADD CONSTRAINT [FK_Fact_Induccion_Floral_Geografia] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Induccion_Floral_Personal')
    ALTER TABLE [Silver].[Fact_Induccion_Floral] WITH CHECK ADD CONSTRAINT [FK_Fact_Induccion_Floral_Personal] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Induccion_Floral_Tiempo')
    ALTER TABLE [Silver].[Fact_Induccion_Floral] WITH CHECK ADD CONSTRAINT [FK_Fact_Induccion_Floral_Tiempo] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Induccion_Floral_Variedad')
    ALTER TABLE [Silver].[Fact_Induccion_Floral] WITH CHECK ADD CONSTRAINT [FK_Fact_Induccion_Floral_Variedad] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Maduracion_Cinta')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK_Fact_Maduracion_Cinta] FOREIGN KEY ([ID_Cinta]) REFERENCES [Silver].[Dim_Cinta] ([ID_Cinta]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Maduracion_Estado_Fenologico')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK_Fact_Maduracion_Estado_Fenologico] FOREIGN KEY ([ID_Estado_Fenologico]) REFERENCES [Silver].[Dim_Estado_Fenologico] ([ID_Estado_Fenologico]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Maduracion_Geo')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK_Fact_Maduracion_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Maduracion_Personal')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK_Fact_Maduracion_Personal] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Maduracion_Tiempo')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK_Fact_Maduracion_Tiempo] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Maduracion_Variedad')
    ALTER TABLE [Silver].[Fact_Maduracion] WITH CHECK ADD CONSTRAINT [FK_Fact_Maduracion_Variedad] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Peladas_Geo')
    ALTER TABLE [Silver].[Fact_Peladas_Old] WITH CHECK ADD CONSTRAINT [FK_Fact_Peladas_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Proyecciones_Geo')
    ALTER TABLE [Silver].[Fact_Proyecciones] WITH CHECK ADD CONSTRAINT [FK_Fact_Proyecciones_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Sanidad_Activo_Geo')
    ALTER TABLE [Silver].[Fact_Censo_Plantas] WITH CHECK ADD CONSTRAINT [FK_Fact_Sanidad_Activo_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Tareo_Geo')
    ALTER TABLE [Silver].[Fact_Tareo] WITH CHECK ADD CONSTRAINT [FK_Fact_Tareo_Geo] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_TasaCrec_Campana')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK_Fact_TasaCrec_Campana] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_TasaCrec_Condicion')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK_Fact_TasaCrec_Condicion] FOREIGN KEY ([ID_Condicion]) REFERENCES [Silver].[Dim_Condicion_Cultivo] ([ID_Condicion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_TasaCrecimiento_Geografia')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK_Fact_TasaCrecimiento_Geografia] FOREIGN KEY ([ID_Geografia]) REFERENCES [Silver].[Dim_Geografia] ([ID_Geografia]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_TasaCrecimiento_Personal')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK_Fact_TasaCrecimiento_Personal] FOREIGN KEY ([ID_Personal]) REFERENCES [Silver].[Dim_Personal] ([ID_Personal]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_TasaCrecimiento_Tiempo')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK_Fact_TasaCrecimiento_Tiempo] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_TasaCrecimiento_Variedad')
    ALTER TABLE [Silver].[Fact_Tasa_Crecimiento_Brotes] WITH CHECK ADD CONSTRAINT [FK_Fact_TasaCrecimiento_Variedad] FOREIGN KEY ([ID_Variedad]) REFERENCES [Silver].[Dim_Variedad] ([ID_Variedad]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Fact_Telemetria_Clima_Tiempo')
    ALTER TABLE [Silver].[Fact_Telemetria_Clima] WITH CHECK ADD CONSTRAINT [FK_Fact_Telemetria_Clima_Tiempo] FOREIGN KEY ([ID_Tiempo]) REFERENCES [Silver].[Dim_Tiempo] ([ID_Tiempo]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_FactAreasPlantas_Campana')
    ALTER TABLE [Silver].[Fact_areas_plantas] WITH CHECK ADD CONSTRAINT [FK_FactAreasPlantas_Campana] FOREIGN KEY ([ID_Campana]) REFERENCES [Silver].[Dim_Campana] ([ID_Campana]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_FactAreasPlantas_Condicion')
    ALTER TABLE [Silver].[Fact_areas_plantas] WITH CHECK ADD CONSTRAINT [FK_FactAreasPlantas_Condicion] FOREIGN KEY ([ID_Condicion]) REFERENCES [Silver].[Dim_Condicion_Cultivo] ([ID_Condicion]);
GO
IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_Paso_Corrida')
    ALTER TABLE [Control].[Corrida_Paso] WITH CHECK ADD CONSTRAINT [FK_Paso_Corrida] FOREIGN KEY ([ID_Corrida]) REFERENCES [Control].[Corrida] ([ID_Corrida]);
GO

-- ========================================================================
-- VIEWS / PROCEDURES / FUNCTIONS / TRIGGERS
-- ========================================================================

-- [Control].[sp_Purgar_Historial_Control] (SQL_STORED_PROCEDURE)
CREATE   PROCEDURE Control.sp_Purgar_Historial_Control
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

-- [Control].[vw_Cola_Comandos] (VIEW)
CREATE   VIEW Control.vw_Cola_Comandos
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
    ON c.ID_Corrida = cmd.ID_Corrida;
GO

-- [Control].[vw_Corridas_Activas] (VIEW)
CREATE   VIEW Control.vw_Corridas_Activas
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
    l.[Nombre_Archivo_Fuente] AS Nombre_Ejecucion_Auditoria,
    l.Tabla_Destino,
    l.[Estado_Proceso] AS Estado_Auditoria
FROM Control.Corrida c
LEFT JOIN Auditoria.Log_Carga l
    ON l.ID_Log_Carga = c.ID_Log_Auditoria
WHERE c.Estado IN ('PENDIENTE', 'EJECUTANDO');
GO

-- [Control].[vw_Ultima_Corrida_Por_Tabla] (VIEW)
CREATE   VIEW Control.vw_Ultima_Corrida_Por_Tabla
        AS
        WITH ultimas AS (
            SELECT
                l.Tabla_Destino,
                l.ID_Log_Carga,
                l.[Nombre_Archivo_Fuente] AS Nombre_Archivo,
                l.Fecha_Inicio,
                l.Fecha_Fin,
                l.[Estado_Proceso] AS Estado,
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
GO

-- [dbo].[fn_diagramobjects] (SQL_SCALAR_FUNCTION)
CREATE FUNCTION dbo.fn_diagramobjects() 
	RETURNS int
	WITH EXECUTE AS N'dbo'
	AS
	BEGIN
		declare @id_upgraddiagrams		int
		declare @id_sysdiagrams			int
		declare @id_helpdiagrams		int
		declare @id_helpdiagramdefinition	int
		declare @id_creatediagram	int
		declare @id_renamediagram	int
		declare @id_alterdiagram 	int 
		declare @id_dropdiagram		int
		declare @InstalledObjects	int

		select @InstalledObjects = 0

		select 	@id_upgraddiagrams = object_id(N'dbo.sp_upgraddiagrams'),
			@id_sysdiagrams = object_id(N'dbo.sysdiagrams'),
			@id_helpdiagrams = object_id(N'dbo.sp_helpdiagrams'),
			@id_helpdiagramdefinition = object_id(N'dbo.sp_helpdiagramdefinition'),
			@id_creatediagram = object_id(N'dbo.sp_creatediagram'),
			@id_renamediagram = object_id(N'dbo.sp_renamediagram'),
			@id_alterdiagram = object_id(N'dbo.sp_alterdiagram'), 
			@id_dropdiagram = object_id(N'dbo.sp_dropdiagram')

		if @id_upgraddiagrams is not null
			select @InstalledObjects = @InstalledObjects + 1
		if @id_sysdiagrams is not null
			select @InstalledObjects = @InstalledObjects + 2
		if @id_helpdiagrams is not null
			select @InstalledObjects = @InstalledObjects + 4
		if @id_helpdiagramdefinition is not null
			select @InstalledObjects = @InstalledObjects + 8
		if @id_creatediagram is not null
			select @InstalledObjects = @InstalledObjects + 16
		if @id_renamediagram is not null
			select @InstalledObjects = @InstalledObjects + 32
		if @id_alterdiagram  is not null
			select @InstalledObjects = @InstalledObjects + 64
		if @id_dropdiagram is not null
			select @InstalledObjects = @InstalledObjects + 128
		
		return @InstalledObjects 
	END
GO

-- [dbo].[sp_alterdiagram] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_alterdiagram
	(
		@diagramname 	sysname,
		@owner_id	int	= null,
		@version 	int,
		@definition 	varbinary(max)
	)
	WITH EXECUTE AS 'dbo'
	AS
	BEGIN
		set nocount on
	
		declare @theId 			int
		declare @retval 		int
		declare @IsDbo 			int
		
		declare @UIDFound 		int
		declare @DiagId			int
		declare @ShouldChangeUID	int
	
		if(@diagramname is null)
		begin
			RAISERROR ('Invalid ARG', 16, 1)
			return -1
		end
	
		execute as caller;
		select @theId = DATABASE_PRINCIPAL_ID();	 
		select @IsDbo = IS_MEMBER(N'db_owner'); 
		if(@owner_id is null)
			select @owner_id = @theId;
		revert;
	
		select @ShouldChangeUID = 0
		select @DiagId = diagram_id, @UIDFound = principal_id from dbo.sysdiagrams where principal_id = @owner_id and name = @diagramname 
		
		if(@DiagId IS NULL or (@IsDbo = 0 and @theId <> @UIDFound))
		begin
			RAISERROR ('Diagram does not exist or you do not have permission.', 16, 1);
			return -3
		end
	
		if(@IsDbo <> 0)
		begin
			if(@UIDFound is null or USER_NAME(@UIDFound) is null) -- invalid principal_id
			begin
				select @ShouldChangeUID = 1 ;
			end
		end

		-- update dds data			
		update dbo.sysdiagrams set definition = @definition where diagram_id = @DiagId ;

		-- change owner
		if(@ShouldChangeUID = 1)
			update dbo.sysdiagrams set principal_id = @theId where diagram_id = @DiagId ;

		-- update dds version
		if(@version is not null)
			update dbo.sysdiagrams set version = @version where diagram_id = @DiagId ;

		return 0
	END
GO

-- [dbo].[sp_creatediagram] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_creatediagram
	(
		@diagramname 	sysname,
		@owner_id		int	= null, 	
		@version 		int,
		@definition 	varbinary(max)
	)
	WITH EXECUTE AS 'dbo'
	AS
	BEGIN
		set nocount on
	
		declare @theId int
		declare @retval int
		declare @IsDbo	int
		declare @userName sysname
		if(@version is null or @diagramname is null)
		begin
			RAISERROR (N'E_INVALIDARG', 16, 1);
			return -1
		end
	
		execute as caller;
		select @theId = DATABASE_PRINCIPAL_ID(); 
		select @IsDbo = IS_MEMBER(N'db_owner');
		revert; 
		
		if @owner_id is null
		begin
			select @owner_id = @theId;
		end
		else
		begin
			if @theId <> @owner_id
			begin
				if @IsDbo = 0
				begin
					RAISERROR (N'E_INVALIDARG', 16, 1);
					return -1
				end
				select @theId = @owner_id
			end
		end
		-- next 2 line only for test, will be removed after define name unique
		if EXISTS(select diagram_id from dbo.sysdiagrams where principal_id = @theId and name = @diagramname)
		begin
			RAISERROR ('The name is already used.', 16, 1);
			return -2
		end
	
		insert into dbo.sysdiagrams(name, principal_id , version, definition)
				VALUES(@diagramname, @theId, @version, @definition) ;
		
		select @retval = @@IDENTITY 
		return @retval
	END
GO

-- [dbo].[sp_dropdiagram] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_dropdiagram
	(
		@diagramname 	sysname,
		@owner_id	int	= null
	)
	WITH EXECUTE AS 'dbo'
	AS
	BEGIN
		set nocount on
		declare @theId 			int
		declare @IsDbo 			int
		
		declare @UIDFound 		int
		declare @DiagId			int
	
		if(@diagramname is null)
		begin
			RAISERROR ('Invalid value', 16, 1);
			return -1
		end
	
		EXECUTE AS CALLER;
		select @theId = DATABASE_PRINCIPAL_ID();
		select @IsDbo = IS_MEMBER(N'db_owner'); 
		if(@owner_id is null)
			select @owner_id = @theId;
		REVERT; 
		
		select @DiagId = diagram_id, @UIDFound = principal_id from dbo.sysdiagrams where principal_id = @owner_id and name = @diagramname 
		if(@DiagId IS NULL or (@IsDbo = 0 and @UIDFound <> @theId))
		begin
			RAISERROR ('Diagram does not exist or you do not have permission.', 16, 1)
			return -3
		end
	
		delete from dbo.sysdiagrams where diagram_id = @DiagId;
	
		return 0;
	END
GO

-- [dbo].[sp_helpdiagramdefinition] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_helpdiagramdefinition
	(
		@diagramname 	sysname,
		@owner_id	int	= null 		
	)
	WITH EXECUTE AS N'dbo'
	AS
	BEGIN
		set nocount on

		declare @theId 		int
		declare @IsDbo 		int
		declare @DiagId		int
		declare @UIDFound	int
	
		if(@diagramname is null)
		begin
			RAISERROR (N'E_INVALIDARG', 16, 1);
			return -1
		end
	
		execute as caller;
		select @theId = DATABASE_PRINCIPAL_ID();
		select @IsDbo = IS_MEMBER(N'db_owner');
		if(@owner_id is null)
			select @owner_id = @theId;
		revert; 
	
		select @DiagId = diagram_id, @UIDFound = principal_id from dbo.sysdiagrams where principal_id = @owner_id and name = @diagramname;
		if(@DiagId IS NULL or (@IsDbo = 0 and @UIDFound <> @theId ))
		begin
			RAISERROR ('Diagram does not exist or you do not have permission.', 16, 1);
			return -3
		end

		select version, definition FROM dbo.sysdiagrams where diagram_id = @DiagId ; 
		return 0
	END
GO

-- [dbo].[sp_helpdiagrams] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_helpdiagrams
	(
		@diagramname sysname = NULL,
		@owner_id int = NULL
	)
	WITH EXECUTE AS N'dbo'
	AS
	BEGIN
		DECLARE @user sysname
		DECLARE @dboLogin bit
		EXECUTE AS CALLER;
			SET @user = USER_NAME();
			SET @dboLogin = CONVERT(bit,IS_MEMBER('db_owner'));
		REVERT;
		SELECT
			[Database] = DB_NAME(),
			[Name] = name,
			[ID] = diagram_id,
			[Owner] = USER_NAME(principal_id),
			[OwnerID] = principal_id
		FROM
			sysdiagrams
		WHERE
			(@dboLogin = 1 OR USER_NAME(principal_id) = @user) AND
			(@diagramname IS NULL OR name = @diagramname) AND
			(@owner_id IS NULL OR principal_id = @owner_id)
		ORDER BY
			4, 5, 1
	END
GO

-- [dbo].[sp_renamediagram] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_renamediagram
	(
		@diagramname 		sysname,
		@owner_id		int	= null,
		@new_diagramname	sysname
	
	)
	WITH EXECUTE AS 'dbo'
	AS
	BEGIN
		set nocount on
		declare @theId 			int
		declare @IsDbo 			int
		
		declare @UIDFound 		int
		declare @DiagId			int
		declare @DiagIdTarg		int
		declare @u_name			sysname
		if((@diagramname is null) or (@new_diagramname is null))
		begin
			RAISERROR ('Invalid value', 16, 1);
			return -1
		end
	
		EXECUTE AS CALLER;
		select @theId = DATABASE_PRINCIPAL_ID();
		select @IsDbo = IS_MEMBER(N'db_owner'); 
		if(@owner_id is null)
			select @owner_id = @theId;
		REVERT;
	
		select @u_name = USER_NAME(@owner_id)
	
		select @DiagId = diagram_id, @UIDFound = principal_id from dbo.sysdiagrams where principal_id = @owner_id and name = @diagramname 
		if(@DiagId IS NULL or (@IsDbo = 0 and @UIDFound <> @theId))
		begin
			RAISERROR ('Diagram does not exist or you do not have permission.', 16, 1)
			return -3
		end
	
		-- if((@u_name is not null) and (@new_diagramname = @diagramname))	-- nothing will change
		--	return 0;
	
		if(@u_name is null)
			select @DiagIdTarg = diagram_id from dbo.sysdiagrams where principal_id = @theId and name = @new_diagramname
		else
			select @DiagIdTarg = diagram_id from dbo.sysdiagrams where principal_id = @owner_id and name = @new_diagramname
	
		if((@DiagIdTarg is not null) and  @DiagId <> @DiagIdTarg)
		begin
			RAISERROR ('The name is already used.', 16, 1);
			return -2
		end		
	
		if(@u_name is null)
			update dbo.sysdiagrams set [name] = @new_diagramname, principal_id = @theId where diagram_id = @DiagId
		else
			update dbo.sysdiagrams set [name] = @new_diagramname where diagram_id = @DiagId
		return 0
	END
GO

-- [dbo].[sp_upgraddiagrams] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE dbo.sp_upgraddiagrams
	AS
	BEGIN
		IF OBJECT_ID(N'dbo.sysdiagrams') IS NOT NULL
			return 0;
	
		CREATE TABLE dbo.sysdiagrams
		(
			name sysname NOT NULL,
			principal_id int NOT NULL,	-- we may change it to varbinary(85)
			diagram_id int PRIMARY KEY IDENTITY,
			version int,
	
			definition varbinary(max)
			CONSTRAINT UK_principal_name UNIQUE
			(
				principal_id,
				name
			)
		);


		/* Add this if we need to have some form of extended properties for diagrams */
		/*
		IF OBJECT_ID(N'dbo.sysdiagram_properties') IS NULL
		BEGIN
			CREATE TABLE dbo.sysdiagram_properties
			(
				diagram_id int,
				name sysname,
				value varbinary(max) NOT NULL
			)
		END
		*/

		IF OBJECT_ID(N'dbo.dtproperties') IS NOT NULL
		begin
			insert into dbo.sysdiagrams
			(
				[name],
				[principal_id],
				[version],
				[definition]
			)
			select	 
				convert(sysname, dgnm.[uvalue]),
				DATABASE_PRINCIPAL_ID(N'dbo'),			-- will change to the sid of sa
				0,							-- zero for old format, dgdef.[version],
				dgdef.[lvalue]
			from dbo.[dtproperties] dgnm
				inner join dbo.[dtproperties] dggd on dggd.[property] = 'DtgSchemaGUID' and dggd.[objectid] = dgnm.[objectid]	
				inner join dbo.[dtproperties] dgdef on dgdef.[property] = 'DtgSchemaDATA' and dgdef.[objectid] = dgnm.[objectid]
				
			where dgnm.[property] = 'DtgSchemaNAME' and dggd.[uvalue] like N'_EA3E6268-D998-11CE-9454-00AA00A3F36E_' 
			return 2;
		end
		return 1;
	END
GO

-- [MDM].[usp_Backfill_FK_Fact_Tasa_Crecimiento] (SQL_STORED_PROCEDURE)
-- -----------------------------------------------------------------------------
-- 4. SP de backfill: rellena ID_Campana / ID_Condicion en la fact desde el bridge
-- -----------------------------------------------------------------------------
CREATE   PROCEDURE MDM.usp_Backfill_FK_Fact_Tasa_Crecimiento
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE f
       SET f.ID_Campana   = b.ID_Campana,
           f.ID_Condicion = b.ID_Condicion
      FROM Silver.Fact_Tasa_Crecimiento_Brotes f
      JOIN Silver.Bridge_Geografia_Campana_Condicion b
        ON  b.ID_Geografia    = f.ID_Geografia
        AND b.Es_Activa       = 1
        AND f.Fecha_Evento BETWEEN b.Vigencia_Inicio AND ISNULL(b.Vigencia_Fin, '9999-12-31')
     WHERE f.Estado_DQ = 'OK'
       AND (f.ID_Campana IS NULL OR f.ID_Condicion IS NULL);

    SELECT Filas_Backfill = @@ROWCOUNT;
END;
GO

-- [MDM].[usp_Popular_Bridge_Geo_Campana_Condicion] (SQL_STORED_PROCEDURE)
-- -----------------------------------------------------------------------------
-- 2. SP populador (idempotente)
-- -----------------------------------------------------------------------------
CREATE   PROCEDURE MDM.usp_Popular_Bridge_Geo_Campana_Condicion
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ins INT = 0, @upd INT = 0, @cuar INT = 0;

    IF OBJECT_ID('tempdb..#Acciones') IS NOT NULL DROP TABLE #Acciones;
    CREATE TABLE #Acciones (accion NVARCHAR(10));

    IF OBJECT_ID('tempdb..#Resueltas') IS NOT NULL DROP TABLE #Resueltas;

    -- Combinaciones distintas observadas en el fact (Geografia ya resuelta).
    -- Campana y Condicion vienen como texto; se resuelven contra sus Dim.
    ;WITH Combinaciones AS (
        SELECT
            f.ID_Geografia,
            LTRIM(RTRIM(UPPER(f.Campana)))   AS Campana_Raw,
            LTRIM(RTRIM(UPPER(f.Condicion))) AS Condicion_Raw,
            MIN(f.Fecha_Evento) AS Vigencia_Inicio,
            MAX(f.Fecha_Evento) AS Vigencia_Fin
        FROM Silver.Fact_Tasa_Crecimiento_Brotes f
        WHERE f.Estado_DQ = 'OK'
          AND f.ID_Geografia IS NOT NULL
        GROUP BY
            f.ID_Geografia,
            LTRIM(RTRIM(UPPER(f.Campana))),
            LTRIM(RTRIM(UPPER(f.Condicion)))
    )
    SELECT
        c.ID_Geografia,
        c.Campana_Raw,
        c.Condicion_Raw,
        c.Vigencia_Inicio,
        c.Vigencia_Fin,
        -- Campana: match por Nombre_Campana exacto, o por anio (4 digitos) -> Anio_Cosecha.
        COALESCE(
            (SELECT TOP 1 dc.ID_Campana FROM Silver.Dim_Campana dc
              WHERE UPPER(dc.Nombre_Campana) = c.Campana_Raw),
            (SELECT TOP 1 dc.ID_Campana FROM Silver.Dim_Campana dc
              WHERE TRY_CAST(
                      SUBSTRING(c.Campana_Raw, PATINDEX('%[0-9][0-9][0-9][0-9]%', c.Campana_Raw), 4)
                      AS INT) = dc.Anio_Cosecha)
        ) AS ID_Campana,
        -- Condicion: split por '/' -> (Sustrato, Certificacion) -> Dim.
        (SELECT TOP 1 dcc.ID_Condicion
           FROM Silver.Dim_Condicion_Cultivo dcc
          WHERE UPPER(dcc.Sustrato)      = LEFT(c.Condicion_Raw,
                                                NULLIF(CHARINDEX('/', c.Condicion_Raw) - 1, -1))
            AND UPPER(dcc.Certificacion) = SUBSTRING(c.Condicion_Raw,
                                                     CHARINDEX('/', c.Condicion_Raw) + 1, 200)
        ) AS ID_Condicion
    INTO #Resueltas
    FROM Combinaciones c;

    -- Cuarentena: filas con cualquier FK no resuelta.
    INSERT INTO MDM.Cuarentena (Tabla_Origen, Campo_Origen, Valor_Recibido, Motivo, Tipo_Regla)
    SELECT
        'Silver.Fact_Tasa_Crecimiento_Brotes',
        'Bridge_GCC',
        LEFT(CONCAT('Geo=', r.ID_Geografia, ' | Campana=', r.Campana_Raw, ' | Condicion=', r.Condicion_Raw), 500),
        LEFT(CONCAT(
            CASE WHEN r.ID_Campana   IS NULL THEN 'CAMPANA_NO_RESUELTA;'   ELSE '' END,
            CASE WHEN r.ID_Condicion IS NULL THEN 'CONDICION_NO_RESUELTA;' ELSE '' END
        ), 200),
        'CATALOGO'
    FROM #Resueltas r
    WHERE r.ID_Campana IS NULL OR r.ID_Condicion IS NULL;

    SET @cuar = @@ROWCOUNT;

    ;WITH Validas AS (
        SELECT
            r.ID_Geografia,
            r.ID_Campana,
            r.ID_Condicion,
            r.Vigencia_Inicio,
            r.Vigencia_Fin,
            HASHBYTES(
                'SHA2_256',
                CONCAT(r.ID_Geografia, '|', r.ID_Campana, '|', r.ID_Condicion, '|',
                       CONVERT(VARCHAR(10), r.Vigencia_Inicio, 23))
            ) AS Hash_Llave
        FROM #Resueltas r
        WHERE r.ID_Campana   IS NOT NULL
          AND r.ID_Condicion IS NOT NULL
    )
    MERGE Silver.Bridge_Geografia_Campana_Condicion AS dst
    USING Validas AS src
       ON dst.Hash_Llave = src.Hash_Llave
    WHEN MATCHED AND (
            ISNULL(dst.Vigencia_Fin, '9999-12-31') <> ISNULL(src.Vigencia_Fin, '9999-12-31')
         OR dst.Es_Activa = 0
        )
        THEN UPDATE SET
            dst.Vigencia_Fin = src.Vigencia_Fin,
            dst.Es_Activa    = 1
    WHEN NOT MATCHED BY TARGET
        THEN INSERT (ID_Geografia, ID_Campana, ID_Condicion, Vigencia_Inicio, Vigencia_Fin, Es_Activa, Hash_Llave)
             VALUES (src.ID_Geografia, src.ID_Campana, src.ID_Condicion, src.Vigencia_Inicio, src.Vigencia_Fin, 1, src.Hash_Llave)
    OUTPUT $action INTO #Acciones(accion);

    SELECT @ins = SUM(CASE WHEN accion = 'INSERT' THEN 1 ELSE 0 END),
           @upd = SUM(CASE WHEN accion = 'UPDATE' THEN 1 ELSE 0 END)
    FROM #Acciones;

    DROP TABLE #Resueltas;
    DROP TABLE #Acciones;

    SELECT
        Filas_Insertadas   = ISNULL(@ins, 0),
        Filas_Actualizadas = ISNULL(@upd, 0),
        Filas_Cuarentena   = @cuar;
END;
GO

-- [Silver].[sp_Resolver_Geografia_Cama] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE Silver.sp_Resolver_Geografia_Cama
    @Modulo_Raw NVARCHAR(100) = NULL,
    @Turno_Raw NVARCHAR(100) = NULL,
    @Valvula_Raw NVARCHAR(100) = NULL,
    @Cama_Raw NVARCHAR(100) = NULL,
    @Cama_Min_Permitida INT = 1,
    @Cama_Max_Permitida INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE
        @Modulo_Token NVARCHAR(50),
        @Turno_Token NVARCHAR(50),
        @Valvula_Token NVARCHAR(50),
        @Cama_Token NVARCHAR(50),
        @Modulo_Int INT = NULL,
        @SubModulo_Int INT = NULL,
        @Turno_Int INT = NULL,
        @Cama_Int INT = NULL,
        @Es_Modulo_Especial BIT = 0,
        @Es_Test_Block_Regla BIT = 0,
        @Coincidencias_Geo INT = 0,
        @ID_Geografia INT = NULL,
        @ID_Cama_Catalogo INT = NULL,
        @Estado_Resolucion NVARCHAR(50),
        @Detalle NVARCHAR(300),
        @Tipo_Conduccion_Regla NVARCHAR(50) = NULL,
        @Prioridad_Regla INT = NULL;

    SELECT
        @Modulo_Token = NULLIF(LTRIM(RTRIM(@Modulo_Raw)), ''),
        @Turno_Token = NULLIF(LTRIM(RTRIM(@Turno_Raw)), ''),
        @Valvula_Token = NULLIF(LTRIM(RTRIM(@Valvula_Raw)), ''),
        @Cama_Token = NULLIF(LTRIM(RTRIM(@Cama_Raw)), '');

    IF @Modulo_Token IS NOT NULL AND @Modulo_Token NOT LIKE '%[^0-9]%'
        SET @Modulo_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Modulo_Token));

    IF @Turno_Token IS NOT NULL AND @Turno_Token NOT LIKE '%[^0-9]%'
        SET @Turno_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Turno_Token));

    IF @Valvula_Token IS NOT NULL AND @Valvula_Token NOT LIKE '%[^0-9]%'
        SET @Valvula_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Valvula_Token));

    IF @Cama_Token IS NOT NULL AND @Cama_Token NOT LIKE '%[^0-9]%'
        SET @Cama_Token = CONVERT(NVARCHAR(50), CONVERT(INT, @Cama_Token));

    IF @Turno_Token IS NOT NULL AND @Turno_Token NOT LIKE '%[^0-9]%'
        SET @Turno_Int = CONVERT(INT, @Turno_Token);

    IF @Cama_Token IS NOT NULL AND @Cama_Token NOT LIKE '%[^0-9]%'
        SET @Cama_Int = CONVERT(INT, @Cama_Token);

    /* 1) Regla exacta vigente: 9.1, 9.2, 11.1, 11.2, etc. */
    IF OBJECT_ID('MDM.Regla_Modulo_Raw', 'U') IS NOT NULL
       AND @Modulo_Token IS NOT NULL
    BEGIN
        SELECT TOP (1)
            @Modulo_Int = r.Modulo_Int,
            @SubModulo_Int = r.SubModulo_Int,
            @Es_Test_Block_Regla = ISNULL(r.Es_Test_Block, 0),
            @Tipo_Conduccion_Regla = r.Tipo_Conduccion
        FROM MDM.Regla_Modulo_Raw r
        WHERE r.Es_Activa = 1
          AND UPPER(LTRIM(RTRIM(r.Modulo_Raw))) = UPPER(@Modulo_Token);
    END;

    /* 2) Si no hubo regla exacta, intentar regla por rango de turno */
    IF @Modulo_Int IS NULL
       AND OBJECT_ID('MDM.Regla_Modulo_Turno_SubModulo', 'U') IS NOT NULL
       AND @Modulo_Token IS NOT NULL
       AND @Turno_Int IS NOT NULL
    BEGIN
        SELECT TOP (1)
            @Modulo_Int = r.Modulo_Int,
            @SubModulo_Int = r.SubModulo_Int,
            @Es_Test_Block_Regla = ISNULL(r.Es_Test_Block, 0),
            @Tipo_Conduccion_Regla = r.Tipo_Conduccion,
            @Prioridad_Regla = r.Prioridad
        FROM MDM.Regla_Modulo_Turno_SubModulo r
        WHERE r.Es_Activa = 1
          AND UPPER(LTRIM(RTRIM(r.Modulo_Raw_Base))) = UPPER(@Modulo_Token)
          AND @Turno_Int BETWEEN r.Turno_Desde AND r.Turno_Hasta
        ORDER BY r.Prioridad ASC, r.Turno_Desde ASC, r.ID_Regla_Modulo_Turno ASC;
    END;

    /* 3) Si sigue sin regla, usar modulo puro solo si es entero limpio */
    IF @Modulo_Int IS NULL
       AND @Modulo_Token IS NOT NULL
       AND @Modulo_Token NOT LIKE '%[^0-9]%'
    BEGIN
        SET @Modulo_Int = CONVERT(INT, @Modulo_Token);
    END;

    IF @Es_Test_Block_Regla = 1
    BEGIN
        IF @Turno_Int IS NULL OR @Valvula_Token IS NULL
        BEGIN
            SET @Estado_Resolucion = 'CLAVE_GEOGRAFICA_INCOMPLETA';
            SET @Detalle = 'Test block sin turno o valvula.';
        END
        ELSE
        BEGIN
            ;WITH GeoTB AS (
                SELECT g.ID_Geografia
                FROM Silver.Dim_Geografia g
                WHERE ISNULL(g.Es_Vigente, 1) = 1
                  AND ISNULL(g.Es_Test_Block, 0) = 1
                  AND g.Turno = @Turno_Int
                  AND (
                        CASE
                            WHEN g.Valvula IS NULL THEN NULL
                            WHEN LTRIM(RTRIM(g.Valvula)) = '' THEN NULL
                            WHEN LTRIM(RTRIM(g.Valvula)) NOT LIKE '%[^0-9]%'
                                THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(g.Valvula))))
                            ELSE LTRIM(RTRIM(g.Valvula))
                        END
                      ) = @Valvula_Token
            )
            SELECT
                @Coincidencias_Geo = COUNT(*),
                @ID_Geografia = MIN(ID_Geografia)
            FROM GeoTB;

            IF @Coincidencias_Geo = 1
            BEGIN
                SET @Estado_Resolucion = 'RESUELTA_TEST_BLOCK';
                SET @Detalle = 'Test block resuelto por Turno/Valvula.';
            END
            ELSE IF @Coincidencias_Geo = 0
            BEGIN
                SET @Estado_Resolucion = 'TEST_BLOCK_NO_MAPEADO';
                SET @Detalle = 'No existe geografia test block para Turno/Valvula.';
                SET @ID_Geografia = NULL;
            END
            ELSE
            BEGIN
                SET @Estado_Resolucion = 'TEST_BLOCK_AMBIGUO';
                SET @Detalle = 'Mas de una geografia test block para Turno/Valvula.';
                SET @ID_Geografia = NULL;
            END
        END;

        SELECT
            @Modulo_Token AS Modulo_Token,
            @Turno_Token AS Turno_Token,
            @Valvula_Token AS Valvula_Token,
            @Cama_Token AS Cama_Token,
            @Modulo_Int AS Modulo_Int,
            @SubModulo_Int AS SubModulo_Int,
            @Turno_Int AS Turno_Int,
            @Cama_Int AS Cama_Int,
            @ID_Geografia AS ID_Geografia,
            @ID_Cama_Catalogo AS ID_Cama_Catalogo,
            @Estado_Resolucion AS Estado_Resolucion,
            @Detalle AS Detalle;

        RETURN;
    END;

    IF @Modulo_Int IS NULL
        SET @Es_Modulo_Especial = 1;

    IF @Es_Modulo_Especial = 1
    BEGIN
        SET @Estado_Resolucion = 'CASO_ESPECIAL_MODULO';
        SET @Detalle = 'Modulo especial (sin regla operativa).';
    END
    ELSE IF @Turno_Int IS NULL OR @Valvula_Token IS NULL
    BEGIN
        SET @Estado_Resolucion = 'CLAVE_GEOGRAFICA_INCOMPLETA';
        SET @Detalle = 'Falta turno o valvula.';
    END
    ELSE
    BEGIN
        ;WITH Geo AS (
            SELECT
                g.ID_Geografia
            FROM Silver.Dim_Geografia g
            WHERE ISNULL(g.Es_Vigente, 1) = 1
              AND ISNULL(g.Es_Test_Block, 0) = 0
              AND g.Modulo = @Modulo_Int
              AND ISNULL(g.SubModulo, -1) = ISNULL(@SubModulo_Int, -1)
              AND g.Turno = @Turno_Int
              AND (
                    CASE
                        WHEN g.Valvula IS NULL THEN NULL
                        WHEN LTRIM(RTRIM(g.Valvula)) = '' THEN NULL
                        WHEN LTRIM(RTRIM(g.Valvula)) NOT LIKE '%[^0-9]%'
                            THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(g.Valvula))))
                        ELSE LTRIM(RTRIM(g.Valvula))
                    END
                  ) = @Valvula_Token
        )
        SELECT
            @Coincidencias_Geo = COUNT(*),
            @ID_Geografia = MIN(ID_Geografia)
        FROM Geo;

        IF @Coincidencias_Geo = 0
        BEGIN
            SET @Estado_Resolucion = 'GEOGRAFIA_NO_ENCONTRADA';
            SET @Detalle = 'No existe geografia vigente para modulo/submodulo/turno/valvula.';
        END
        ELSE IF @Coincidencias_Geo > 1
        BEGIN
            SET @Estado_Resolucion = 'GEOGRAFIA_AMBIGUA';
            SET @Detalle = 'Existe mas de una geografia vigente para modulo/submodulo/turno/valvula.';
            SET @ID_Geografia = NULL;
        END
        ELSE
        BEGIN
            IF @Cama_Token IS NULL OR @Cama_Token = '0'
            BEGIN
                SET @Estado_Resolucion = 'RESUELTA_BASE_SIN_CAMA';
                SET @Detalle = 'Geografia resuelta sin cama especifica.';
            END
            ELSE IF @Cama_Int IS NULL OR @Cama_Int < @Cama_Min_Permitida OR @Cama_Int > @Cama_Max_Permitida
            BEGIN
                SET @Estado_Resolucion = 'CAMA_NO_VALIDA';
                SET @Detalle = 'Cama fuera de rango permitido.';
            END
            ELSE
            BEGIN
                SELECT
                    @ID_Cama_Catalogo = c.ID_Cama_Catalogo
                FROM Silver.Dim_Cama_Catalogo c
                WHERE c.Es_Activa = 1
                  AND c.Cama_Normalizada = CONVERT(NVARCHAR(50), @Cama_Int);

                IF @ID_Cama_Catalogo IS NULL
                BEGIN
                    SET @Estado_Resolucion = 'CAMA_NO_CATALOGO';
                    SET @Detalle = 'Cama valida, pero no existe en catalogo.';
                END
                ELSE IF EXISTS (
                    SELECT 1
                    FROM Silver.Bridge_Geografia_Cama b
                    WHERE b.ID_Geografia = @ID_Geografia
                      AND b.ID_Cama_Catalogo = @ID_Cama_Catalogo
                      AND b.Es_Vigente = 1
                      AND b.Fecha_Fin_Vigencia IS NULL
                )
                BEGIN
                    SET @Estado_Resolucion = 'RESUELTA_BASE_Y_CAMA';
                    SET @Detalle = 'Geografia y cama resueltas.';
                END
                ELSE
                BEGIN
                    SET @Estado_Resolucion = 'CAMA_NO_RELACION';
                    SET @Detalle = 'Cama existe en catalogo, pero no esta relacionada a la geografia.';
                END
            END
        END
    END

    SELECT
        @Modulo_Token AS Modulo_Token,
        @Turno_Token AS Turno_Token,
        @Valvula_Token AS Valvula_Token,
        @Cama_Token AS Cama_Token,
        @Modulo_Int AS Modulo_Int,
        @SubModulo_Int AS SubModulo_Int,
        @Turno_Int AS Turno_Int,
        @Cama_Int AS Cama_Int,
        @ID_Geografia AS ID_Geografia,
        @ID_Cama_Catalogo AS ID_Cama_Catalogo,
        @Estado_Resolucion AS Estado_Resolucion,
        @Detalle AS Detalle;
END;
GO

-- [Silver].[sp_Sincronizar_Periodos_Campana] (SQL_STORED_PROCEDURE)
CREATE   PROCEDURE Silver.sp_Sincronizar_Periodos_Campana
AS
BEGIN
    SET NOCOUNT ON;
    SET DATEFIRST 1; -- Asegurar Lunes como primer dia de la semana (ISO)

    -- 1. Crear Campañas faltantes en Dim_Campana
    INSERT INTO Silver.Dim_Campana (Anio_Cosecha, Nombre_Campana, Estado, Es_Activa, Fecha_Creacion)
    SELECT DISTINCT 
        Calculo.Anio_Cosecha,
        'Campaña ' + CAST(Calculo.Anio_Cosecha AS VARCHAR),
        'ACTIVO', 
        1, 
        GETDATE()
    FROM (
        SELECT 
            CASE 
                WHEN DATEPART(isowk, Fecha_Evento) <= 20 THEN YEAR(Fecha_Evento)
                ELSE YEAR(Fecha_Evento) + 1
            END as Anio_Cosecha
        FROM Silver.Fact_Ciclo_Poda
        WHERE Estado_DQ = 'OK'
    ) Calculo
    WHERE NOT EXISTS (
        SELECT 1 FROM Silver.Dim_Campana c WHERE c.Anio_Cosecha = Calculo.Anio_Cosecha
    );

    -- 2. Procesar Podas para generar el Bridge
    -- Usamos una tabla temporal para agrupar y calcular intervalos
    IF OBJECT_ID('tempdb..#TmpPodas') IS NOT NULL DROP TABLE #TmpPodas;
    
    SELECT 
        g.ID_Modulo_Catalogo,
        p.ID_Variedad,
        CASE 
            WHEN DATEPART(isowk, p.Fecha_Evento) <= 20 THEN YEAR(p.Fecha_Evento)
            ELSE YEAR(p.Fecha_Evento) + 1
        END as Anio_Cosecha,
        MIN(p.Fecha_Evento) as Fecha_Inicio,
        MIN(DATEPART(isowk, p.Fecha_Evento)) as Semana_Poda_ISO,
        MIN(YEAR(p.Fecha_Evento)) as Anio_Poda_ISO -- Simplificado, podria ser ISODATE si fuera critico
    INTO #TmpPodas
    FROM Silver.Fact_Ciclo_Poda p
    INNER JOIN Silver.Dim_Geografia g ON p.ID_Geografia = g.ID_Geografia
    WHERE p.Estado_DQ = 'OK'
    GROUP BY g.ID_Modulo_Catalogo, p.ID_Variedad, 
             CASE WHEN DATEPART(isowk, p.Fecha_Evento) <= 20 THEN YEAR(p.Fecha_Evento) ELSE YEAR(p.Fecha_Evento) + 1 END;

    -- 3. Calcular Fecha_Fin (Dia antes de la siguiente poda del mismo Modulo+Variedad)
    IF OBJECT_ID('tempdb..#TmpBridge') IS NOT NULL DROP TABLE #TmpBridge;
    
    SELECT 
        t.ID_Modulo_Catalogo,
        t.ID_Variedad,
        c.ID_Campana,
        t.Fecha_Inicio,
        ISNULL(
            DATEADD(DAY, -1, LEAD(t.Fecha_Inicio) OVER (PARTITION BY t.ID_Modulo_Catalogo, t.ID_Variedad ORDER BY t.Fecha_Inicio)),
            '2099-12-31'
        ) as Fecha_Fin,
        t.Semana_Poda_ISO,
        t.Anio_Poda_ISO
    INTO #TmpBridge
    FROM #TmpPodas t
    INNER JOIN Silver.Dim_Campana c ON t.Anio_Cosecha = c.Anio_Cosecha;

    -- 4. Actualizar Bridge_Modulo_Campana (Truncate & Reload es seguro aqui porque se deriva de Fact_Ciclo_Poda)
    TRUNCATE TABLE Silver.Bridge_Modulo_Campana;
    
    INSERT INTO Silver.Bridge_Modulo_Campana 
    (ID_Modulo_Catalogo, ID_Variedad, ID_Campana, Tipo_Campana, Fecha_Inicio, Fecha_Fin, Es_Activa, Fecha_Creacion, Semana_Poda_ISO, Anio_Poda_ISO)
    SELECT 
        ID_Modulo_Catalogo, ID_Variedad, ID_Campana, 'COMERCIAL', Fecha_Inicio, Fecha_Fin, 1, GETDATE(), Semana_Poda_ISO, Anio_Poda_ISO
    FROM #TmpBridge;

    PRINT 'Bridge de Campañas sincronizado exitosamente.';
END;
GO

-- [Silver].[sp_Upsert_Cama_Desde_Bronce] (SQL_STORED_PROCEDURE)
CREATE   PROCEDURE Silver.sp_Upsert_Cama_Desde_Bronce
    @Modo_Aplicar       BIT = 1,
    @Cama_Min_Permitida INT = 1,
    @Cama_Max_Permitida INT = 100
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('Silver.Dim_Cama_Catalogo', 'U') IS NULL
    BEGIN
        RAISERROR('No existe Silver.Dim_Cama_Catalogo.', 16, 1);
        RETURN;
    END;
    IF OBJECT_ID('Silver.Bridge_Geografia_Cama', 'U') IS NULL
    BEGIN
        RAISERROR('No existe Silver.Bridge_Geografia_Cama.', 16, 1);
        RETURN;
    END;
    IF OBJECT_ID('Bronce.Evaluacion_Pesos', 'U') IS NULL
       OR OBJECT_ID('Bronce.Evaluacion_Vegetativa', 'U') IS NULL
    BEGIN
        RAISERROR('No existen tablas Bronce requeridas.', 16, 1);
        RETURN;
    END;
    IF OBJECT_ID('tempdb..#BronceRaw') IS NOT NULL DROP TABLE #BronceRaw;
    IF OBJECT_ID('tempdb..#Eval')      IS NOT NULL DROP TABLE #Eval;
    IF OBJECT_ID('tempdb..#Aptos')     IS NOT NULL DROP TABLE #Aptos;
    -- ── 1. Leer último lote de cada fuente Bronce ─────────────────────────────
    CREATE TABLE #BronceRaw (
        Tabla_Origen NVARCHAR(50)  NOT NULL,
        Modulo_Raw   NVARCHAR(100) NULL,
        Turno_Raw    NVARCHAR(100) NULL,
        Valvula_Raw  NVARCHAR(100) NULL,
        Cama_Raw     NVARCHAR(100) NULL
    );
    ;WITH LotePesos AS (
        SELECT TOP (1) Fecha_Sistema, Nombre_Archivo
        FROM Bronce.Evaluacion_Pesos
        ORDER BY Fecha_Sistema DESC, ID_Evaluacion_Pesos DESC
    )
    INSERT INTO #BronceRaw (Tabla_Origen, Modulo_Raw, Turno_Raw, Valvula_Raw, Cama_Raw)
    SELECT 'Bronce.Evaluacion_Pesos', p.Modulo_Raw, p.Turno_Raw, p.Valvula_Raw, p.Cama_Raw
    FROM Bronce.Evaluacion_Pesos p
    INNER JOIN LotePesos l ON p.Fecha_Sistema = l.Fecha_Sistema
                          AND p.Nombre_Archivo = l.Nombre_Archivo;
    ;WITH LoteVeg AS (
        SELECT TOP (1) Fecha_Sistema, Nombre_Archivo
        FROM Bronce.Evaluacion_Vegetativa
        ORDER BY Fecha_Sistema DESC, ID_Evaluacion_Veg DESC -- <--- FIX AQUI: ID_Evaluacion_Veg
    )
    INSERT INTO #BronceRaw (Tabla_Origen, Modulo_Raw, Turno_Raw, Valvula_Raw, Cama_Raw)
    SELECT 'Bronce.Evaluacion_Vegetativa', v.Modulo_Raw, v.Turno_Raw, v.Valvula_Raw, v.Cama_Raw
    FROM Bronce.Evaluacion_Vegetativa v
    INNER JOIN LoteVeg l ON v.Fecha_Sistema = l.Fecha_Sistema
                        AND v.Nombre_Archivo = l.Nombre_Archivo;
    -- ── 2. Resolver geografía por fila ────────────────────────────────────────
    CREATE TABLE #Eval (
        Estado_Resolucion NVARCHAR(50) NOT NULL,
        ID_Geografia      INT          NULL,
        Cama_Int          INT          NULL
    );
    INSERT INTO #Eval (Estado_Resolucion, ID_Geografia, Cama_Int)
    SELECT
        CASE
            WHEN x.Es_Modulo_Especial = 1                                                        THEN 'CASO_ESPECIAL_MODULO'
            WHEN x.Modulo_Int IS NULL OR x.Turno_Int IS NULL OR x.Valvula_Token IS NULL          THEN 'CLAVE_GEOGRAFICA_INCOMPLETA'
            WHEN x.Cama_Int IS NULL
              OR x.Cama_Int < @Cama_Min_Permitida
              OR x.Cama_Int > @Cama_Max_Permitida                                                THEN 'CAMA_NO_VALIDA'
            WHEN x.Coincidencias_Geo = 0                                                         THEN 'GEOGRAFIA_NO_ENCONTRADA'
            WHEN x.Coincidencias_Geo > 1                                                         THEN 'GEOGRAFIA_AMBIGUA'
            ELSE 'APTO_PARA_INSERT'
        END AS Estado_Resolucion,
        CASE WHEN x.Coincidencias_Geo = 1 THEN x.ID_Geografia_Unica ELSE NULL END AS ID_Geografia,
        x.Cama_Int
    FROM (
        SELECT
            t.Modulo_Int,
            t.SubModulo_Int,
            t.Turno_Int,
            t.Valvula_Token,
            t.Cama_Int,
            t.Es_Modulo_Especial,
            g.Coincidencias_Geo,
            g.ID_Geografia_Unica
        FROM #BronceRaw r
        CROSS APPLY (
            SELECT
                NULLIF(LTRIM(RTRIM(r.Modulo_Raw)),  '') AS Modulo_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Turno_Raw)),   '') AS Turno_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Valvula_Raw)), '') AS Valvula_Token_Raw,
                NULLIF(LTRIM(RTRIM(r.Cama_Raw)),    '') AS Cama_Token_Raw
        ) raw
        OUTER APPLY (
            SELECT TOP (1)
                rr.Modulo_Int,
                rr.SubModulo_Int,
                ISNULL(rr.Es_Test_Block, 0) AS Es_Test_Block_Regla
            FROM MDM.Regla_Modulo_Raw rr
            WHERE rr.Es_Activa = 1
              AND raw.Modulo_Token_Raw IS NOT NULL
              AND UPPER(LTRIM(RTRIM(rr.Modulo_Raw))) = UPPER(raw.Modulo_Token_Raw)
        ) regla
        CROSS APPLY (
            SELECT
                CASE WHEN raw.Turno_Token_Raw IS NULL   THEN NULL
                     WHEN raw.Turno_Token_Raw   NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Turno_Token_Raw)
                     ELSE NULL END AS Turno_Int,
                CASE WHEN raw.Valvula_Token_Raw IS NULL THEN NULL
                     WHEN raw.Valvula_Token_Raw NOT LIKE '%[^0-9]%' THEN CONVERT(NVARCHAR(50), CONVERT(INT, raw.Valvula_Token_Raw))
                     ELSE raw.Valvula_Token_Raw END AS Valvula_Token,
                CASE WHEN raw.Cama_Token_Raw IS NULL    THEN NULL
                     WHEN raw.Cama_Token_Raw    NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Cama_Token_Raw)
                     ELSE NULL END AS Cama_Int,
                CASE WHEN raw.Modulo_Token_Raw IS NOT NULL
                      AND raw.Modulo_Token_Raw NOT LIKE '%[^0-9]%' THEN CONVERT(INT, raw.Modulo_Token_Raw)
                     ELSE NULL END AS Modulo_Int_Raw
        ) base
        CROSS APPLY (
            SELECT
                COALESCE(regla.Modulo_Int, base.Modulo_Int_Raw)   AS Modulo_Int,
                regla.SubModulo_Int                                AS SubModulo_Int,
                CASE
                    WHEN ISNULL(regla.Es_Test_Block_Regla, 0) = 1           THEN 1
                    WHEN COALESCE(regla.Modulo_Int, base.Modulo_Int_Raw) IS NULL THEN 1
                    ELSE 0
                END AS Es_Modulo_Especial,
                base.Turno_Int,
                base.Valvula_Token,
                base.Cama_Int
        ) t
        OUTER APPLY (
            SELECT
                COUNT(*)          AS Coincidencias_Geo,
                MIN(gv.ID_Geografia) AS ID_Geografia_Unica
            FROM Silver.Dim_Geografia      gv
            JOIN Silver.Dim_Modulo_Catalogo  mc ON mc.ID_Modulo_Catalogo  = gv.ID_Modulo_Catalogo
            JOIN Silver.Dim_Turno_Catalogo   tc ON tc.ID_Turno_Catalogo   = gv.ID_Turno_Catalogo
            JOIN Silver.Dim_Valvula_Catalogo vc ON vc.ID_Valvula_Catalogo = gv.ID_Valvula_Catalogo
            WHERE ISNULL(gv.Es_Vigente,    1) = 1
              AND ISNULL(gv.Es_Test_Block,  0) = 0
              AND mc.Modulo                      = t.Modulo_Int
              AND ISNULL(mc.SubModulo, -1)       = ISNULL(t.SubModulo_Int, -1)
              AND tc.Turno                       = t.Turno_Int
              AND (
                    CASE
                        WHEN LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula))) = ''   THEN NULL
                        WHEN LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula))) NOT LIKE '%[^0-9]%'
                            THEN CONVERT(NVARCHAR(50), CONVERT(INT, LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula)))))
                        ELSE LTRIM(RTRIM(CONVERT(NVARCHAR(50), vc.Valvula)))
                    END
                  ) = t.Valvula_Token
        ) g
    ) x;
    -- ── 3. Filtrar aptos ──────────────────────────────────────────────────────
    CREATE TABLE #Aptos (
        ID_Geografia    INT          NOT NULL,
        Cama_Normalizada NVARCHAR(50) NOT NULL,
        CONSTRAINT PK_Aptos PRIMARY KEY (ID_Geografia, Cama_Normalizada)
    );
    INSERT INTO #Aptos (ID_Geografia, Cama_Normalizada)
    SELECT DISTINCT
        e.ID_Geografia,
        CONVERT(NVARCHAR(50), e.Cama_Int)
    FROM #Eval e
    WHERE e.Estado_Resolucion = 'APTO_PARA_INSERT'
      AND e.ID_Geografia IS NOT NULL
      AND e.Cama_Int BETWEEN @Cama_Min_Permitida AND @Cama_Max_Permitida;
    -- ── 4. Aplicar (solo si @Modo_Aplicar = 1) ────────────────────────────────
    DECLARE
        @Insert_Catalogo_Real INT = 0,
        @Insert_Bridge_Real   INT = 0;
    IF @Modo_Aplicar = 1
    BEGIN
        BEGIN TRANSACTION;
        INSERT INTO Silver.Dim_Cama_Catalogo (Cama_Normalizada)
        SELECT DISTINCT a.Cama_Normalizada
        FROM #Aptos a
        WHERE NOT EXISTS (
            SELECT 1 FROM Silver.Dim_Cama_Catalogo c
            WHERE c.Cama_Normalizada = a.Cama_Normalizada
        );
        SET @Insert_Catalogo_Real = @@ROWCOUNT;
        INSERT INTO Silver.Bridge_Geografia_Cama (
            ID_Geografia, ID_Cama_Catalogo,
            Fecha_Inicio_Vigencia, Fecha_Fin_Vigencia,
            Es_Vigente, Fuente_Registro, Observacion
        )
        SELECT
            a.ID_Geografia,
            c.ID_Cama_Catalogo,
            CAST(GETDATE() AS DATE),
            NULL,
            1,
            'SP_UPSERT_CAMA_BRONCE',
            'Insercion via Silver.sp_Upsert_Cama_Desde_Bronce'
        FROM #Aptos a
        INNER JOIN Silver.Dim_Cama_Catalogo c ON c.Cama_Normalizada = a.Cama_Normalizada
        WHERE NOT EXISTS (
            SELECT 1 FROM Silver.Bridge_Geografia_Cama b
            WHERE b.ID_Geografia    = a.ID_Geografia
              AND b.ID_Cama_Catalogo = c.ID_Cama_Catalogo
              AND b.Es_Vigente       = 1
              AND b.Fecha_Fin_Vigencia IS NULL
        );
        SET @Insert_Bridge_Real = @@ROWCOUNT;
        COMMIT TRANSACTION;
    END;
    -- ── 5. Resultados ─────────────────────────────────────────────────────────
    SELECT
        @Modo_Aplicar                           AS Modo_Aplicar,
        (SELECT COUNT(*) FROM #BronceRaw)       AS Filas_Bronce_Leidas,
        (SELECT COUNT(*) FROM #Eval)            AS Filas_Evaluadas,
        (SELECT COUNT(*) FROM #Aptos)           AS Combinaciones_Aptas_Distintas,
        @Insert_Catalogo_Real                   AS Insert_Catalogo_Real,
        @Insert_Bridge_Real                     AS Insert_Bridge_Real;
    SELECT Estado_Resolucion, COUNT(*) AS Filas
    FROM #Eval
    GROUP BY Estado_Resolucion
    ORDER BY COUNT(*) DESC;
END;
GO

-- [Silver].[sp_Validar_Calidad_Camas] (SQL_STORED_PROCEDURE)
CREATE PROCEDURE Silver.sp_Validar_Calidad_Camas
    @Cama_Max_Permitida INT = 100,
    @Max_Camas_Por_Geografia INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    ;WITH Catalogo AS (
        SELECT
            TRY_CONVERT(INT, Cama_Normalizada) AS Cama_Int
        FROM Silver.Dim_Cama_Catalogo
        WHERE Es_Activa = 1
    ),
    Metricas AS (
        SELECT
            SUM(CASE WHEN Cama_Int IS NULL OR Cama_Int <= 0 OR Cama_Int > @Cama_Max_Permitida THEN 1 ELSE 0 END) AS Cama_Fuera_Regla
        FROM Catalogo
    ),
    GeoSaturada AS (
        SELECT COUNT(*) AS Geografias_Saturadas
        FROM (
            SELECT
                ID_Geografia,
                COUNT(*) AS Cantidad_Camas
            FROM Silver.Bridge_Geografia_Cama
            WHERE Es_Vigente = 1
              AND Fecha_Fin_Vigencia IS NULL
            GROUP BY ID_Geografia
            HAVING COUNT(*) > @Max_Camas_Por_Geografia
        ) q
    )
    SELECT
        m.Cama_Fuera_Regla,
        gs.Geografias_Saturadas,
        CASE
            WHEN m.Cama_Fuera_Regla = 0 AND gs.Geografias_Saturadas = 0 THEN 'OK_OPERATIVO'
            WHEN m.Cama_Fuera_Regla <= 5 AND gs.Geografias_Saturadas <= 5 THEN 'REVISAR_PUNTUAL'
            ELSE 'RIESGO_CONTAMINACION'
        END AS Estado_Calidad_Cama
    FROM Metricas m
    CROSS JOIN GeoSaturada gs;
END;
GO

-- [Silver].[vFact_areas_plantas] (VIEW)
CREATE   VIEW Silver.vFact_areas_plantas AS
        SELECT 
            f.ID_Censo,
            t.Fecha AS Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            cond.Sustrato AS Condicion_Sustrato,
            cond.Certificacion AS Condicion_Certificacion,
            f.Cantidad_Plantas,
            f.Area_ha,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_areas_plantas f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Tiempo t ON f.ID_Tiempo = t.ID_Tiempo
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Condicion_Cultivo cond ON f.ID_Condicion = cond.ID_Condicion
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Censo_Plantas] (VIEW)
CREATE   VIEW Silver.vFact_Censo_Plantas AS
        SELECT 
            f.ID_Censo,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            f.Plantas_Buenas,
            f.Plantas_Regulares,
            f.Plantas_Malas,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema
        FROM Silver.Fact_Censo_Plantas f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Ciclo_Poda] (VIEW)
CREATE   VIEW Silver.vFact_Ciclo_Poda AS
        SELECT 
            f.ID_Poda,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            f.Punto,
            var.Nombre_Variedad AS Variedad,
            f.Tipo_Evaluacion,
            f.Tallos_Planta,
            f.Longitud_Tallo,
            f.Diametro_Tallo,
            f.Ramilla_Planta,
            f.Tocones_Planta,
            f.Cortes_Defectuosos,
            f.Altura_Poda,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Ciclo_Poda f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Conteo_Fenologico] (VIEW)
CREATE   VIEW Silver.vFact_Conteo_Fenologico AS
        SELECT 
            f.ID_Conteo_Fenologico,
            f.Fecha_Evento,
            f.Fecha_Registro,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            f.Punto,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            est.Nombre_Estado AS Estado_Fenologico,
            f.Cantidad_Organos,
            f.Plantas_Productivas,
            f.Plantas_No_Productivas,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Conteo_Fenologico f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana
        LEFT JOIN Silver.Dim_Estado_Fenologico est ON f.ID_Estado_Fenologico = est.ID_Estado_Fenologico;
GO

-- [Silver].[vFact_Cosecha_SAP] (VIEW)
CREATE   VIEW Silver.vFact_Cosecha_SAP AS
        SELECT 
            f.ID_Cosecha_SAP,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            cond.Sustrato AS Condicion_Sustrato,
            cond.Certificacion AS Condicion_Certificacion,
            f.Kg_Brutos,
            f.Kg_Neto_MP,
            f.Cantidad_Jabas,
            f.Lote,
            f.Almacen,
            f.Doc_Remision,
            f.Codigo_Cliente,
            f.Responsable,
            f.Descripcion_Material,
            f.Codigo_SAP_Material,
            f.Fecha_Recepcion,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Cosecha_SAP f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Condicion_Cultivo cond ON f.ID_Condicion_Cultivo = cond.ID_Condicion
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Evaluacion_Pesos] (VIEW)
CREATE   VIEW Silver.vFact_Evaluacion_Pesos AS
        SELECT 
            f.ID_Evaluacion_Pesos,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Peso_Promedio_Baya_g,
            f.Cantidad_Bayas_Muestra,
            f.Peso_Proyectado_Baya_g,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Evaluacion_Pesos f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Evaluacion_Vegetativa] (VIEW)
CREATE   VIEW Silver.vFact_Evaluacion_Vegetativa AS
        SELECT 
            f.ID_Fact_Evaluacion_Vegetativa,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            f.Semanas_Despues_Poda,
            f.Promedio_Altura,
            f.Promedio_Tallos_Basales,
            f.Promedio_Tallos_Basales_Nuevos,
            f.Promedio_Brotes_Generales,
            f.Promedio_Brotes_Productivos,
            f.Promedio_Diametro_Brote,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Evaluacion_Vegetativa f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Evaluacion_Vegetativa_Floracion] (VIEW)
CREATE   VIEW Silver.vFact_Evaluacion_Vegetativa_Floracion AS
        SELECT 
            f.ID_Fact_Evaluacion_Vegetativa_Floracion,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Cantidad_Plantas_Evaluadas,
            f.Cantidad_Plantas_en_Floracion,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Evaluacion_Vegetativa_Floracion f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Fisiologia] (VIEW)
CREATE   VIEW Silver.vFact_Fisiologia AS
        SELECT 
            f.ID_Fisiologia,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            f.Tercio,
            f.Brotes_Productivos,
            f.Brotes_Vegetativos,
            f.Hinchadas,
            f.Productivas,
            f.Total_Organos,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Fisiologia f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Floracion] (VIEW)
CREATE   VIEW Silver.vFact_Floracion AS
        SELECT 
            f.ID_Fact_Floracion,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Cantidad_Plantas_Evaluadas,
            f.Cantidad_Plantas_en_Floracion,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Floracion f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Induccion_Floral] (VIEW)
CREATE   VIEW Silver.vFact_Induccion_Floral AS
        SELECT 
            f.ID_Induccion_Floral,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Codigo_Consumidor,
            f.Cantidad_Plantas_Por_Cama,
            f.Cantidad_Plantas_Con_Induccion,
            f.Cantidad_Brotes_Con_Induccion,
            f.Cantidad_Brotes_Totales,
            f.Cantidad_Brotes_Con_Flor,
            f.Pct_Plantas_Con_Induccion,
            f.Pct_Brotes_Con_Induccion,
            f.Pct_Brotes_Con_Flor,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Induccion_Floral f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Maduracion] (VIEW)
CREATE   VIEW Silver.vFact_Maduracion AS
        SELECT 
            f.ID_Maduracion,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            est.Nombre_Estado AS Estado_Fenologico,
            cinta.Color_Cinta AS Color_Cinta,
            f.ID_Organo,
            f.Dias_Pasados_Del_Marcado,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Maduracion f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Estado_Fenologico est ON f.ID_Estado_Fenologico = est.ID_Estado_Fenologico
        LEFT JOIN Silver.Dim_Cinta cinta ON f.ID_Cinta = cinta.ID_Cinta
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Peladas] (VIEW)
CREATE   VIEW Silver.vFact_Peladas AS
        SELECT 
            f.ID_Peladas,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            f.Punto,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Botones_Florales,
            f.Flores,
            f.Bayas_Pequenas,
            f.Bayas_Grandes,
            f.Fase_1,
            f.Fase_2,
            f.Bayas_Cremas,
            f.Bayas_Maduras,
            f.Bayas_Cosechables,
            f.Plantas_Productivas,
            f.Plantas_No_Productivas,
            f.Muestras,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Peladas f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Proyecciones] (VIEW)
CREATE   VIEW Silver.vFact_Proyecciones AS
        SELECT 
            f.ID_Proyeccion,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            esc.Tipo_Escenario AS Escenario_Proyeccion,
            esc.Descripcion AS Escenario_Descripcion,
            wk.Estado AS Estado_Workflow,
            f.Kg_Proyectados,
            f.Kg_Pesimista,
            f.Kg_Optimista,
            f.Pct_Maduracion,
            f.Pct_Productivas,
            f.MAPE,
            f.Version_Modelo,
            f.Fecha_Cutoff,
            f.ID_Version_Datos,
            f.Flag_Override,
            f.Motivo_Override,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Proyecciones f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Escenario_Proyeccion esc ON f.ID_Escenario = esc.ID_Escenario
        LEFT JOIN Silver.Dim_Estado_Workflow wk ON f.ID_Estado_Workflow = wk.ID_Workflow
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Tareo] (VIEW)
CREATE   VIEW Silver.vFact_Tareo AS
        SELECT 
            f.ID_Tareo,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            per.Nombre_Completo AS Colaborador,
            per.DNI AS Colaborador_DNI,
            sup.Nombre_Completo AS Supervisor,
            sup.DNI AS Supervisor_DNI,
            act.Nombre_Actividad AS Actividad_Operativa,
            f.Horas_Trabajadas,
            f.ID_Planilla,
            f.Es_Observado_SAP,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema
        FROM Silver.Fact_Tareo f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Personal sup ON f.ID_Personal_Supervisor = sup.ID_Personal
        LEFT JOIN Silver.Dim_Actividad_Operativa act ON f.ID_Actividad_Operativa = act.ID_Actividad
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Tasa_Crecimiento_Brotes] (VIEW)
CREATE   VIEW Silver.vFact_Tasa_Crecimiento_Brotes AS
        SELECT 
            f.ID_Tasa_Crecimiento_Brotes,
            f.Fecha_Evento,
            fundo.Fundo,
            sector.Sector,
            modulo.Modulo,
            modulo.SubModulo,
            turno.Turno,
            valvula.Valvula,
            cama.Cama_Normalizada AS Cama,
            var.Nombre_Variedad AS Variedad,
            per.Nombre_Completo AS Evaluador,
            per.DNI AS Evaluador_DNI,
            f.Tipo_Evaluacion,
            f.Condicion,
            f.Estado_Vegetativo,
            f.Tipo_Tallo,
            f.Codigo_Ensayo,
            f.Codigo_Origen,
            f.Campana AS Campana_Origen,
            f.Observacion,
            f.Fecha_Poda_Aux,
            f.Dias_Desde_Poda,
            f.Medida_Crecimiento,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema,
            f.Estado_DQ
        FROM Silver.Fact_Tasa_Crecimiento_Brotes f
        JOIN Silver.Dim_Geografia geo ON f.ID_Geografia = geo.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fundo ON geo.ID_Fundo_Catalogo = fundo.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Sector_Catalogo sector ON geo.ID_Sector_Catalogo = sector.ID_Sector_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo modulo ON geo.ID_Modulo_Catalogo = modulo.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo turno ON geo.ID_Turno_Catalogo = turno.ID_Turno_Catalogo
        LEFT JOIN Silver.Dim_Valvula_Catalogo valvula ON geo.ID_Valvula_Catalogo = valvula.ID_Valvula_Catalogo
        LEFT JOIN Silver.Dim_Cama_Catalogo cama ON geo.ID_Cama_Catalogo = cama.ID_Cama_Catalogo
        LEFT JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
        LEFT JOIN Silver.Dim_Personal per ON f.ID_Personal = per.ID_Personal
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO

-- [Silver].[vFact_Telemetria_Clima] (VIEW)
CREATE   VIEW Silver.vFact_Telemetria_Clima AS
        SELECT 
            f.ID_Telemetria_Clima,
            f.Fecha_Evento,
            f.Sector_Climatico,
            f.Temperatura_Max_C,
            f.Temperatura_Min_C,
            f.Humedad_Relativa_Pct,
            f.Precipitacion_mm,
            f.VPD,
            f.Radiacion_Solar,
            c_camp.Nombre_Campana AS Campana,
            f.Fecha_Sistema
        FROM Silver.Fact_Telemetria_Clima f
        LEFT JOIN Silver.Dim_Campana c_camp ON f.ID_Campana = c_camp.ID_Campana;
GO
