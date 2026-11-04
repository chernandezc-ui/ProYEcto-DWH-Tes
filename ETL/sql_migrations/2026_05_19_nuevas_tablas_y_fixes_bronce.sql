/* ============================================================================
   Nuevas tablas Bronce + ajustes derivados del análisis de archivos entrantes
   Fecha   : 2026-05-19
   Contexto: 3 archivos en data/entrada/ no tenían destino mapeado.
             Fixes:
               1) Crear Bronce.Censo_Plantas (dim plantas por modulo/variedad)
               2) Crear Bronce.Cosecha_SAP   (histórico cosecha agregado)
               3) ALTER Bronce.Conteo_Fruta  (agregar Fundo_Raw/Sector_Raw que
                  el cargador genera pero no existen en tabla)
   ============================================================================ */

USE ACP_DataWarehose_Proyecciones;
GO

SET XACT_ABORT ON;
BEGIN TRAN nuevas_tablas_bronce;

/* ---------------------------------------------------------------------------
   1) Bronce.Censo_Plantas
      Archivo origen : fact_Censo_Plantas.xlsx
      Layout         : Campaña, Módulo, Turno, Válvula, Variedad, Área, Plantas
   --------------------------------------------------------------------------- */
IF OBJECT_ID('Bronce.Censo_Plantas', 'U') IS NULL
BEGIN
    CREATE TABLE Bronce.Censo_Plantas
    (
        ID_Censo_Plantas  BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Bronce_Censo_Plantas PRIMARY KEY,
        Campana_Raw       NVARCHAR(50)         NULL,
        Modulo_Raw        NVARCHAR(50)         NULL,
        Turno_Raw         NVARCHAR(50)         NULL,
        Valvula_Raw       NVARCHAR(50)         NULL,
        Variedad_Raw      NVARCHAR(100)        NULL,
        Area_Raw          NVARCHAR(30)         NULL,
        Plantas_Raw       NVARCHAR(30)         NULL,
        Valores_Raw       NVARCHAR(MAX)        NULL,
        Nombre_Archivo    NVARCHAR(255)        NOT NULL,
        Fecha_Sistema     DATETIME2            NOT NULL
            CONSTRAINT DF_Bronce_Censo_Plantas_Fecha_Sistema DEFAULT (SYSDATETIME()),
        Estado_Carga      NVARCHAR(20)         NOT NULL
            CONSTRAINT DF_Bronce_Censo_Plantas_Estado_Carga DEFAULT ('CARGADO')
    );
END;


/* ---------------------------------------------------------------------------
   2) Bronce.Cosecha_SAP
      Archivo origen : historico_BI_Cosecha3.xlsx (hoja Sheet1)
      Layout         : Campaña, Fecha, Semana, Sector, Módulo, Turno, Válvula,
                       Variedad, Kg Total, Área, Plantas, SemCal, Semana Cosecha
   --------------------------------------------------------------------------- */
IF OBJECT_ID('Bronce.Cosecha_SAP', 'U') IS NULL
BEGIN
    CREATE TABLE Bronce.Cosecha_SAP
    (
        ID_Cosecha_SAP    BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Bronce_Cosecha_SAP PRIMARY KEY,
        Campana_Raw       NVARCHAR(50)         NULL,
        Fecha_Raw         NVARCHAR(50)         NULL,
        Semana_Raw        NVARCHAR(20)         NULL,
        Sector_Raw        NVARCHAR(50)         NULL,
        Modulo_Raw        NVARCHAR(50)         NULL,
        Turno_Raw         NVARCHAR(50)         NULL,
        Valvula_Raw       NVARCHAR(50)         NULL,
        Variedad_Raw      NVARCHAR(100)        NULL,
        Kg_Total_Raw      NVARCHAR(30)         NULL,
        Area_Raw          NVARCHAR(30)         NULL,
        Plantas_Raw       NVARCHAR(30)         NULL,
        SemCal_Raw        NVARCHAR(20)         NULL,
        Semana_Cosecha_Raw NVARCHAR(20)        NULL,
        Valores_Raw       NVARCHAR(MAX)        NULL,
        Nombre_Archivo    NVARCHAR(255)        NOT NULL,
        Fecha_Sistema     DATETIME2            NOT NULL
            CONSTRAINT DF_Bronce_Cosecha_SAP_Fecha_Sistema DEFAULT (SYSDATETIME()),
        Estado_Carga      NVARCHAR(20)         NOT NULL
            CONSTRAINT DF_Bronce_Cosecha_SAP_Estado_Carga DEFAULT ('CARGADO')
    );
END;


/* ---------------------------------------------------------------------------
   3) Bronce.Conteo_Fruta — agregar columnas que el cargador genera
      Hoy van a Valores_Raw como string concatenado (pérdida de tipado).
   --------------------------------------------------------------------------- */
IF COL_LENGTH('Bronce.Conteo_Fruta', 'Fundo_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta
        ADD Fundo_Raw NVARCHAR(50) NULL;

IF COL_LENGTH('Bronce.Conteo_Fruta', 'Sector_Raw') IS NULL
    ALTER TABLE Bronce.Conteo_Fruta
        ADD Sector_Raw NVARCHAR(50) NULL;


/* ---------------------------------------------------------------------------
   VERIFICACION
   --------------------------------------------------------------------------- */
SELECT TABLE_NAME, COUNT(*) AS columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'Bronce'
  AND TABLE_NAME IN ('Censo_Plantas', 'Cosecha_SAP', 'Conteo_Fruta')
GROUP BY TABLE_NAME
ORDER BY TABLE_NAME;


/* ---------------------------------------------------------------------------
   COMMIT manual: revisar resultados y ejecutar
       COMMIT TRAN nuevas_tablas_bronce;
   o:
       ROLLBACK TRAN nuevas_tablas_bronce;
   --------------------------------------------------------------------------- */
