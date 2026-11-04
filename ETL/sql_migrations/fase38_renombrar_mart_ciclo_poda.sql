/* ============================================================
   fase38_renombrar_mart_ciclo_poda.sql
   ============================================================
   Acompaña a fase37. Reestructura Gold.Mart_Ciclo_Poda para:

     - Renombrar columnas X_Prom -> X_Total (ya no son promedios,
       son SUMA por punto de muestreo).
     - Agregar columna N_Muestras INT NOT NULL DEFAULT 0
       (cantidad de puntos agregados por grupo).

   Idempotente. Transaccional.

   NOTA: Gold.Mart_Ciclo_Poda se refresca con INSERT desde Silver
   en marts.py::refrescar_mart_ciclo_poda. Antes de correr la
   siguiente carga Gold, hay que ejecutar fase37 + fase38 + el
   pipeline Silver actualizado.
   ============================================================ */

SET NOCOUNT ON;
BEGIN TRY
BEGIN TRANSACTION;

IF OBJECT_ID('Gold.Mart_Ciclo_Poda', 'U') IS NULL
BEGIN
    PRINT 'INFO Gold.Mart_Ciclo_Poda no existe todavia. Nada que hacer.';
    COMMIT TRANSACTION;
    RETURN;
END

/* ------------------------------------------------------------
   0. Vaciar la tabla para evitar inconsistencias con Silver
      reestructurado.
   ------------------------------------------------------------ */
DECLARE @rows_antes INT = (SELECT COUNT(*) FROM Gold.Mart_Ciclo_Poda);
IF @rows_antes > 0
BEGIN
    TRUNCATE TABLE Gold.Mart_Ciclo_Poda;
    PRINT CONCAT('OK  TRUNCATE Gold.Mart_Ciclo_Poda (', @rows_antes, ' filas borradas)');
END
ELSE
    PRINT 'SKIP TRUNCATE (Gold.Mart_Ciclo_Poda ya estaba vacio)';

/* ------------------------------------------------------------
   1. Renombrar 7 columnas X_Prom -> X_Total
   ------------------------------------------------------------ */
IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Tallos_Planta_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Tallos_Planta_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Tallos_Planta_Prom', N'Tallos_Planta_Total', N'COLUMN';
    PRINT 'OK  RENAME Tallos_Planta_Prom -> Tallos_Planta_Total';
END
ELSE PRINT 'SKIP Tallos_Planta_Prom';

IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Longitud_Tallo_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Longitud_Tallo_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Longitud_Tallo_Prom', N'Longitud_Tallo_Total', N'COLUMN';
    PRINT 'OK  RENAME Longitud_Tallo_Prom -> Longitud_Tallo_Total';
END
ELSE PRINT 'SKIP Longitud_Tallo_Prom';

IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Diametro_Tallo_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Diametro_Tallo_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Diametro_Tallo_Prom', N'Diametro_Tallo_Total', N'COLUMN';
    PRINT 'OK  RENAME Diametro_Tallo_Prom -> Diametro_Tallo_Total';
END
ELSE PRINT 'SKIP Diametro_Tallo_Prom';

IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Ramilla_Planta_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Ramilla_Planta_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Ramilla_Planta_Prom', N'Ramilla_Planta_Total', N'COLUMN';
    PRINT 'OK  RENAME Ramilla_Planta_Prom -> Ramilla_Planta_Total';
END
ELSE PRINT 'SKIP Ramilla_Planta_Prom';

IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Tocones_Planta_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Tocones_Planta_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Tocones_Planta_Prom', N'Tocones_Planta_Total', N'COLUMN';
    PRINT 'OK  RENAME Tocones_Planta_Prom -> Tocones_Planta_Total';
END
ELSE PRINT 'SKIP Tocones_Planta_Prom';

IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Cortes_Defectuosos_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Cortes_Defectuosos_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Cortes_Defectuosos_Prom', N'Cortes_Defectuosos_Total', N'COLUMN';
    PRINT 'OK  RENAME Cortes_Defectuosos_Prom -> Cortes_Defectuosos_Total';
END
ELSE PRINT 'SKIP Cortes_Defectuosos_Prom';

IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Altura_Poda_Prom') IS NOT NULL
   AND COL_LENGTH('Gold.Mart_Ciclo_Poda', 'Altura_Poda_Total') IS NULL
BEGIN
    EXEC sp_rename N'Gold.Mart_Ciclo_Poda.Altura_Poda_Prom', N'Altura_Poda_Total', N'COLUMN';
    PRINT 'OK  RENAME Altura_Poda_Prom -> Altura_Poda_Total';
END
ELSE PRINT 'SKIP Altura_Poda_Prom';

/* ------------------------------------------------------------
   2. ADD COLUMN N_Muestras INT NOT NULL DEFAULT 0
   ------------------------------------------------------------ */
IF COL_LENGTH('Gold.Mart_Ciclo_Poda', 'N_Muestras') IS NULL
BEGIN
    ALTER TABLE Gold.Mart_Ciclo_Poda
        ADD N_Muestras INT NOT NULL CONSTRAINT DF_MartCicloPoda_NMuestras DEFAULT 0;
    PRINT 'OK  ADD COLUMN N_Muestras INT NOT NULL DEFAULT 0';
END
ELSE
    PRINT 'SKIP N_Muestras (ya existe)';


COMMIT TRANSACTION;
PRINT '== fase38 OK ==';

/* ------------------------------------------------------------
   Verificacion final:

     SELECT c.name, ty.name AS tipo, c.is_nullable
     FROM sys.columns c
     JOIN sys.types ty ON ty.user_type_id = c.user_type_id
     WHERE c.object_id = OBJECT_ID('Gold.Mart_Ciclo_Poda')
     ORDER BY c.column_id;
   ------------------------------------------------------------ */

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR fase38: ' + ERROR_MESSAGE();
    THROW;
END CATCH
