/* ============================================================
   fase35_renombrar_facts.sql
   ============================================================
   Refactor de dos tablas Fact:

   1. Silver.Fact_Censo_Plantas  ->  Silver.Fact_areas_plantas
      - Preserva las 1,028 filas existentes (sp_rename, no truncate)
      - Agrega columnas:
          * ID_Campana   (FK -> Dim_Campana)
          * ID_Condicion (FK -> Dim_Condicion_Cultivo)

   2. Silver.Fact_Sanidad_Activo  ->  Silver.Fact_Censo_Plantas
      - La tabla esta vacia, semantica cambia a censo de plantas
        clasificadas por condicion (Buena / Regular / Mala).
      - Elimina columnas obsoletas:
          Plantas_Vivas, Plantas_Muertas, Total_Plantas, Pct_Mortalidad
      - Agrega columnas:
          Plantas_Buenas, Plantas_Regulares, Plantas_Malas  (int NULL)

   Es idempotente: usa OBJECT_ID() y COL_LENGTH() para no fallar
   si ya se aplico.
   ============================================================ */

SET NOCOUNT ON;
BEGIN TRY
BEGIN TRANSACTION;

/* ------------------------------------------------------------
   PASO 1.  Fact_Censo_Plantas  ->  Fact_areas_plantas
   ------------------------------------------------------------ */
IF  OBJECT_ID('Silver.Fact_Censo_Plantas',  'U') IS NOT NULL
AND OBJECT_ID('Silver.Fact_areas_plantas',  'U') IS NULL
BEGIN
    /* Verificacion previa: la tabla actual no debe tener las columnas
       de la nueva tabla, sino estamos pisando algo inesperado. */
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Plantas_Buenas') IS NOT NULL
        THROW 50001, 'Fact_Censo_Plantas ya tiene columna Plantas_Buenas. Abortar para evitar perdida.', 1;

    EXEC sp_rename N'Silver.Fact_Censo_Plantas', N'Fact_areas_plantas';
    PRINT 'OK  Renombrado: Silver.Fact_Censo_Plantas -> Silver.Fact_areas_plantas';
END
ELSE
    PRINT 'SKIP paso 1: Fact_areas_plantas ya existe o Fact_Censo_Plantas no encontrada.';


/* ------------------------------------------------------------
   PASO 2.  Fact_Sanidad_Activo  ->  Fact_Censo_Plantas
   Antes hay que dropear IX_FactSanidad_Geografia_Tiempo
   porque incluye Plantas_Vivas, Plantas_Muertas, Total_Plantas
   (no podriamos borrar esas columnas con el indice viviendo).
   ------------------------------------------------------------ */
IF  OBJECT_ID('Silver.Fact_Sanidad_Activo', 'U') IS NOT NULL
AND OBJECT_ID('Silver.Fact_Censo_Plantas',  'U') IS NULL  -- ya liberada por paso 1
BEGIN
    -- 2a. Drop indice que incluye columnas obsoletas
    IF EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = 'IX_FactSanidad_Geografia_Tiempo'
          AND object_id = OBJECT_ID('Silver.Fact_Sanidad_Activo')
    )
    BEGIN
        DROP INDEX IX_FactSanidad_Geografia_Tiempo ON Silver.Fact_Sanidad_Activo;
        PRINT 'OK  Eliminado indice IX_FactSanidad_Geografia_Tiempo.';
    END

    -- 2b. Rename tabla
    EXEC sp_rename N'Silver.Fact_Sanidad_Activo', N'Fact_Censo_Plantas';
    PRINT 'OK  Renombrado: Silver.Fact_Sanidad_Activo -> Silver.Fact_Censo_Plantas';

    -- 2c. Rename indice unico (cosmético)
    IF EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = 'UX_Fact_SanidadActivo_Grain'
          AND object_id = OBJECT_ID('Silver.Fact_Censo_Plantas')
    )
    BEGIN
        EXEC sp_rename N'Silver.Fact_Censo_Plantas.UX_Fact_SanidadActivo_Grain',
                       N'UX_Fact_Censo_Plantas_Grain',
                       N'INDEX';
        PRINT 'OK  Renombrado indice UX_Fact_SanidadActivo_Grain -> UX_Fact_Censo_Plantas_Grain.';
    END
END
ELSE
    PRINT 'SKIP paso 2: ya aplicado o Fact_Sanidad_Activo no encontrada.';


