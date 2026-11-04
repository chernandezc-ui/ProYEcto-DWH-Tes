/*
================================================================================
 Refactor Bronce -> Silver  (2026-05-20)
 BD: ACP_DataWarehose_Proyecciones
 Script idempotente. Orden seguro:
   1) ADD columnas nuevas        (no destructivo)
   2) Crear Silver.dim_Estado_Plantas + seeds
   3) Migrar Bronce.Maduracion -> Bronce.Ciclos_Fenologicos
   4) RENAME columnas
   5) DROP columnas
   6) DROP TABLE Bronce.Maduracion
 Recomendacion: BACKUP DATABASE antes de ejecutar pasos 4-6.
================================================================================
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRAN;

/* ---------- helper: macros de existencia via IF NOT EXISTS inline ---------- */

/* =====================================================================
   PASO 1.  ADD nuevas columnas (no destructivo)
   ===================================================================== */

------------------------------------------------------------ 1.1 Censo_Plantas
IF COL_LENGTH('Bronce.Censo_Plantas','Fecha_Raw')         IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Fecha_Raw         NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','Fecha_Detalle_Raw') IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Fecha_Detalle_Raw NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','Fecha_Subida_Raw')  IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Fecha_Subida_Raw  NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','DNI_Raw')           IS NULL ALTER TABLE Bronce.Censo_Plantas ADD DNI_Raw           NVARCHAR(20)  NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','Evaluador_Raw')     IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Evaluador_Raw     NVARCHAR(150) NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','Linea_Raw')         IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Linea_Raw         NVARCHAR(20)  NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','Estado_Planta_Raw') IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Estado_Planta_Raw NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Censo_Plantas','Cantidad_Raw')      IS NULL ALTER TABLE Bronce.Censo_Plantas ADD Cantidad_Raw      NVARCHAR(30)  NULL;

------------------------------------------------------------ 1.2 Ciclos_Fenologicos
IF COL_LENGTH('Bronce.Ciclos_Fenologicos','Fecha_Registro_Raw')   IS NULL ALTER TABLE Bronce.Ciclos_Fenologicos ADD Fecha_Registro_Raw   NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos','DNI_Raw')              IS NULL ALTER TABLE Bronce.Ciclos_Fenologicos ADD DNI_Raw              NVARCHAR(20)  NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos','ID_Estado_Ciclo_Raw')  IS NULL ALTER TABLE Bronce.Ciclos_Fenologicos ADD ID_Estado_Ciclo_Raw  NVARCHAR(20)  NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos','Etapa_Fenologica_Raw') IS NULL ALTER TABLE Bronce.Ciclos_Fenologicos ADD Etapa_Fenologica_Raw NVARCHAR(100) NULL;
IF COL_LENGTH('Bronce.Ciclos_Fenologicos','Sector_Raw')           IS NULL ALTER TABLE Bronce.Ciclos_Fenologicos ADD Sector_Raw           NVARCHAR(200) NULL;

------------------------------------------------------------ 1.3 Evaluacion_Pesos (solo ADD aqui; drop en paso 5)
IF COL_LENGTH('Bronce.Evaluacion_Pesos','Fecha_Registro_Raw') IS NULL ALTER TABLE Bronce.Evaluacion_Pesos ADD Fecha_Registro_Raw NVARCHAR(50) NULL;

------------------------------------------------------------ 1.4 Evaluacion_Vegetativa
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Nombres_Raw')      IS NULL ALTER TABLE Bronce.Evaluacion_Vegetativa ADD Nombres_Raw      NVARCHAR(200) NULL;
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Fecha_Subida_Raw') IS NULL ALTER TABLE Bronce.Evaluacion_Vegetativa ADD Fecha_Subida_Raw NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Evaluacion_Raw')   IS NULL ALTER TABLE Bronce.Evaluacion_Vegetativa ADD Evaluacion_Raw   NVARCHAR(100) NULL;

