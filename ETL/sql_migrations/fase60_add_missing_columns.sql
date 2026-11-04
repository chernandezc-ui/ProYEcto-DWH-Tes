-- fase60_add_missing_columns.sql
-- Agrega columnas que existen en el DDL pero no fueron aplicadas a la BD existente.
-- Idempotente: usa IF NOT EXISTS antes de cada ALTER.

PRINT '=== fase60: Agregando columnas faltantes en tablas Silver ===';

-- 1. Fact_Evaluacion_Pesos: Cantidad_Bayas_Muestra
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
      AND name = 'Cantidad_Bayas_Muestra'
)
BEGIN
    ALTER TABLE Silver.Fact_Evaluacion_Pesos
        ADD Cantidad_Bayas_Muestra INT NULL;
    PRINT 'OK: Agregada columna Cantidad_Bayas_Muestra a Silver.Fact_Evaluacion_Pesos';
END
ELSE
    PRINT 'SKIP: Cantidad_Bayas_Muestra ya existe.';

-- 2. Fact_Evaluacion_Pesos: Peso_Proyectado_Baya_g
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Silver.Fact_Evaluacion_Pesos')
      AND name = 'Peso_Proyectado_Baya_g'
)
BEGIN
    ALTER TABLE Silver.Fact_Evaluacion_Pesos
        ADD Peso_Proyectado_Baya_g DECIMAL(6,2) NULL;
    PRINT 'OK: Agregada columna Peso_Proyectado_Baya_g a Silver.Fact_Evaluacion_Pesos';
END
ELSE
    PRINT 'SKIP: Peso_Proyectado_Baya_g ya existe.';

PRINT '=== fase60: Completado ===';