/* ------------------------------------------------------------
   PASO 3.  Modificar nuevo Fact_Censo_Plantas
       Eliminar  : Plantas_Vivas, Plantas_Muertas, Total_Plantas, Pct_Mortalidad
       Agregar   : Plantas_Buenas, Plantas_Regulares, Plantas_Malas  (int NULL)
       Recrear   : indice de cobertura con las columnas nuevas
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_Censo_Plantas', 'U') IS NOT NULL
BEGIN
    -- Pct_Mortalidad es columna computada y depende de las otras: dropear PRIMERO
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Pct_Mortalidad')  IS NOT NULL
        ALTER TABLE Silver.Fact_Censo_Plantas DROP COLUMN Pct_Mortalidad;
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Plantas_Vivas')   IS NOT NULL
        ALTER TABLE Silver.Fact_Censo_Plantas DROP COLUMN Plantas_Vivas;
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Plantas_Muertas') IS NOT NULL
        ALTER TABLE Silver.Fact_Censo_Plantas DROP COLUMN Plantas_Muertas;
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Total_Plantas')   IS NOT NULL
        ALTER TABLE Silver.Fact_Censo_Plantas DROP COLUMN Total_Plantas;
    PRINT 'OK  Eliminadas columnas obsoletas en Fact_Censo_Plantas.';

    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Plantas_Buenas')    IS NULL
        ALTER TABLE Silver.Fact_Censo_Plantas ADD Plantas_Buenas    INT NULL;
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Plantas_Regulares') IS NULL
        ALTER TABLE Silver.Fact_Censo_Plantas ADD Plantas_Regulares INT NULL;
    IF COL_LENGTH('Silver.Fact_Censo_Plantas', 'Plantas_Malas')     IS NULL
        ALTER TABLE Silver.Fact_Censo_Plantas ADD Plantas_Malas     INT NULL;
    PRINT 'OK  Agregadas columnas Plantas_Buenas/Regulares/Malas.';

    -- Indice de cobertura recreado
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = 'IX_FactCenso_Geografia_Tiempo'
          AND object_id = OBJECT_ID('Silver.Fact_Censo_Plantas')
    )
    BEGIN
        CREATE NONCLUSTERED INDEX IX_FactCenso_Geografia_Tiempo
            ON Silver.Fact_Censo_Plantas (ID_Geografia, ID_Tiempo)
            INCLUDE (ID_Variedad, Plantas_Buenas, Plantas_Regulares, Plantas_Malas);
        PRINT 'OK  Creado IX_FactCenso_Geografia_Tiempo.';
    END
END


/* ------------------------------------------------------------
   PASO 4.  Agregar columnas FK a Fact_areas_plantas
       ID_Campana   (FK -> Dim_Campana.ID_Campana)
       ID_Condicion (FK -> Dim_Condicion_Cultivo.ID_Condicion)
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_areas_plantas', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('Silver.Fact_areas_plantas', 'ID_Campana') IS NULL
    BEGIN
        ALTER TABLE Silver.Fact_areas_plantas ADD ID_Campana INT NULL;
        PRINT 'OK  Agregada columna ID_Campana.';
    END

    IF COL_LENGTH('Silver.Fact_areas_plantas', 'ID_Condicion') IS NULL
    BEGIN
        ALTER TABLE Silver.Fact_areas_plantas ADD ID_Condicion INT NULL;
        PRINT 'OK  Agregada columna ID_Condicion.';
    END

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactAreasPlantas_Campana'
    )
    BEGIN
        ALTER TABLE Silver.Fact_areas_plantas
            ADD CONSTRAINT FK_FactAreasPlantas_Campana
            FOREIGN KEY (ID_Campana) REFERENCES Silver.Dim_Campana(ID_Campana);
        PRINT 'OK  FK_FactAreasPlantas_Campana creada.';
    END

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactAreasPlantas_Condicion'
    )
    BEGIN
        ALTER TABLE Silver.Fact_areas_plantas
            ADD CONSTRAINT FK_FactAreasPlantas_Condicion
            FOREIGN KEY (ID_Condicion) REFERENCES Silver.Dim_Condicion_Cultivo(ID_Condicion);
        PRINT 'OK  FK_FactAreasPlantas_Condicion creada.';
    END
END


COMMIT TRANSACTION;
PRINT '== fase35 OK ==';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR fase35: ' + ERROR_MESSAGE();
    THROW;
END CATCH
