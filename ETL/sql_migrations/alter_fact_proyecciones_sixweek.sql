-- Migracion para agregar columnas extendidas a Silver.Fact_Proyecciones
-- Necesarias para el modelo Six-Week

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Proyecciones' AND COLUMN_NAME = 'Kg_Pesimista')
BEGIN
    ALTER TABLE Silver.Fact_Proyecciones ADD Kg_Pesimista DECIMAL(18,4);
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Proyecciones' AND COLUMN_NAME = 'Kg_Optimista')
BEGIN
    ALTER TABLE Silver.Fact_Proyecciones ADD Kg_Optimista DECIMAL(18,4);
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Proyecciones' AND COLUMN_NAME = 'Pct_Maduracion')
BEGIN
    ALTER TABLE Silver.Fact_Proyecciones ADD Pct_Maduracion DECIMAL(10,6);
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Proyecciones' AND COLUMN_NAME = 'Pct_Productivas')
BEGIN
    ALTER TABLE Silver.Fact_Proyecciones ADD Pct_Productivas DECIMAL(10,6);
END
