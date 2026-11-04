/* ============================================================================
   Separar fenologia historica de conteo de frutas
   Fecha   : 2026-05-20
   Modelo  :
     historico_fenologia.xlsx -> Bronce.Fenologia (unpivot) -> Silver.Fact_Conteo_Fenologico
     conteo_fruta diario       -> Bronce.Conteo_Fruta        -> Silver.Fact_Conteo_Frutas
   ============================================================================ */

USE ACP_DataWarehose_Proyecciones;
GO

SET XACT_ABORT ON;
BEGIN TRAN fenologia_y_conteo_frutas;

/* ---------------------------------------------------------------------------
   Bronce.Fenologia
   Origen: historico_fenologia.xlsx con unpivot por estado fenologico.
   --------------------------------------------------------------------------- */
IF OBJECT_ID('Bronce.Fenologia', 'U') IS NULL
BEGIN
    CREATE TABLE Bronce.Fenologia
    (
        ID_Fenologia    BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Bronce_Fenologia PRIMARY KEY,
        Campana_Raw     NVARCHAR(50)  NULL,
        Anio_Raw        NVARCHAR(10)  NULL,
        Semana_Raw      NVARCHAR(10)  NULL,
        Fecha_Raw       NVARCHAR(50)  NULL,
        Modulo_Raw      NVARCHAR(50)  NULL,
        Turno_Raw       NVARCHAR(50)  NULL,
        Valvula_Raw     NVARCHAR(50)  NULL,
        Variedad_Raw    NVARCHAR(100) NULL,
        Estado_Raw      NVARCHAR(50)  NULL,
        Cantidad_Raw    NVARCHAR(30)  NULL,
        Valores_Raw     NVARCHAR(MAX) NULL,
        Nombre_Archivo  NVARCHAR(255) NOT NULL,
        Fecha_Sistema   DATETIME2     NOT NULL
            CONSTRAINT DF_Bronce_Fenologia_Fecha_Sistema DEFAULT (SYSDATETIME()),
        Estado_Carga    NVARCHAR(20)  NOT NULL
            CONSTRAINT DF_Bronce_Fenologia_Estado_Carga DEFAULT ('CARGADO')
    );
END;

/* ---------------------------------------------------------------------------
   Silver.Fact_Conteo_Frutas
   Origen: Bronce.Conteo_Fruta (flujo diario). Grano y columnas igual a
   Fact_Conteo_Fenologico para reusar el patron de procesador.
   --------------------------------------------------------------------------- */
IF OBJECT_ID('Silver.Fact_Conteo_Frutas', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.Fact_Conteo_Frutas
    (
        ID_Conteo_Frutas       BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_Silver_Fact_Conteo_Frutas PRIMARY KEY,
        ID_Geografia           INT NOT NULL,
        ID_Tiempo              INT NOT NULL,
        ID_Variedad            INT NOT NULL,
        ID_Personal            INT NULL,
        ID_Estado_Fenologico   INT NOT NULL,
        Cantidad_Organos       INT NULL,
        Fecha_Evento           DATE NOT NULL,
        Fecha_Sistema          DATETIME2 NOT NULL
            CONSTRAINT DF_Silver_Fact_Conteo_Frutas_Fecha_Sistema DEFAULT (SYSDATETIME()),
        Estado_DQ              NVARCHAR(10) NULL,
        Punto                  NVARCHAR(20) NULL,
        ID_Campana             INT NULL,
        Fecha_Registro         DATETIME2 NULL,
        Plantas_Productivas    INT NULL,
        Plantas_No_Productivas INT NULL
    );
END;

SELECT TABLE_SCHEMA, TABLE_NAME, COUNT(*) AS columnas
FROM INFORMATION_SCHEMA.COLUMNS
WHERE (TABLE_SCHEMA='Bronce' AND TABLE_NAME='Fenologia')
   OR (TABLE_SCHEMA='Silver' AND TABLE_NAME='Fact_Conteo_Frutas')
GROUP BY TABLE_SCHEMA, TABLE_NAME;

/* ---------------------------------------------------------------------------
   COMMIT TRAN fenologia_y_conteo_frutas;  o ROLLBACK
   --------------------------------------------------------------------------- */