------------------------------------------------------------ 1.5 Fiscalizacion
IF COL_LENGTH('Bronce.Fiscalizacion','Cartilla_Raw')           IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Cartilla_Raw           NVARCHAR(100) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Fecha_Registro_Raw')     IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Fecha_Registro_Raw     NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Fecha_Subida_Raw')       IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Fecha_Subida_Raw       NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Fiscalizador_Raw')       IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Fiscalizador_Raw       NVARCHAR(200) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Tipo_Fiscalizador_Raw')  IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Tipo_Fiscalizador_Raw  NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','DNI_Evaluador_Raw')      IS NULL ALTER TABLE Bronce.Fiscalizacion ADD DNI_Evaluador_Raw      NVARCHAR(20)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Evaluador_Raw')          IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Evaluador_Raw          NVARCHAR(200) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Valvula_Raw')            IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Valvula_Raw            NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Variedad_Raw')           IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Variedad_Raw           NVARCHAR(100) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Cama_Raw')               IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Cama_Raw               NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Muestra_Raw')            IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Muestra_Raw            NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Observaciones_Raw')      IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Observaciones_Raw      NVARCHAR(500) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Descripcion_Raw')        IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Descripcion_Raw        NVARCHAR(200) NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Cantidad1_Raw')          IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Cantidad1_Raw          NVARCHAR(30)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Fiscalizacion_Raw')      IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Fiscalizacion_Raw      NVARCHAR(30)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Cantidad3_Raw')          IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Cantidad3_Raw          NVARCHAR(30)  NULL;
IF COL_LENGTH('Bronce.Fiscalizacion','Fiscalizacion2_Raw')     IS NULL ALTER TABLE Bronce.Fiscalizacion ADD Fiscalizacion2_Raw     NVARCHAR(30)  NULL;

------------------------------------------------------------ 1.6 Fisiologia
IF COL_LENGTH('Bronce.Fisiologia','Fecha_Detalle_Raw') IS NULL ALTER TABLE Bronce.Fisiologia ADD Fecha_Detalle_Raw NVARCHAR(50) NULL;
IF COL_LENGTH('Bronce.Fisiologia','Fecha_Subida_Raw')  IS NULL ALTER TABLE Bronce.Fisiologia ADD Fecha_Subida_Raw  NVARCHAR(50) NULL;
IF COL_LENGTH('Bronce.Fisiologia','DNI_Raw')           IS NULL ALTER TABLE Bronce.Fisiologia ADD DNI_Raw           NVARCHAR(20) NULL;

------------------------------------------------------------ 1.7 Floracion
IF COL_LENGTH('Bronce.Floracion','Fecha_Detalle_Raw') IS NULL ALTER TABLE Bronce.Floracion ADD Fecha_Detalle_Raw NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Floracion','Variedad_Raw')      IS NULL ALTER TABLE Bronce.Floracion ADD Variedad_Raw      NVARCHAR(100) NULL;

------------------------------------------------------------ 1.8 Induccion_Floral
IF COL_LENGTH('Bronce.Induccion_Floral','Fecha_Registro_Raw') IS NULL ALTER TABLE Bronce.Induccion_Floral ADD Fecha_Registro_Raw NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Induccion_Floral','Evaluacion_Raw')     IS NULL ALTER TABLE Bronce.Induccion_Floral ADD Evaluacion_Raw     NVARCHAR(100) NULL;

------------------------------------------------------------ 1.9 Tasa_Crecimiento_Brotes
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Fecha_Registro_Raw') IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Fecha_Registro_Raw NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Fecha_Subida_Raw')   IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Fecha_Subida_Raw   NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Nombres_Raw')        IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Nombres_Raw        NVARCHAR(200) NULL;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Cama_Raw')           IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Cama_Raw           NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Evaluacion_Raw')     IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Evaluacion_Raw     NVARCHAR(100) NULL;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Planta_Brote_Raw')   IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Planta_Brote_Raw   NVARCHAR(50)  NULL;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Cantidad_Raw')       IS NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes ADD Cantidad_Raw       NVARCHAR(30)  NULL;

PRINT '[PASO 1] ADD columnas OK';


/* =====================================================================
   PASO 2.  Crear Silver.dim_Estado_Plantas + seeds
   ===================================================================== */
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'Silver')
    EXEC('CREATE SCHEMA Silver');

IF NOT EXISTS (SELECT 1 FROM sys.tables t
               JOIN sys.schemas s ON s.schema_id = t.schema_id
               WHERE s.name = 'Silver' AND t.name = 'dim_Estado_Plantas')
