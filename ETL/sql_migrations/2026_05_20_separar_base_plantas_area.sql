/* ============================================================================
   Separar Base_Plantas_Area de Censo_Plantas
   Fecha   : 2026-05-20
   Motivo  : 1 archivo -> 1 Bronce -> 1 Silver. Base_Plantas_Area_v2.xlsx no
             debe mezclarse con Historico_Censo.xlsx en la misma Bronce.
             Modelo correcto:
               Base_Plantas_Area_v2.xlsx  -> Bronce.Base_Plantas_Area -> Silver.Fact_areas_plantas
               Historico_Censo.xlsx       -> Bronce.Censo_Plantas     -> Silver.Fact_Censo_Plantas
   ============================================================================ */

USE ACP_DataWarehose_Proyecciones;
GO

SET XACT_ABORT ON;
BEGIN TRAN separar_base_plantas_area;

/* ---------------------------------------------------------------------------
   Bronce.Base_Plantas_Area
   Archivo origen : Base_Plantas_Area_v2.xlsx (Hoja1)
   Layout         : Campania, Modulo, Turno, Valvula, Variedad, Area, Plantas
   --------------------------------------------------------------------------- */
IF OBJECT_ID('Bronce.Base_Plantas_Area', 'U') IS NULL
BEGIN
    CREATE TABLE Bronce.Base_Plantas_Area
    (
        ID_Base_Plantas_Area BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Bronce_Base_Plantas_Area PRIMARY KEY,
        Campana_Raw          NVARCHAR(50)         NULL,
        Modulo_Raw           NVARCHAR(50)         NULL,
        Turno_Raw            NVARCHAR(50)         NULL,
        Valvula_Raw          NVARCHAR(50)         NULL,
        Variedad_Raw         NVARCHAR(100)        NULL,
        Area_Raw             NVARCHAR(30)         NULL,
        Plantas_Raw          NVARCHAR(30)         NULL,
        Valores_Raw          NVARCHAR(MAX)        NULL,
        Nombre_Archivo       NVARCHAR(255)        NOT NULL,
        Fecha_Sistema        DATETIME2            NOT NULL
            CONSTRAINT DF_Bronce_Base_Plantas_Area_Fecha_Sistema DEFAULT (SYSDATETIME()),
        Estado_Carga         NVARCHAR(20)         NOT NULL
            CONSTRAINT DF_Bronce_Base_Plantas_Area_Estado_Carga DEFAULT ('CARGADO')
    );
END;

/* ---------------------------------------------------------------------------
   ALTER Bronce.Censo_Plantas
   El layout real de Historico_Censo.xlsx trae:
     Buenas, Regulares, Malas, Muertas, Ha en Produccion
   Estas columnas faltan en la tabla actual y se perdian al cargar.
   --------------------------------------------------------------------------- */
IF COL_LENGTH('Bronce.Censo_Plantas', 'Ha_Produccion_Raw') IS NULL
    ALTER TABLE Bronce.Censo_Plantas ADD Ha_Produccion_Raw NVARCHAR(30) NULL;
IF COL_LENGTH('Bronce.Censo_Plantas', 'Buenas_Raw') IS NULL
    ALTER TABLE Bronce.Censo_Plantas ADD Buenas_Raw NVARCHAR(30) NULL;
IF COL_LENGTH('Bronce.Censo_Plantas', 'Regulares_Raw') IS NULL
    ALTER TABLE Bronce.Censo_Plantas ADD Regulares_Raw NVARCHAR(30) NULL;
IF COL_LENGTH('Bronce.Censo_Plantas', 'Malas_Raw') IS NULL
    ALTER TABLE Bronce.Censo_Plantas ADD Malas_Raw NVARCHAR(30) NULL;
IF COL_LENGTH('Bronce.Censo_Plantas', 'Muertas_Raw') IS NULL
    ALTER TABLE Bronce.Censo_Plantas ADD Muertas_Raw NVARCHAR(30) NULL;

/* ---------------------------------------------------------------------------
   ALTER Bronce.Ciclos_Fenologicos
   Soportar carga historica de fenologia con unpivot (1 fila por estado).
   --------------------------------------------------------------------------- */
IF COL_LENGTH('Bronce.Ciclos_Fenologicos', 'Campana_Raw') IS NULL
    ALTER TABLE Bronce.Ciclos_Fenologicos ADD Campana_Raw NVARCHAR(50) NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos', 'Anio_Raw') IS NULL
    ALTER TABLE Bronce.Ciclos_Fenologicos ADD Anio_Raw NVARCHAR(10) NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos', 'Semana_Raw') IS NULL
    ALTER TABLE Bronce.Ciclos_Fenologicos ADD Semana_Raw NVARCHAR(10) NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos', 'Estado_Raw') IS NULL
    ALTER TABLE Bronce.Ciclos_Fenologicos ADD Estado_Raw NVARCHAR(50) NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos', 'Cantidad_Raw') IS NULL
    ALTER TABLE Bronce.Ciclos_Fenologicos ADD Cantidad_Raw NVARCHAR(30) NULL;

SELECT TABLE_NAME, COUNT(*) AS columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'Bronce'
  AND TABLE_NAME IN ('Base_Plantas_Area', 'Censo_Plantas', 'Ciclos_Fenologicos')
GROUP BY TABLE_NAME
ORDER BY TABLE_NAME;

/* ---------------------------------------------------------------------------
   COMMIT manual: revisar resultados y ejecutar
       COMMIT TRAN separar_base_plantas_area;
   o:
       ROLLBACK TRAN separar_base_plantas_area;
   --------------------------------------------------------------------------- */
