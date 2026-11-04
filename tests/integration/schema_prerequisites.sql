-- Prerequisites absent from the exported snapshot, required by phase46.
-- Applied ONLY to a newly created synthetic ACP_E2E_* database.
IF DB_NAME() NOT LIKE 'ACP[_]E2E[_]%' THROW 51000, 'E2E database required', 1;
GO
IF COL_LENGTH('Silver.Dim_Campana','Fecha_Inicio_Poda') IS NULL
    ALTER TABLE Silver.Dim_Campana ADD Fecha_Inicio_Poda DATE NULL;
IF COL_LENGTH('Silver.Dim_Campana','Fecha_Fin_Evaluacion') IS NULL
    ALTER TABLE Silver.Dim_Campana ADD Fecha_Fin_Evaluacion DATE NULL;
IF COL_LENGTH('Silver.Dim_Campana','Fecha_Inicio_Campana') IS NULL
    ALTER TABLE Silver.Dim_Campana ADD Fecha_Inicio_Campana DATE NULL;
IF COL_LENGTH('Silver.Dim_Campana','Fecha_Fin_Campana') IS NULL
    ALTER TABLE Silver.Dim_Campana ADD Fecha_Fin_Campana DATE NULL;
IF COL_LENGTH('Silver.Dim_Campana','Es_Vigente_Operacion') IS NULL
    ALTER TABLE Silver.Dim_Campana ADD Es_Vigente_Operacion BIT NOT NULL DEFAULT 0;
GO
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Campana WHERE ID_Campana=0)
BEGIN
    SET IDENTITY_INSERT Silver.Dim_Campana ON;
    INSERT INTO Silver.Dim_Campana(ID_Campana, Anio_Cosecha,Nombre_Campana,Estado,Es_Activa)
    VALUES(0,0,'SIN_CAMPANA','ACTIVA',1);
    SET IDENTITY_INSERT Silver.Dim_Campana OFF;
END;
IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Campana WHERE Anio_Cosecha=2025)
    INSERT INTO Silver.Dim_Campana(Anio_Cosecha,Nombre_Campana,Estado,Es_Activa)
    VALUES(2025,'2025 - 2026','ACTIVA',1);
GO
-- Runtime schema contract present in current Python/Gold but absent from snapshot.
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Cantidad') IS NULL
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD Cantidad INT NULL;
IF COL_LENGTH('Silver.Fact_Censo_Plantas','Cantidad') IS NULL
    ALTER TABLE Silver.Fact_Censo_Plantas ADD Cantidad INT NULL;
IF COL_LENGTH('Silver.Fact_Censo_Plantas','ID_Estado_Planta') IS NULL
    ALTER TABLE Silver.Fact_Censo_Plantas ADD ID_Estado_Planta INT NULL;
IF COL_LENGTH('Silver.Fact_Censo_Plantas','Linea_Raw') IS NULL
    ALTER TABLE Silver.Fact_Censo_Plantas ADD Linea_Raw NVARCHAR(100) NULL;
IF OBJECT_ID('Silver.Dim_Estado_Planta','U') IS NULL
    CREATE TABLE Silver.Dim_Estado_Planta(ID_Estado_Planta INT PRIMARY KEY,Nombre_Estado NVARCHAR(100));
IF COL_LENGTH('Silver.Fact_Ciclo_Poda','Fecha_Registro_App') IS NULL
    ALTER TABLE Silver.Fact_Ciclo_Poda ADD Fecha_Registro_App DATETIME2 NULL;
GO
IF COL_LENGTH('Silver.Fact_Evaluacion_Pesos','Cantidad_Cosechables') IS NULL
    ALTER TABLE Silver.Fact_Evaluacion_Pesos ADD Cantidad_Cosechables FLOAT NULL;
IF COL_LENGTH('Silver.Fact_Evaluacion_Pesos','Peso_Cosechables_g') IS NULL
    ALTER TABLE Silver.Fact_Evaluacion_Pesos ADD Peso_Cosechables_g FLOAT NULL;
GO
IF COL_LENGTH('Bronce.Fiscalizacion','DNI_Evaluador_Raw') IS NULL
    ALTER TABLE Bronce.Fiscalizacion ADD DNI_Evaluador_Raw NVARCHAR(100) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Evaluador_Raw') IS NULL
    ALTER TABLE Bronce.Fiscalizacion ADD Evaluador_Raw NVARCHAR(200) NULL;
GO
DECLARE @column SYSNAME;
DECLARE columns_to_add CURSOR LOCAL FAST_FORWARD FOR
SELECT name FROM (VALUES ('Fecha_Raw'),('Fundo_Raw'),('DNI_Raw'),('Estado_Planta_Raw'),('Cantidad_Raw'),('Linea_Raw'),('Evaluador_Raw'),('Fecha_Detalle_Raw'),('Fecha_Subida_Raw'),('Campana_Raw')) c(name);
OPEN columns_to_add;
FETCH NEXT FROM columns_to_add INTO @column;
WHILE @@FETCH_STATUS=0
BEGIN
    IF COL_LENGTH('Bronce.Censo_Plantas',@column) IS NULL
        EXEC('ALTER TABLE Bronce.Censo_Plantas ADD '+@column+' NVARCHAR(300) NULL');
    FETCH NEXT FROM columns_to_add INTO @column;
END;
CLOSE columns_to_add;
DEALLOCATE columns_to_add;
GO
IF COL_LENGTH('Silver.Fact_Tasa_Crecimiento_Brotes','Planta_Brote') IS NULL
    ALTER TABLE Silver.Fact_Tasa_Crecimiento_Brotes ADD Planta_Brote NVARCHAR(100) NULL;
IF COL_LENGTH('Bronce.Floracion','ID_Floracion') IS NULL
    EXEC sp_rename 'Bronce.Floracion.ID_Evaluacion_Vegetativa','ID_Floracion','COLUMN';
IF OBJECT_ID('Bronce.Base_Plantas_Area','U') IS NULL
    CREATE TABLE Bronce.Base_Plantas_Area(
        ID_Base_Plantas_Area BIGINT IDENTITY PRIMARY KEY,
        Campana_Raw NVARCHAR(100), Modulo_Raw NVARCHAR(100), Turno_Raw NVARCHAR(100),
        Valvula_Raw NVARCHAR(100), Variedad_Raw NVARCHAR(100), Area_Raw NVARCHAR(100),
        Plantas_Raw NVARCHAR(100), Nombre_Archivo NVARCHAR(255),
        Estado_Carga NVARCHAR(20) DEFAULT 'CARGADO', Fecha_Sistema DATETIME2 DEFAULT GETDATE());
GO