BEGIN
    CREATE TABLE Silver.dim_Estado_Plantas (
        ID_Estado_Planta INT IDENTITY(1,1) PRIMARY KEY,
        Codigo           NVARCHAR(20)  NOT NULL UNIQUE,
        Descripcion      NVARCHAR(50)  NOT NULL,
        Activo           BIT           NOT NULL CONSTRAINT DF_dim_Estado_Plantas_Activo DEFAULT 1,
        Fecha_Creacion   DATETIME2     NOT NULL CONSTRAINT DF_dim_Estado_Plantas_FCrea DEFAULT SYSDATETIME()
    );
END;

MERGE Silver.dim_Estado_Plantas AS dst
USING (VALUES
    ('BUENAS',    'Plantas Buenas'),
    ('REGULARES', 'Plantas Regulares'),
    ('MALAS',     'Plantas Malas'),
    ('HOYOS',     'Hoyos')
) AS src(Codigo, Descripcion)
   ON dst.Codigo = src.Codigo
WHEN NOT MATCHED BY TARGET THEN
    INSERT (Codigo, Descripcion) VALUES (src.Codigo, src.Descripcion);

PRINT '[PASO 2] dim_Estado_Plantas creada/poblada OK';


/* =====================================================================
   PASO 3.  Migrar Bronce.Maduracion -> Bronce.Ciclos_Fenologicos
   Solo migra si la tabla aun existe.
   ===================================================================== */
IF EXISTS (SELECT 1 FROM sys.tables t
           JOIN sys.schemas s ON s.schema_id = t.schema_id
           WHERE s.name = 'Bronce' AND t.name = 'Maduracion')
BEGIN
    DECLARE @cnt_origen INT, @cnt_destino_pre INT, @cnt_destino_post INT;
    SELECT @cnt_origen     = COUNT(*) FROM Bronce.Maduracion;
    SELECT @cnt_destino_pre= COUNT(*) FROM Bronce.Ciclos_Fenologicos;

    /* EXEC para diferir la compilacion del INSERT: Sector_Raw fue agregada
       en el PASO 1 dentro de este mismo batch y el parser estatico no la ve. */
    EXEC sp_executesql N'
        INSERT INTO Bronce.Ciclos_Fenologicos
            (Fecha_Raw, Modulo_Raw, Turno_Raw, Valvula_Raw, Variedad_Raw,
             Evaluador_Raw, Organo_Raw, Color_Raw, Valores_Raw,
             Nombre_Archivo, Fecha_Sistema, Estado_Carga, Sector_Raw)
        SELECT
             Fecha_Raw, Modulo_Raw, Turno_Raw, Valvula_Raw, Variedad_Raw,
             Evaluador_Raw, Organo_Raw, Color_Raw, Valores_Raw,
             Nombre_Archivo, Fecha_Sistema, Estado_Carga, Sector_Raw
        FROM Bronce.Maduracion;
    ';

    SELECT @cnt_destino_post = COUNT(*) FROM Bronce.Ciclos_Fenologicos;

    PRINT CONCAT('[PASO 3] Maduracion -> Ciclos_Fenologicos: ',
                 @cnt_origen, ' filas origen, +',
                 (@cnt_destino_post - @cnt_destino_pre), ' filas insertadas');

    IF (@cnt_destino_post - @cnt_destino_pre) <> @cnt_origen
        THROW 50001, 'Migracion Maduracion: conteo no cuadra. ROLLBACK.', 1;
END
ELSE
    PRINT '[PASO 3] Maduracion ya no existe, skip migracion';


/* =====================================================================
   PASO 4.  RENAMES (sp_rename)
   ===================================================================== */

-- 4.1 Conteo_Fruta: Tipo_Evaluacion_Raw -> Evaluacion_Raw
IF COL_LENGTH('Bronce.Conteo_Fruta','Tipo_Evaluacion_Raw') IS NOT NULL
   AND COL_LENGTH('Bronce.Conteo_Fruta','Evaluacion_Raw')  IS NULL
    EXEC sp_rename 'Bronce.Conteo_Fruta.Tipo_Evaluacion_Raw',
                   'Evaluacion_Raw', 'COLUMN';

