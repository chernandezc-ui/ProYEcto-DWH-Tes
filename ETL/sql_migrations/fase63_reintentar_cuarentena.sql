/* ==========================================================================
   fase63_reintentar_cuarentena.sql
   --------------------------------------------------------------------------
   Marca como CARGADO todos los registros rechazados de cualquier tabla
   Bronce.* para que el próximo run del ETL los reprocese.

   Aprovecha el nuevo default global FUNDO_DEFECTO='ARANDANO ACP' (fase62),
   por lo que filas rechazadas por fundo ausente ahora podrán resolverse.

   - Recorre dinámicamente todas las tablas de Bronce con columna Estado_Carga.
   - Cambia Estado_Carga IN ('RECHAZADO','CUARENTENA','ERROR','PENDIENTE') -> 'CARGADO'.
     ('CARGADO' es el estado que TODAS las facts filtran en _leer_bronce_*.
      'PENDIENTE' quedaba invisible al filtro y dejaba filas atascadas.)
   - Reporta cuántas filas se actualizaron por tabla.
   ========================================================================== */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @esquema  SYSNAME = N'Bronce';

DECLARE @resumen TABLE (
    tabla        SYSNAME,
    filas_antes  INT,
    filas_reset  INT
);

DECLARE @tabla SYSNAME, @sql NVARCHAR(MAX), @filas_antes INT, @filas_reset INT;

DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
    SELECT t.name
    FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    JOIN sys.columns c ON c.object_id = t.object_id
    WHERE s.name = @esquema
      AND c.name = 'Estado_Carga'
    ORDER BY t.name;

OPEN cur;
FETCH NEXT FROM cur INTO @tabla;

WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'
        SELECT @cnt = COUNT(*)
        FROM ' + QUOTENAME(@esquema) + N'.' + QUOTENAME(@tabla) + N'
        WHERE Estado_Carga IN (N''RECHAZADO'', N''CUARENTENA'', N''ERROR'', N''PENDIENTE'');';
    EXEC sp_executesql @sql, N'@cnt INT OUTPUT', @cnt = @filas_antes OUTPUT;

    IF @filas_antes > 0
    BEGIN
        SET @sql = N'
            UPDATE ' + QUOTENAME(@esquema) + N'.' + QUOTENAME(@tabla) + N'
            SET    Estado_Carga = N''CARGADO''
            WHERE  Estado_Carga IN (N''RECHAZADO'', N''CUARENTENA'', N''ERROR'', N''PENDIENTE'');
            SELECT @r = @@ROWCOUNT;';
        EXEC sp_executesql @sql, N'@r INT OUTPUT', @r = @filas_reset OUTPUT;
    END
    ELSE
        SET @filas_reset = 0;

    INSERT INTO @resumen (tabla, filas_antes, filas_reset)
    VALUES (@tabla, @filas_antes, @filas_reset);

    FETCH NEXT FROM cur INTO @tabla;
END

CLOSE cur;
DEALLOCATE cur;

SELECT
    tabla,
    filas_antes,
    filas_reset
FROM @resumen
ORDER BY filas_reset DESC, tabla;

SELECT
    SUM(filas_reset) AS Total_Filas_Reseteadas,
    COUNT(*)         AS Tablas_Procesadas
FROM @resumen;
GO
