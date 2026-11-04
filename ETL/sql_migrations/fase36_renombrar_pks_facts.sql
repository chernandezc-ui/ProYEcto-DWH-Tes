/* ============================================================
   fase36_renombrar_pks_facts.sql
   ============================================================
   Limpieza cosmetica que termina lo que dejo la fase35.

   Despues de la fase35, las dos tablas quedaron con PKs heredados
   de su nombre anterior:

     Silver.Fact_areas_plantas
        - columna PK : ID_Censo        (heredada de Fact_Censo_Plantas viejo)
        - constraint : PK__Fact_Cen__... (autonombrada, ID_Censo era OK
                                          pero ya no es coherente con el
                                          nombre de la tabla)

     Silver.Fact_Censo_Plantas
        - columna PK : ID_Sanidad      (heredada de Fact_Sanidad_Activo)
        - constraint : PK__Fact_San__...

   Esta fase:
     1. Renombra columna ID_Censo   -> ID_Area  en Fact_areas_plantas
     2. Renombra PK constraint a    PK_Fact_areas_plantas
     3. Renombra columna ID_Sanidad -> ID_Censo en Fact_Censo_Plantas
     4. Renombra PK constraint a    PK_Fact_Censo_Plantas

   No mueve datos. No agrega ni elimina columnas. Es idempotente.

   Verificacion previa:
     - Ninguna otra tabla del DWH referencia estas dos como FK,
       asi que renombrar la columna no rompe constraints externos.
       (Confirmado: ambas tablas no tienen FKs entrantes.)
   ============================================================ */

SET NOCOUNT ON;
BEGIN TRY
BEGIN TRANSACTION;

/* ------------------------------------------------------------
   1. Fact_areas_plantas : ID_Censo -> ID_Area
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_areas_plantas', 'U') IS NOT NULL
BEGIN
    IF  COL_LENGTH('Silver.Fact_areas_plantas', 'ID_Censo') IS NOT NULL
    AND COL_LENGTH('Silver.Fact_areas_plantas', 'ID_Area')  IS NULL
    BEGIN
        EXEC sp_rename
            N'Silver.Fact_areas_plantas.ID_Censo',
            N'ID_Area',
            N'COLUMN';
        PRINT 'OK  Fact_areas_plantas: columna ID_Censo -> ID_Area';
    END
    ELSE
        PRINT 'SKIP Fact_areas_plantas.ID_Censo (ya renombrada o ID_Area ya existe)';
END

/* ------------------------------------------------------------
   2. Fact_areas_plantas : PK -> PK_Fact_areas_plantas
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_areas_plantas', 'U') IS NOT NULL
BEGIN
    DECLARE @pk_areas SYSNAME = (
        SELECT TOP 1 name FROM sys.key_constraints
        WHERE parent_object_id = OBJECT_ID('Silver.Fact_areas_plantas')
          AND type = 'PK'
    );
    IF @pk_areas IS NOT NULL AND @pk_areas <> 'PK_Fact_areas_plantas'
    BEGIN
        DECLARE @old_areas NVARCHAR(300) = N'Silver.' + @pk_areas;
        EXEC sp_rename @old_areas, N'PK_Fact_areas_plantas', N'OBJECT';
        PRINT 'OK  Fact_areas_plantas: PK constraint renombrada';
    END
    ELSE
        PRINT 'SKIP Fact_areas_plantas: PK ya tenia el nombre limpio';
END

/* ------------------------------------------------------------
   3. Fact_Censo_Plantas : ID_Sanidad -> ID_Censo
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_Censo_Plantas', 'U') IS NOT NULL
BEGIN
    IF  COL_LENGTH('Silver.Fact_Censo_Plantas', 'ID_Sanidad') IS NOT NULL
    AND COL_LENGTH('Silver.Fact_Censo_Plantas', 'ID_Censo')   IS NULL
    BEGIN
        EXEC sp_rename
            N'Silver.Fact_Censo_Plantas.ID_Sanidad',
            N'ID_Censo',
            N'COLUMN';
        PRINT 'OK  Fact_Censo_Plantas: columna ID_Sanidad -> ID_Censo';
    END
    ELSE
        PRINT 'SKIP Fact_Censo_Plantas.ID_Sanidad (ya renombrada o ID_Censo ya existe)';
END

/* ------------------------------------------------------------
   4. Fact_Censo_Plantas : PK -> PK_Fact_Censo_Plantas
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_Censo_Plantas', 'U') IS NOT NULL
BEGIN
    DECLARE @pk_censo SYSNAME = (
        SELECT TOP 1 name FROM sys.key_constraints
        WHERE parent_object_id = OBJECT_ID('Silver.Fact_Censo_Plantas')
          AND type = 'PK'
    );
    IF @pk_censo IS NOT NULL AND @pk_censo <> 'PK_Fact_Censo_Plantas'
    BEGIN
        DECLARE @old_censo NVARCHAR(300) = N'Silver.' + @pk_censo;
        EXEC sp_rename @old_censo, N'PK_Fact_Censo_Plantas', N'OBJECT';
        PRINT 'OK  Fact_Censo_Plantas: PK constraint renombrada';
    END
    ELSE
        PRINT 'SKIP Fact_Censo_Plantas: PK ya tenia el nombre limpio';
END


COMMIT TRANSACTION;
PRINT '== fase36 OK ==';

/* ------------------------------------------------------------
   Verificacion final (ejecutar a mano si querés):

     SELECT t.name AS Tabla, c.name AS Col, c.column_id
     FROM sys.tables t
     JOIN sys.columns c ON c.object_id = t.object_id
     WHERE t.schema_id = SCHEMA_ID('Silver')
       AND t.name IN ('Fact_areas_plantas','Fact_Censo_Plantas')
     ORDER BY t.name, c.column_id;

     SELECT OBJECT_NAME(parent_object_id) AS Tabla, name AS Constraint_Name
     FROM sys.key_constraints
     WHERE parent_object_id IN (
        OBJECT_ID('Silver.Fact_areas_plantas'),
        OBJECT_ID('Silver.Fact_Censo_Plantas')
     );
   ------------------------------------------------------------ */

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR fase36: ' + ERROR_MESSAGE();
    THROW;
END CATCH
