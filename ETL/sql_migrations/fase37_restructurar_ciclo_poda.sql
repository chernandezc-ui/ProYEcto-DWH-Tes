/* ============================================================
   fase37_restructurar_ciclo_poda.sql
   ============================================================
   Reestructura Silver.Fact_Ciclo_Poda para reflejar la granularidad
   real de Bronce: UNA FILA POR PUNTO DE MUESTREO.

   Hoy:
     - Silver tiene grain [Geo, Tiempo, Variedad, Tipo_Evaluacion]
       y descarta puntos extra de una misma valvula con el batch
       deduplicador. Perdida silenciosa de datos.
     - Columnas se llaman Promedio_X pero el procesador NO promedia,
       solo copia el valor Raw. El prefijo miente.

   Cambios:
     1. DROP UNIQUE INDEX UX_Fact_CicloPoda_Grain (viejo, 4 cols)
     2. TRUNCATE TABLE Silver.Fact_Ciclo_Poda
        (la data actual perdio Punto y no se puede backfillear;
         se re-procesa desde Bronce con el pipeline)
     3. Renombrar 7 columnas Promedio_X -> X
     4. ADD COLUMN Punto INT NULL
     5. CREATE UNIQUE INDEX UX_Fact_CicloPoda_Grain con 5 cols
        (incluye Punto), filtrado para tolerar NULLs transitorios

   Idempotente. Transaccional con TRY/CATCH+ROLLBACK.

   Otros indices (IX_FactCicloPoda_Tiempo_Variedad de fase34)
   NO se tocan, siguen siendo validos.
   ============================================================ */

SET NOCOUNT ON;
BEGIN TRY
BEGIN TRANSACTION;

/* ------------------------------------------------------------
   1. Drop UNIQUE INDEX viejo
   ------------------------------------------------------------ */
IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_CicloPoda_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclo_Poda')
)
BEGIN
    DROP INDEX UX_Fact_CicloPoda_Grain ON Silver.Fact_Ciclo_Poda;
    PRINT 'OK  DROP INDEX UX_Fact_CicloPoda_Grain (viejo, 4 cols)';
END
ELSE
    PRINT 'SKIP UX_Fact_CicloPoda_Grain (ya no existe)';

/* ------------------------------------------------------------
   2. TRUNCATE TABLE
   ------------------------------------------------------------ */
IF OBJECT_ID('Silver.Fact_Ciclo_Poda', 'U') IS NOT NULL
BEGIN
    DECLARE @rows_antes INT = (SELECT COUNT(*) FROM Silver.Fact_Ciclo_Poda);
    TRUNCATE TABLE Silver.Fact_Ciclo_Poda;
    PRINT CONCAT('OK  TRUNCATE Silver.Fact_Ciclo_Poda (', @rows_antes, ' filas borradas, se re-procesan desde Bronce)');
END

/* ------------------------------------------------------------
   3. Renombrar columnas Promedio_X -> X
   ------------------------------------------------------------ */
IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Tallos_Planta') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Tallos_Planta') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Tallos_Planta', N'Tallos_Planta', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Tallos_Planta -> Tallos_Planta';
END
ELSE PRINT 'SKIP Promedio_Tallos_Planta';

IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Longitud_Tallo') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Longitud_Tallo') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Longitud_Tallo', N'Longitud_Tallo', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Longitud_Tallo -> Longitud_Tallo';
END
ELSE PRINT 'SKIP Promedio_Longitud_Tallo';

IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Diametro_Tallo') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Diametro_Tallo') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Diametro_Tallo', N'Diametro_Tallo', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Diametro_Tallo -> Diametro_Tallo';
END
ELSE PRINT 'SKIP Promedio_Diametro_Tallo';

IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Ramilla_Planta') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Ramilla_Planta') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Ramilla_Planta', N'Ramilla_Planta', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Ramilla_Planta -> Ramilla_Planta';
END
ELSE PRINT 'SKIP Promedio_Ramilla_Planta';

IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Tocones_Planta') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Tocones_Planta') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Tocones_Planta', N'Tocones_Planta', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Tocones_Planta -> Tocones_Planta';
END
ELSE PRINT 'SKIP Promedio_Tocones_Planta';

IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Cortes_Defectuosos') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Cortes_Defectuosos') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Cortes_Defectuosos', N'Cortes_Defectuosos', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Cortes_Defectuosos -> Cortes_Defectuosos';
END
ELSE PRINT 'SKIP Promedio_Cortes_Defectuosos';

IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Promedio_Altura_Poda') IS NOT NULL
   AND COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Altura_Poda') IS NULL
BEGIN
    EXEC sp_rename N'Silver.Fact_Ciclo_Poda.Promedio_Altura_Poda', N'Altura_Poda', N'COLUMN';
    PRINT 'OK  RENAME Promedio_Altura_Poda -> Altura_Poda';
END
ELSE PRINT 'SKIP Promedio_Altura_Poda';

/* ------------------------------------------------------------
   4. ADD COLUMN Punto INT NULL
   ------------------------------------------------------------ */
IF COL_LENGTH('Silver.Fact_Ciclo_Poda', 'Punto') IS NULL
BEGIN
    ALTER TABLE Silver.Fact_Ciclo_Poda ADD Punto INT NULL;
    PRINT 'OK  ADD COLUMN Punto INT NULL';
END
ELSE
    PRINT 'SKIP Punto (ya existe)';

/* ------------------------------------------------------------
   5. CREATE UNIQUE INDEX UX_Fact_CicloPoda_Grain (5 cols)
      Filtrado WHERE Punto IS NOT NULL para tolerar transitorios.
   ------------------------------------------------------------ */
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_Fact_CicloPoda_Grain'
      AND object_id = OBJECT_ID('Silver.Fact_Ciclo_Poda')
)
BEGIN
    EXEC sp_executesql N'
        CREATE UNIQUE NONCLUSTERED INDEX UX_Fact_CicloPoda_Grain
            ON Silver.Fact_Ciclo_Poda (ID_Geografia, ID_Tiempo, ID_Variedad, Tipo_Evaluacion, Punto)
            WHERE Punto IS NOT NULL;
    ';
    PRINT 'OK  CREATE UNIQUE INDEX UX_Fact_CicloPoda_Grain (5 cols, filtrado)';
END
ELSE
    PRINT 'SKIP UX_Fact_CicloPoda_Grain (ya existe)';


COMMIT TRANSACTION;
PRINT '== fase37 OK ==';

/* ------------------------------------------------------------
   Verificacion final (ejecutar a mano si querés):

     SELECT c.name, ty.name AS tipo, c.is_nullable
     FROM sys.columns c
     JOIN sys.types ty ON ty.user_type_id = c.user_type_id
     WHERE c.object_id = OBJECT_ID('Silver.Fact_Ciclo_Poda')
     ORDER BY c.column_id;

     SELECT i.name, i.is_unique, i.has_filter, i.filter_definition,
            (SELECT STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal)
             FROM sys.index_columns ic
             JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
             WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id) AS cols
     FROM sys.indexes i
     WHERE i.object_id = OBJECT_ID('Silver.Fact_Ciclo_Poda')
       AND i.is_primary_key = 0;
   ------------------------------------------------------------ */

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR fase37: ' + ERROR_MESSAGE();
    THROW;
END CATCH