-- 4.2 Fiscalizacion: DNI_Raw -> DNI_Fiscalizador_Raw
IF COL_LENGTH('Bronce.Fiscalizacion','DNI_Raw')              IS NOT NULL
   AND COL_LENGTH('Bronce.Fiscalizacion','DNI_Fiscalizador_Raw') IS NULL
    EXEC sp_rename 'Bronce.Fiscalizacion.DNI_Raw',
                   'DNI_Fiscalizador_Raw', 'COLUMN';

-- 4.3 Floracion: ID_Evaluacion_Vegetativa -> ID_Floracion
IF COL_LENGTH('Bronce.Floracion','ID_Evaluacion_Vegetativa') IS NOT NULL
   AND COL_LENGTH('Bronce.Floracion','ID_Floracion')         IS NULL
    EXEC sp_rename 'Bronce.Floracion.ID_Evaluacion_Vegetativa',
                   'ID_Floracion', 'COLUMN';

-- 4.4 Tasa_Crecimiento_Brotes: Tipo_Tallo_Raw -> Tallo_Raw
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Tipo_Tallo_Raw') IS NOT NULL
   AND COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Tallo_Raw')  IS NULL
    EXEC sp_rename 'Bronce.Tasa_Crecimiento_Brotes.Tipo_Tallo_Raw',
                   'Tallo_Raw', 'COLUMN';

PRINT '[PASO 4] Renames OK';


/* =====================================================================
   PASO 5.  DROP columnas (destructivo)
   ===================================================================== */

------------------------------------------------------------ 5.1 Censo_Plantas
IF COL_LENGTH('Bronce.Censo_Plantas','Campana_Raw')       IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Campana_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Area_Raw')          IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Area_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Plantas_Raw')       IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Plantas_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Ha_Produccion_Raw') IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Ha_Produccion_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Buenas_Raw')        IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Buenas_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Regulares_Raw')     IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Regulares_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Malas_Raw')         IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Malas_Raw;
IF COL_LENGTH('Bronce.Censo_Plantas','Muertas_Raw')       IS NOT NULL ALTER TABLE Bronce.Censo_Plantas DROP COLUMN Muertas_Raw;

------------------------------------------------------------ 5.2 Conteo_Fruta
IF COL_LENGTH('Bronce.Conteo_Fruta','Evaluador_Raw') IS NOT NULL ALTER TABLE Bronce.Conteo_Fruta DROP COLUMN Evaluador_Raw;
IF COL_LENGTH('Bronce.Conteo_Fruta','Fundo_Raw')     IS NOT NULL ALTER TABLE Bronce.Conteo_Fruta DROP COLUMN Fundo_Raw;
IF COL_LENGTH('Bronce.Conteo_Fruta','Sector_Raw')    IS NOT NULL ALTER TABLE Bronce.Conteo_Fruta DROP COLUMN Sector_Raw;

------------------------------------------------------------ 5.3 Evaluacion_Pesos (17 cols)
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoBaya_Raw')             IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoBaya_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','CantMuestra_Raw')          IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN CantMuestra_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','Cremas_Raw')               IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN Cremas_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','Maduras_Raw')              IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN Maduras_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','BayasPequenas_Raw')        IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN BayasPequenas_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoBayasPequenas_Raw')    IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoBayasPequenas_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','BayasPequenas2_Raw')       IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN BayasPequenas2_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','BayasGrandes_Raw')         IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN BayasGrandes_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoBayasGrandes_Raw')     IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoBayasGrandes_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','BayasFase1_Raw')           IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN BayasFase1_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoBayasFase1_Raw')       IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoBayasFase1_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','BayasFase2_Raw')           IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN BayasFase2_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoBayasFase2_Raw')       IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoBayasFase2_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoCremas_Raw')           IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoCremas_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoMaduras_Raw')          IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoMaduras_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','PesoBayasPequenas2_Raw')   IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN PesoBayasPequenas2_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Pesos','Fundo_Raw')                IS NOT NULL ALTER TABLE Bronce.Evaluacion_Pesos DROP COLUMN Fundo_Raw;

