-- Migración: agregar métricas de filas a Control.Corrida_Paso
-- Ejecutar en SQL Server contra la base de datos ACP

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'Control'
      AND TABLE_NAME   = 'Corrida_Paso'
      AND COLUMN_NAME  = 'Filas_Procesadas'
)
BEGIN
    ALTER TABLE Control.Corrida_Paso
        ADD Filas_Procesadas INT NULL DEFAULT 0,
            Filas_Rechazadas INT NULL DEFAULT 0;
    PRINT 'Columnas Filas_Procesadas y Filas_Rechazadas agregadas a Control.Corrida_Paso';
END
ELSE
BEGIN
    PRINT 'Las columnas ya existen — migración omitida.';
END