------------------------------------------------------------ 5.4 Evaluacion_Vegetativa
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Campana_Raw')         IS NOT NULL ALTER TABLE Bronce.Evaluacion_Vegetativa DROP COLUMN Campana_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Semanas_Poda_Raw')    IS NOT NULL ALTER TABLE Bronce.Evaluacion_Vegetativa DROP COLUMN Semanas_Poda_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Muestra_Plantas_Raw') IS NOT NULL ALTER TABLE Bronce.Evaluacion_Vegetativa DROP COLUMN Muestra_Plantas_Raw;
IF COL_LENGTH('Bronce.Evaluacion_Vegetativa','Evaluador_Raw')       IS NOT NULL ALTER TABLE Bronce.Evaluacion_Vegetativa DROP COLUMN Evaluador_Raw;

------------------------------------------------------------ 5.5 Fisiologia
IF COL_LENGTH('Bronce.Fisiologia','Fundo_Raw') IS NOT NULL ALTER TABLE Bronce.Fisiologia DROP COLUMN Fundo_Raw;

------------------------------------------------------------ 5.6 Floracion
IF COL_LENGTH('Bronce.Floracion','Consumidor_Raw')  IS NOT NULL ALTER TABLE Bronce.Floracion DROP COLUMN Consumidor_Raw;
IF COL_LENGTH('Bronce.Floracion','Descripcion_Raw') IS NOT NULL ALTER TABLE Bronce.Floracion DROP COLUMN Descripcion_Raw;

------------------------------------------------------------ 5.7 Induccion_Floral
IF COL_LENGTH('Bronce.Induccion_Floral','Variedad_Raw')        IS NOT NULL ALTER TABLE Bronce.Induccion_Floral DROP COLUMN Variedad_Raw;
IF COL_LENGTH('Bronce.Induccion_Floral','Tipo_Evaluacion_Raw') IS NOT NULL ALTER TABLE Bronce.Induccion_Floral DROP COLUMN Tipo_Evaluacion_Raw;
IF COL_LENGTH('Bronce.Induccion_Floral','Evaluador_Raw')       IS NOT NULL ALTER TABLE Bronce.Induccion_Floral DROP COLUMN Evaluador_Raw;
IF COL_LENGTH('Bronce.Induccion_Floral','Consumidor_Raw')      IS NOT NULL ALTER TABLE Bronce.Induccion_Floral DROP COLUMN Consumidor_Raw;
IF COL_LENGTH('Bronce.Induccion_Floral','BrotesTotales_Raw')   IS NOT NULL ALTER TABLE Bronce.Induccion_Floral DROP COLUMN BrotesTotales_Raw;

------------------------------------------------------------ 5.8 Tasa_Crecimiento_Brotes (10 cols)
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Codigo_Origen_Raw')   IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Codigo_Origen_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Semana_Raw')          IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Semana_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Dia_Raw')             IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Dia_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Condicion_Raw')       IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Condicion_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Ensayo_Raw')          IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Ensayo_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Medida_Raw')          IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Medida_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Fecha_Poda_Aux_Raw')  IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Fecha_Poda_Aux_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Campana_Raw')         IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Campana_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Observacion_Raw')     IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Observacion_Raw;
IF COL_LENGTH('Bronce.Tasa_Crecimiento_Brotes','Tipo_Evaluacion_Raw') IS NOT NULL ALTER TABLE Bronce.Tasa_Crecimiento_Brotes DROP COLUMN Tipo_Evaluacion_Raw;

PRINT '[PASO 5] DROP columnas OK';


/* =====================================================================
   PASO 6.  DROP TABLE Bronce.Maduracion
   ===================================================================== */
IF EXISTS (SELECT 1 FROM sys.tables t
           JOIN sys.schemas s ON s.schema_id = t.schema_id
           WHERE s.name = 'Bronce' AND t.name = 'Maduracion')
BEGIN
    DROP TABLE Bronce.Maduracion;
    PRINT '[PASO 6] DROP TABLE Bronce.Maduracion OK';
END
ELSE
    PRINT '[PASO 6] Bronce.Maduracion ya no existe';


COMMIT TRAN;
PRINT '======== REFACTOR COMPLETO ========';
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRAN;
    DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
    PRINT '======== ERROR -> ROLLBACK ========';
    PRINT @msg;
    THROW;
END CATCH;
